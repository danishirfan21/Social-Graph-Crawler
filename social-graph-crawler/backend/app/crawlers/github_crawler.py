"""
GitHub crawler for discovering repository and contributor relationships.
Uses GitHub REST API (requires authentication token for better rate limits).
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.crawlers.base import BaseCrawler
from app.models import CrawlJob, CrawlStatus
from app.config import settings


logger = logging.getLogger(__name__)


class GitHubCrawler(BaseCrawler):
    """
    Crawls GitHub to discover:
    - Repositories and their contributors
    - User relationships (followers, following)
    - Organization memberships
    - Starred repositories
    - Fork relationships
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": settings.REDDIT_USER_AGENT
        }
        if settings.GITHUB_TOKEN:
            self.headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    
    def get_source_name(self) -> str:
        return "github"
    
    async def crawl(
        self,
        start_entity: str,
        depth: int = 2,
        max_entities: int = 100
    ) -> CrawlJob:
        """
        Crawl GitHub starting from a user or repository.
        
        Args:
            start_entity: Username or 'owner/repo' format
            depth: Crawl depth
            max_entities: Maximum entities to discover
        
        Returns:
            CrawlJob with statistics
        """
        job = await self.create_crawl_job()
        
        try:
            await self.update_crawl_job(job, CrawlStatus.RUNNING)
            
            # Determine if it's a user or repo
            if "/" in start_entity:
                # It's a repository
                owner, repo_name = start_entity.split("/", 1)
                await self._crawl_repository(owner, repo_name, depth, max_entities)
            else:
                # It's a user
                await self._crawl_user(start_entity, depth, max_entities)
            
            # Update job statistics
            await self.update_crawl_job(
                job,
                CrawlStatus.COMPLETED,
                entity_count=len(self.discovered_nodes),
                edge_count=len(self.discovered_edges)
            )
            
            await self.db.commit()
            logger.info(
                f"GitHub crawl completed: {len(self.discovered_nodes)} nodes, "
                f"{len(self.discovered_edges)} edges"
            )
            
        except Exception as e:
            logger.error(f"GitHub crawl failed: {e}")
            await self.update_crawl_job(
                job,
                CrawlStatus.FAILED,
                error_message=str(e)
            )
            await self.db.commit()
            raise
        
        return job
    
    async def _crawl_user(
        self,
        username: str,
        depth: int,
        max_entities: int
    ):
        """Crawl a GitHub user and their relationships."""
        if len(self.discovered_nodes) >= max_entities:
            return
        
        # Get user info
        user_data = await self._fetch_user_info(username)
        if not user_data:
            logger.warning(f"Could not fetch user: {username}")
            return
        
        # Create user node
        user_node = await self.create_or_update_node(
            entity_type="user",
            entity_id=username.lower(),
            display_name=user_data.get("login", username),
            metadata={
                "name": user_data.get("name", ""),
                "bio": user_data.get("bio", ""),
                "public_repos": user_data.get("public_repos", 0),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "created_at": user_data.get("created_at", ""),
                "location": user_data.get("location", "")
            }
        )
        
        if depth < 2:
            return
        
        # Get user's repositories
        repos = await self._fetch_user_repos(username, per_page=20)
        
        for repo in repos:
            if len(self.discovered_nodes) >= max_entities:
                break
            
            repo_name = repo.get("name")
            if not repo_name:
                continue
            
            # Create repository node
            repo_node = await self.create_or_update_node(
                entity_type="repository",
                entity_id=f"{username}/{repo_name}".lower(),
                display_name=repo.get("full_name", f"{username}/{repo_name}"),
                metadata={
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "language": repo.get("language", ""),
                    "created_at": repo.get("created_at", ""),
                    "updated_at": repo.get("updated_at", ""),
                    "topics": repo.get("topics", [])
                }
            )
            
            # Create edge: user owns repository
            await self.create_edge(
                source_node=user_node,
                target_node=repo_node,
                relationship_type="owns",
                weight=1.0,
                metadata={
                    "is_fork": repo.get("fork", False),
                    "is_private": repo.get("private", False)
                }
            )
            
            # If depth allows, get contributors
            if depth >= 3:
                await self._crawl_repository_contributors(
                    username,
                    repo_name,
                    repo_node,
                    max_contributors=10
                )
        
        # Get followers (sample)
        if depth >= 2:
            followers = await self._fetch_user_followers(username, per_page=15)
            for follower in followers:
                if len(self.discovered_nodes) >= max_entities:
                    break
                
                follower_login = follower.get("login")
                if not follower_login:
                    continue
                
                follower_node = await self.create_or_update_node(
                    entity_type="user",
                    entity_id=follower_login.lower(),
                    display_name=follower_login,
                    metadata={}
                )
                
                await self.create_edge(
                    source_node=follower_node,
                    target_node=user_node,
                    relationship_type="follows",
                    weight=1.0
                )
    
    async def _crawl_repository(
        self,
        owner: str,
        repo_name: str,
        depth: int,
        max_entities: int
    ):
        """Crawl a GitHub repository and its contributors."""
        if len(self.discovered_nodes) >= max_entities:
            return
        
        # Get repo info
        repo_data = await self._fetch_repo_info(owner, repo_name)
        if not repo_data:
            logger.warning(f"Could not fetch repo: {owner}/{repo_name}")
            return
        
        # Create repository node
        repo_node = await self.create_or_update_node(
            entity_type="repository",
            entity_id=f"{owner}/{repo_name}".lower(),
            display_name=repo_data.get("full_name", f"{owner}/{repo_name}"),
            metadata={
                "description": repo_data.get("description", ""),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "language": repo_data.get("language", ""),
                "created_at": repo_data.get("created_at", ""),
                "topics": repo_data.get("topics", [])
            }
        )
        
        if depth < 2:
            return
        
        # Get contributors
        await self._crawl_repository_contributors(
            owner,
            repo_name,
            repo_node,
            max_contributors=25
        )
    
    async def _crawl_repository_contributors(
        self,
        owner: str,
        repo_name: str,
        repo_node,
        max_contributors: int = 25
    ):
        """Crawl repository contributors."""
        contributors = await self._fetch_repo_contributors(
            owner,
            repo_name,
            per_page=max_contributors
        )
        
        for contributor in contributors:
            if len(self.discovered_nodes) >= 1000:  # Safety limit
                break
            
            login = contributor.get("login")
            if not login:
                continue
            
            contributor_node = await self.create_or_update_node(
                entity_type="user",
                entity_id=login.lower(),
                display_name=login,
                metadata={
                    "contributions": contributor.get("contributions", 0)
                }
            )
            
            # Create edge: user contributes to repository
            await self.create_edge(
                source_node=contributor_node,
                target_node=repo_node,
                relationship_type="contributes_to",
                weight=min(contributor.get("contributions", 1) / 100.0, 1.0),
                metadata={
                    "contributions": contributor.get("contributions", 0)
                }
            )
    
    async def _fetch_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch user information."""
        url = f"{self.BASE_URL}/users/{username}"
        try:
            return await self.fetch_with_rate_limit(url, headers=self.headers)
        except Exception as e:
            logger.error(f"Error fetching user {username}: {e}")
            return None
    
    async def _fetch_user_repos(
        self,
        username: str,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """Fetch user's repositories."""
        url = f"{self.BASE_URL}/users/{username}/repos"
        params = {"per_page": per_page, "sort": "updated"}
        
        try:
            return await self.fetch_with_rate_limit(
                url,
                headers=self.headers,
                params=params
            )
        except Exception as e:
            logger.error(f"Error fetching repos for {username}: {e}")
            return []
    
    async def _fetch_user_followers(
        self,
        username: str,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """Fetch user's followers."""
        url = f"{self.BASE_URL}/users/{username}/followers"
        params = {"per_page": per_page}
        
        try:
            return await self.fetch_with_rate_limit(
                url,
                headers=self.headers,
                params=params
            )
        except Exception as e:
            logger.error(f"Error fetching followers for {username}: {e}")
            return []
    
    async def _fetch_repo_info(
        self,
        owner: str,
        repo_name: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch repository information."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo_name}"
        try:
            return await self.fetch_with_rate_limit(url, headers=self.headers)
        except Exception as e:
            logger.error(f"Error fetching repo {owner}/{repo_name}: {e}")
            return None
    
    async def _fetch_repo_contributors(
        self,
        owner: str,
        repo_name: str,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """Fetch repository contributors."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/contributors"
        params = {"per_page": per_page}
        
        try:
            return await self.fetch_with_rate_limit(
                url,
                headers=self.headers,
                params=params
            )
        except Exception as e:
            logger.error(f"Error fetching contributors for {owner}/{repo_name}: {e}")
            return []
