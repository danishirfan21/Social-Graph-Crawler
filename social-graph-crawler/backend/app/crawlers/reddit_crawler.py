"""
Reddit crawler for discovering subreddit and user relationships.
Uses Reddit's public JSON API (no authentication required for public data).
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.crawlers.base import BaseCrawler
from app.models import CrawlJob, CrawlStatus
from app.config import settings


logger = logging.getLogger(__name__)


class RedditCrawler(BaseCrawler):
    """
    Crawls Reddit to discover:
    - Subreddits and their subscribers
    - Top posters in subreddits
    - Cross-posting patterns
    - User commenting relationships
    """
    
    BASE_URL = "https://www.reddit.com"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "User-Agent": settings.REDDIT_USER_AGENT
        }
    
    def get_source_name(self) -> str:
        return "reddit"
    
    async def crawl(
        self,
        start_entity: str,
        depth: int = 2,
        max_entities: int = 100
    ) -> CrawlJob:
        """
        Crawl Reddit starting from a subreddit.
        
        Args:
            start_entity: Subreddit name (e.g., 'python', 'machinelearning')
            depth: Crawl depth (1 = just subreddit, 2 = subreddit + top users, etc.)
            max_entities: Maximum entities to discover
        
        Returns:
            CrawlJob with statistics
        """
        job = await self.create_crawl_job()
        
        try:
            await self.update_crawl_job(job, CrawlStatus.RUNNING)
            
            # Start crawling from the subreddit
            await self._crawl_subreddit(start_entity, depth, max_entities)
            
            # Update job statistics
            await self.update_crawl_job(
                job,
                CrawlStatus.COMPLETED,
                entity_count=len(self.discovered_nodes),
                edge_count=len(self.discovered_edges)
            )
            
            await self.db.commit()
            logger.info(
                f"Reddit crawl completed: {len(self.discovered_nodes)} nodes, "
                f"{len(self.discovered_edges)} edges"
            )
            
        except Exception as e:
            logger.error(f"Reddit crawl failed: {e}")
            await self.update_crawl_job(
                job,
                CrawlStatus.FAILED,
                error_message=str(e)
            )
            await self.db.commit()
            raise
        
        return job
    
    async def _crawl_subreddit(
        self,
        subreddit_name: str,
        depth: int,
        max_entities: int
    ):
        """Crawl a subreddit and its relationships."""
        if len(self.discovered_nodes) >= max_entities:
            return
        
        # Get subreddit info
        subreddit_data = await self._fetch_subreddit_info(subreddit_name)
        if not subreddit_data:
            logger.warning(f"Could not fetch subreddit: {subreddit_name}")
            return
        
        # Create subreddit node
        subreddit_node = await self.create_or_update_node(
            entity_type="subreddit",
            entity_id=subreddit_name.lower(),
            display_name=f"r/{subreddit_name}",
            metadata={
                "subscribers": subreddit_data.get("subscribers", 0),
                "description": subreddit_data.get("public_description", ""),
                "created_utc": subreddit_data.get("created_utc", 0),
                "over18": subreddit_data.get("over18", False)
            }
        )
        
        if depth < 2:
            return
        
        # Get top posts and their authors
        posts = await self._fetch_subreddit_posts(subreddit_name, limit=25)
        
        for post in posts:
            if len(self.discovered_nodes) >= max_entities:
                break
            
            author = post.get("author")
            if not author or author == "[deleted]":
                continue
            
            # Create user node
            user_node = await self.create_or_update_node(
                entity_type="user",
                entity_id=author.lower(),
                display_name=f"u/{author}",
                metadata={
                    "post_karma": 0,  # Would need user endpoint for this
                    "comment_karma": 0
                }
            )
            
            # Create edge: user posts in subreddit
            await self.create_edge(
                source_node=user_node,
                target_node=subreddit_node,
                relationship_type="posts_in",
                weight=post.get("score", 1) / 100.0,  # Normalize score
                metadata={
                    "post_title": post.get("title", ""),
                    "post_id": post.get("id", ""),
                    "created_utc": post.get("created_utc", 0)
                }
            )
            
            # If depth allows, explore user's other subreddits
            if depth >= 3:
                await self._crawl_user(author, max_subreddits=5)
    
    async def _crawl_user(self, username: str, max_subreddits: int = 5):
        """Crawl a user's posting history to find related subreddits."""
        posts = await self._fetch_user_posts(username, limit=50)
        
        subreddit_counts: Dict[str, int] = {}
        for post in posts:
            subreddit = post.get("subreddit")
            if subreddit:
                subreddit_counts[subreddit] = subreddit_counts.get(subreddit, 0) + 1
        
        # Get user node
        user_node = await self.create_or_update_node(
            entity_type="user",
            entity_id=username.lower(),
            display_name=f"u/{username}",
            metadata={}
        )
        
        # Connect to top subreddits
        for subreddit, count in sorted(
            subreddit_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_subreddits]:
            subreddit_node = await self.create_or_update_node(
                entity_type="subreddit",
                entity_id=subreddit.lower(),
                display_name=f"r/{subreddit}",
                metadata={}
            )
            
            await self.create_edge(
                source_node=user_node,
                target_node=subreddit_node,
                relationship_type="posts_in",
                weight=min(count / 10.0, 1.0),  # Normalize
                metadata={"post_count": count}
            )
    
    async def _fetch_subreddit_info(self, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """Fetch subreddit information."""
        url = f"{self.BASE_URL}/r/{subreddit_name}/about.json"
        try:
            data = await self.fetch_with_rate_limit(url, headers=self.headers)
            return data.get("data", {})
        except Exception as e:
            logger.error(f"Error fetching subreddit {subreddit_name}: {e}")
            return None
    
    async def _fetch_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 25,
        time_filter: str = "week"
    ) -> List[Dict[str, Any]]:
        """Fetch top posts from a subreddit."""
        url = f"{self.BASE_URL}/r/{subreddit_name}/top.json"
        params = {"limit": limit, "t": time_filter}
        
        try:
            data = await self.fetch_with_rate_limit(
                url,
                headers=self.headers,
                params=params
            )
            children = data.get("data", {}).get("children", [])
            return [child.get("data", {}) for child in children]
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
            return []
    
    async def _fetch_user_posts(
        self,
        username: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch user's recent posts."""
        url = f"{self.BASE_URL}/user/{username}/submitted.json"
        params = {"limit": limit}
        
        try:
            data = await self.fetch_with_rate_limit(
                url,
                headers=self.headers,
                params=params
            )
            children = data.get("data", {}).get("children", [])
            return [child.get("data", {}) for child in children]
        except Exception as e:
            logger.error(f"Error fetching posts from u/{username}: {e}")
            return []


# Example usage:
# async with RedditCrawler(db_session, rate_limit=1.0) as crawler:
#     job = await crawler.crawl("python", depth=2, max_entities=100)