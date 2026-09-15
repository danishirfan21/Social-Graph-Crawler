"""Crawler for public Mastodon account and following relationships.

Mastodon is federated: an account's home instance is part of its identity.
This crawler intentionally uses only public, read-only endpoints.  A token is
optional because some instances restrict public relationship endpoints.
"""

import logging
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from app.config import settings
from app.crawlers.base import BaseCrawler
from app.models import CrawlJob, CrawlStatus


logger = logging.getLogger(__name__)


class MastodonCrawler(BaseCrawler):
    """Persist a public Mastodon account and its visible following graph."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {"User-Agent": settings.CRAWLER_USER_AGENT}
        if settings.MASTODON_ACCESS_TOKEN:
            self.headers["Authorization"] = f"Bearer {settings.MASTODON_ACCESS_TOKEN}"

    def get_source_name(self) -> str:
        return "mastodon"

    async def crawl(
        self,
        start_entity: str,
        depth: int = 2,
        max_entities: int = 100,
        job: CrawlJob | None = None,
    ) -> CrawlJob:
        job = job or await self.create_crawl_job(start_entity, f"direct:{start_entity}")
        try:
            await self.update_crawl_job(job, CrawlStatus.RUNNING)
            username, instance = self._parse_handle(start_entity)
            account = await self._lookup_account(username, instance)
            if not account:
                raise ValueError(f"No public Mastodon account found for {start_entity}")
            await self._crawl_account(account, instance, depth, max_entities)
            await self.update_crawl_job(
                job,
                CrawlStatus.COMPLETED,
                entity_count=len(self.discovered_nodes),
                edge_count=len(self.discovered_edges),
            )
            await self.db.commit()
        except Exception as exc:
            logger.error("Mastodon crawl failed: %s", exc)
            await self.update_crawl_job(job, CrawlStatus.FAILED, error_message=str(exc))
            await self.db.commit()
            raise
        return job

    @staticmethod
    def _parse_handle(value: str) -> Tuple[str, str]:
        handle = value.strip().lstrip("@")
        if "@" in handle:
            username, instance = handle.rsplit("@", 1)
        else:
            username, instance = handle, settings.MASTODON_INSTANCE
        instance = instance.lower().strip().rstrip("/")
        if not username or not instance or "/" in instance or ":" in instance:
            raise ValueError("Enter a Mastodon handle such as user@mastodon.social")
        return username, instance

    @staticmethod
    def _base_url(instance: str) -> str:
        return f"https://{instance}"

    async def _lookup_account(self, username: str, instance: str) -> Dict[str, Any] | None:
        data = await self.fetch_with_rate_limit(
            f"{self._base_url(instance)}/api/v1/accounts/lookup",
            headers=self.headers,
            params={"acct": username},
        )
        return data if data.get("id") else None

    async def _crawl_account(
        self,
        account: Dict[str, Any],
        instance: str,
        depth: int,
        max_entities: int,
        current_depth: int = 1,
    ) -> None:
        if len(self.discovered_nodes) >= max_entities:
            return
        account_node = await self._store_account(account, instance)
        if current_depth >= depth or len(self.discovered_nodes) >= max_entities:
            return

        following = await self._following(str(account["id"]), instance)
        for followed in following:
            if len(self.discovered_nodes) >= max_entities:
                break
            followed_instance = self._account_instance(followed, instance)
            followed_node = await self._store_account(followed, followed_instance)
            await self.create_edge(
                source_node=account_node,
                target_node=followed_node,
                relationship_type="follows",
                weight=1.0,
                metadata={"instance": instance},
            )
            if current_depth + 1 < depth:
                await self._crawl_account(
                    followed, followed_instance, depth, max_entities, current_depth + 1
                )

    async def _store_account(self, account: Dict[str, Any], instance: str):
        acct = account.get("acct") or account.get("username") or str(account["id"])
        handle = acct if "@" in acct else f"{acct}@{instance}"
        return await self.create_or_update_node(
            entity_type="account",
            entity_id=f"{instance}:{account['id']}",
            display_name=f"@{handle}",
            metadata={
                "handle": f"@{handle}",
                "display_name": account.get("display_name", ""),
                "url": account.get("url", ""),
                "note": account.get("note", "")[:500],
                "followers": account.get("followers_count", 0),
                "following": account.get("following_count", 0),
                "statuses": account.get("statuses_count", 0),
                "bot": account.get("bot", False),
                "locked": account.get("locked", False),
                "instance": instance,
            },
        )

    async def _following(self, account_id: str, instance: str) -> List[Dict[str, Any]]:
        data = await self.fetch_with_rate_limit(
            f"{self._base_url(instance)}/api/v1/accounts/{account_id}/following",
            headers=self.headers,
            params={"limit": 40},
        )
        return data if isinstance(data, list) else []

    @staticmethod
    def _account_instance(account: Dict[str, Any], fallback: str) -> str:
        acct = account.get("acct", "")
        if "@" in acct:
            return acct.rsplit("@", 1)[1].lower()
        url_host = urlparse(account.get("url", "")).hostname
        return url_host.lower() if url_host else fallback
