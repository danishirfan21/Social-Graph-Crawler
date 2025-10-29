"""
Wikipedia crawler for discovering article and concept relationships.
Uses Wikipedia API to explore link networks and categories.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote

from app.crawlers.base import BaseCrawler
from app.models import CrawlJob, CrawlStatus
from app.config import settings


logger = logging.getLogger(__name__)


class WikipediaCrawler(BaseCrawler):
    """
    Crawls Wikipedia to discover:
    - Article pages and their metadata
    - Outgoing links (what this article links to)
    - Incoming links (backlinks - what links to this article)
    - Category memberships
    - Related articles
    """
    
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "User-Agent": settings.REDDIT_USER_AGENT
        }
    
    def get_source_name(self) -> str:
        return "wikipedia"
    
    async def crawl(
        self,
        start_entity: str,
        depth: int = 2,
        max_entities: int = 100
    ) -> CrawlJob:
        """
        Crawl Wikipedia starting from an article.
        
        Args:
            start_entity: Article title (e.g., "Python_(programming_language)")
            depth: Crawl depth
            max_entities: Maximum entities to discover
        
        Returns:
            CrawlJob with statistics
        """
        job = await self.create_crawl_job()
        
        try:
            await self.update_crawl_job(job, CrawlStatus.RUNNING)
            
            # Start crawling from the article
            await self._crawl_article(start_entity, depth, max_entities)
            
            # Update job statistics
            await self.update_crawl_job(
                job,
                CrawlStatus.COMPLETED,
                entity_count=len(self.discovered_nodes),
                edge_count=len(self.discovered_edges)
            )
            
            await self.db.commit()
            logger.info(
                f"Wikipedia crawl completed: {len(self.discovered_nodes)} nodes, "
                f"{len(self.discovered_edges)} edges"
            )
            
        except Exception as e:
            logger.error(f"Wikipedia crawl failed: {e}")
            await self.update_crawl_job(
                job,
                CrawlStatus.FAILED,
                error_message=str(e)
            )
            await self.db.commit()
            raise
        
        return job
    
    async def _crawl_article(
        self,
        article_title: str,
        depth: int,
        max_entities: int,
        current_depth: int = 0
    ):
        """Crawl a Wikipedia article and its links."""
        if len(self.discovered_nodes) >= max_entities:
            return
        
        if current_depth > depth:
            return
        
        # Get article info
        article_data = await self._fetch_article_info(article_title)
        if not article_data:
            logger.warning(f"Could not fetch article: {article_title}")
            return
        
        page_id = article_data.get("pageid")
        if not page_id:
            return
        
        # Create article node
        article_node = await self.create_or_update_node(
            entity_type="article",
            entity_id=str(page_id),
            display_name=article_data.get("title", article_title),
            metadata={
                "title": article_data.get("title", ""),
                "extract": article_data.get("extract", "")[:500],  # First 500 chars
                "url": article_data.get("fullurl", ""),
                "length": article_data.get("length", 0),
                "touched": article_data.get("touched", ""),
                "categories": article_data.get("categories", [])[:10]  # First 10 categories
            }
        )
        
        if current_depth >= depth:
            return
        
        # Get outgoing links
        links = await self._fetch_article_links(article_title, limit=20)
        
        for link_title in links:
            if len(self.discovered_nodes) >= max_entities:
                break
            
            # Get basic info for linked article
            linked_data = await self._fetch_article_info(link_title)
            if not linked_data or not linked_data.get("pageid"):
                continue
            
            # Create linked article node
            linked_node = await self.create_or_update_node(
                entity_type="article",
                entity_id=str(linked_data["pageid"]),
                display_name=linked_data.get("title", link_title),
                metadata={
                    "title": linked_data.get("title", ""),
                    "extract": linked_data.get("extract", "")[:200],
                    "url": linked_data.get("fullurl", "")
                }
            )
            
            # Create edge: article links to another article
            await self.create_edge(
                source_node=article_node,
                target_node=linked_node,
                relationship_type="links_to",
                weight=1.0,
                metadata={}
            )
            
            # Recursively crawl linked articles (if depth allows)
            if current_depth + 1 < depth:
                await self._crawl_article(
                    link_title,
                    depth,
                    max_entities,
                    current_depth + 1
                )
        
        # Get categories
        if current_depth < depth:
            categories = await self._fetch_article_categories(article_title, limit=5)
            
            for category in categories:
                if len(self.discovered_nodes) >= max_entities:
                    break
                
                category_title = category.get("title", "")
                if not category_title:
                    continue
                
                # Create category node
                category_node = await self.create_or_update_node(
                    entity_type="category",
                    entity_id=category_title.lower(),
                    display_name=category_title,
                    metadata={}
                )
                
                # Create edge: article belongs to category
                await self.create_edge(
                    source_node=article_node,
                    target_node=category_node,
                    relationship_type="in_category",
                    weight=1.0
                )
    
    async def _fetch_article_info(
        self,
        article_title: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch article information."""
        params = {
            "action": "query",
            "format": "json",
            "titles": article_title,
            "prop": "info|extracts|categories",
            "inprop": "url",
            "exintro": True,
            "explaintext": True,
            "exsentences": 3,
            "cllimit": 10
        }
        
        try:
            data = await self.fetch_with_rate_limit(
                self.BASE_URL,
                headers=self.headers,
                params=params
            )
            
            pages = data.get("query", {}).get("pages", {})
            if pages:
                # Get first (and should be only) page
                page_data = next(iter(pages.values()))
                if page_data.get("pageid"):  # Ensure page exists
                    return page_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching article {article_title}: {e}")
            return None
    
    async def _fetch_article_links(
        self,
        article_title: str,
        limit: int = 20
    ) -> List[str]:
        """Fetch outgoing links from an article."""
        params = {
            "action": "query",
            "format": "json",
            "titles": article_title,
            "prop": "links",
            "pllimit": limit,
            "plnamespace": 0  # Only main namespace articles
        }
        
        try:
            data = await self.fetch_with_rate_limit(
                self.BASE_URL,
                headers=self.headers,
                params=params
            )
            
            pages = data.get("query", {}).get("pages", {})
            if pages:
                page_data = next(iter(pages.values()))
                links = page_data.get("links", [])
                return [link["title"] for link in links if "title" in link]
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching links for {article_title}: {e}")
            return []
    
    async def _fetch_article_categories(
        self,
        article_title: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch categories for an article."""
        params = {
            "action": "query",
            "format": "json",
            "titles": article_title,
            "prop": "categories",
            "cllimit": limit,
            "clshow": "!hidden"  # Exclude hidden categories
        }
        
        try:
            data = await self.fetch_with_rate_limit(
                self.BASE_URL,
                headers=self.headers,
                params=params
            )
            
            pages = data.get("query", {}).get("pages", {})
            if pages:
                page_data = next(iter(pages.values()))
                return page_data.get("categories", [])
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching categories for {article_title}: {e}")
            return []
    
    async def _fetch_backlinks(
        self,
        article_title: str,
        limit: int = 10
    ) -> List[str]:
        """Fetch articles that link to this article."""
        params = {
            "action": "query",
            "format": "json",
            "list": "backlinks",
            "bltitle": article_title,
            "bllimit": limit,
            "blnamespace": 0
        }
        
        try:
            data = await self.fetch_with_rate_limit(
                self.BASE_URL,
                headers=self.headers,
                params=params
            )
            
            backlinks = data.get("query", {}).get("backlinks", [])
            return [bl["title"] for bl in backlinks if "title" in bl]
            
        except Exception as e:
            logger.error(f"Error fetching backlinks for {article_title}: {e}")
            return []
