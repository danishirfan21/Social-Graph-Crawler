"""
Base crawler class with common functionality for all crawlers.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from uuid import UUID
import aiohttp
from aiohttp import ClientSession, ClientTimeout
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models import Node, Edge, CrawlJob, CrawlStatus


logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple token bucket rate limiter."""
    
    def __init__(self, requests_per_second: float):
        self.requests_per_second = requests_per_second
        self.tokens = requests_per_second
        self.updated_at = asyncio.get_event_loop().time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary."""
        async with self.lock:
            while self.tokens < 1:
                now = asyncio.get_event_loop().time()
                elapsed = now - self.updated_at
                self.tokens = min(
                    self.requests_per_second,
                    self.tokens + elapsed * self.requests_per_second
                )
                self.updated_at = now
                
                if self.tokens < 1:
                    await asyncio.sleep(0.1)
            
            self.tokens -= 1


class BaseCrawler(ABC):
    """
    Abstract base class for all crawlers.
    Provides common functionality for rate limiting, error handling, and data storage.
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        rate_limit: float = 10.0,  # requests per second
        timeout: int = 30,
    ):
        self.db = db_session
        self.rate_limiter = RateLimiter(rate_limit)
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[ClientSession] = None
        self.discovered_nodes: Set[str] = set()
        self.discovered_edges: Set[tuple] = set()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of the data source (e.g., 'reddit', 'github')."""
        pass
    
    @abstractmethod
    async def crawl(
        self,
        start_entity: str,
        depth: int = 2,
        max_entities: int = 100
    ) -> CrawlJob:
        """
        Main crawl method to be implemented by subclasses.
        
        Args:
            start_entity: Starting point for crawl (username, repo name, etc.)
            depth: How many levels deep to crawl
            max_entities: Maximum number of entities to discover
        
        Returns:
            CrawlJob with statistics
        """
        pass
    
    async def fetch_with_rate_limit(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetch URL with rate limiting and error handling.
        
        Args:
            url: URL to fetch
            headers: Optional HTTP headers
            params: Optional query parameters
        
        Returns:
            Parsed JSON response
        
        Raises:
            aiohttp.ClientError: On HTTP errors
        """
        await self.rate_limiter.acquire()
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 429:  # Too Many Requests
                logger.warning(f"Rate limit hit for {url}, backing off...")
                await asyncio.sleep(60)  # Wait 1 minute
                return await self.fetch_with_rate_limit(url, headers, params)
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise
    
    async def create_or_update_node(
        self,
        entity_type: str,
        entity_id: str,
        display_name: str,
        metadata: Optional[Dict] = None
    ) -> Node:
        """
        Create or update a node in the database.
        
        Args:
            entity_type: Type of entity
            entity_id: External ID
            display_name: Human-readable name
            metadata: Optional metadata
        
        Returns:
            Node instance
        """
        source = self.get_source_name()
        unique_key = f"{source}:{entity_type}:{entity_id}"
        
        if unique_key in self.discovered_nodes:
            # Already processed in this session
            result = await self.db.execute(
                select(Node).where(
                    Node.source == source,
                    Node.entity_type == entity_type,
                    Node.entity_id == entity_id
                )
            )
            return result.scalar_one()
        
        # Check if node exists
        result = await self.db.execute(
            select(Node).where(
                Node.source == source,
                Node.entity_type == entity_type,
                Node.entity_id == entity_id
            )
        )
        node = result.scalar_one_or_none()
        
        if node:
            # Update existing node
            node.display_name = display_name
            if metadata:
                node.metadata = {**node.metadata, **metadata}
        else:
            # Create new node
            node = Node(
                entity_type=entity_type,
                entity_id=entity_id,
                source=source,
                display_name=display_name,
                metadata=metadata or {}
            )
            self.db.add(node)
        
        await self.db.flush()
        self.discovered_nodes.add(unique_key)
        return node
    
    async def create_edge(
        self,
        source_node: Node,
        target_node: Node,
        relationship_type: str,
        weight: float = 1.0,
        metadata: Optional[Dict] = None
    ) -> Optional[Edge]:
        """
        Create an edge between two nodes.
        
        Args:
            source_node: Source node
            target_node: Target node
            relationship_type: Type of relationship
            weight: Edge weight
            metadata: Optional metadata
        
        Returns:
            Edge instance or None if already exists
        """
        edge_key = (source_node.id, target_node.id, relationship_type)
        
        if edge_key in self.discovered_edges:
            return None
        
        # Check if edge exists
        result = await self.db.execute(
            select(Edge).where(
                Edge.source_node_id == source_node.id,
                Edge.target_node_id == target_node.id,
                Edge.relationship_type == relationship_type
            )
        )
        edge = result.scalar_one_or_none()
        
        if edge:
            # Update weight (average with existing)
            edge.weight = (edge.weight + weight) / 2
            if metadata:
                edge.metadata = {**edge.metadata, **metadata}
        else:
            edge = Edge(
                source_node_id=source_node.id,
                target_node_id=target_node.id,
                relationship_type=relationship_type,
                weight=weight,
                metadata=metadata or {}
            )
            self.db.add(edge)
        
        await self.db.flush()
        self.discovered_edges.add(edge_key)
        return edge
    
    async def create_crawl_job(self) -> CrawlJob:
        """Create a new crawl job record."""
        job = CrawlJob(
            source=self.get_source_name(),
            status=CrawlStatus.PENDING.value
        )
        self.db.add(job)
        await self.db.flush()
        return job
    
    async def update_crawl_job(
        self,
        job: CrawlJob,
        status: CrawlStatus,
        entity_count: Optional[int] = None,
        edge_count: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Update crawl job status and statistics."""
        job.status = status.value
        
        if entity_count is not None:
            job.entity_count = entity_count
        
        if edge_count is not None:
            job.edge_count = edge_count
        
        if error_message:
            job.error_message = error_message
        
        if status == CrawlStatus.RUNNING and not job.started_at:
            from datetime import datetime
            job.started_at = datetime.utcnow()
        
        if status in {CrawlStatus.COMPLETED, CrawlStatus.FAILED}:
            from datetime import datetime
            job.completed_at = datetime.utcnow()
        
        await self.db.flush()