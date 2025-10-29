"""
Dependency injection utilities for FastAPI routes.
"""

from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


async def get_current_session(
    db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    """
    Get current database session.
    This can be extended to include authentication/authorization.
    """
    return db


# Example: Add authentication dependencies here
# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     ...
