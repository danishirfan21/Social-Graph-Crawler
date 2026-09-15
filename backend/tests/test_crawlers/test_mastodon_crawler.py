import pytest

from app.crawlers.mastodon_crawler import MastodonCrawler


class StubMastodonCrawler(MastodonCrawler):
    async def _lookup_account(self, username, instance):
        return {"id": "1", "acct": username, "display_name": "Root"}

    async def _following(self, account_id, instance):
        return [
            {"id": "2", "acct": "friend", "display_name": "Friend"},
            {"id": "3", "acct": "remote@hachyderm.io", "display_name": "Remote friend"},
        ]


def test_parse_full_and_default_mastodon_handles():
    assert MastodonCrawler._parse_handle("@alice@hachyderm.io") == ("alice", "hachyderm.io")
    assert MastodonCrawler._parse_handle("alice")[0] == "alice"
    with pytest.raises(ValueError):
        MastodonCrawler._parse_handle("alice@https://bad.example")


@pytest.mark.asyncio
async def test_mastodon_crawl_persists_public_following_graph(test_session):
    crawler = StubMastodonCrawler(test_session)
    job = await crawler.crawl("root@mastodon.social", depth=2, max_entities=10)

    assert job.status == "completed"
    assert job.entity_count == 3
    assert job.edge_count == 2
    assert len(crawler.discovered_nodes) == 3
    assert len(crawler.discovered_edges) == 2
