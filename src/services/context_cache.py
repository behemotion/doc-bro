"""Context cache service for performance optimization.

Provides 5-minute TTL caching for context detection to avoid repeated database queries
within command sessions.
"""

import asyncio
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.models.command_context import CommandContext


@dataclass
class CacheEntry:
    """Single cache entry with TTL and data."""

    data: CommandContext
    created_at: datetime
    ttl_seconds: int = 300  # 5 minutes default

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = datetime.now() - self.created_at
        return age.total_seconds() > self.ttl_seconds


class ContextCache:
    """Performance optimization cache for context detection results.

    Caches CommandContext objects for 5 minutes to prevent repeated database
    queries for the same entity within a command session.
    """

    def __init__(self, default_ttl: int = 300):
        """Initialize context cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._last_cleanup = datetime.now()

    def _make_key(self, entity_type: str, entity_name: str) -> str:
        """Create cache key from entity type and name."""
        return f"{entity_type}:{entity_name}"

    async def get(self, entity_type: str, entity_name: str) -> Optional[CommandContext]:
        """Get cached context if available and not expired.

        Args:
            entity_type: Type of entity ('shelf' or 'box')
            entity_name: Name of the entity

        Returns:
            Cached CommandContext if available and fresh, None otherwise
        """
        key = self._make_key(entity_type, entity_name)

        # Clean up expired entries periodically
        await self._cleanup_if_needed()

        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            # Remove expired entry
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return entry.data

    async def set(self, context: CommandContext, ttl: Optional[int] = None) -> None:
        """Cache a context object.

        Args:
            context: CommandContext to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        key = self._make_key(context.entity_type, context.entity_name)
        ttl = ttl or self.default_ttl

        entry = CacheEntry(
            data=context,
            created_at=datetime.now(),
            ttl_seconds=ttl
        )

        self._cache[key] = entry

        # Clean up periodically
        await self._cleanup_if_needed()

    async def invalidate(self, entity_type: str, entity_name: str) -> bool:
        """Invalidate cached context for specific entity.

        Args:
            entity_type: Type of entity ('shelf' or 'box')
            entity_name: Name of the entity

        Returns:
            True if entry was found and removed, False otherwise
        """
        key = self._make_key(entity_type, entity_name)

        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cached contexts matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "shelf:*" for all shelves)

        Returns:
            Number of entries invalidated
        """
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            keys_to_remove = [key for key in self._cache.keys() if key.startswith(prefix)]
        else:
            keys_to_remove = [key for key in self._cache.keys() if key == pattern]

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)

    async def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    async def _cleanup_if_needed(self) -> None:
        """Clean up expired entries if enough time has passed."""
        now = datetime.now()
        time_since_cleanup = now - self._last_cleanup

        # Cleanup every 60 seconds
        if time_since_cleanup.total_seconds() > 60:
            await self._cleanup_expired()
            self._last_cleanup = now

    async def _cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache performance metrics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_entries": len(self._cache),
            "last_cleanup": self._last_cleanup.isoformat(),
            "default_ttl_seconds": self.default_ttl
        }

    async def get_entry_info(self, entity_type: str, entity_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific cache entry.

        Args:
            entity_type: Type of entity ('shelf' or 'box')
            entity_name: Name of the entity

        Returns:
            Dictionary with entry information or None if not found
        """
        key = self._make_key(entity_type, entity_name)
        entry = self._cache.get(key)

        if entry is None:
            return None

        age_seconds = (datetime.now() - entry.created_at).total_seconds()
        remaining_seconds = max(0, entry.ttl_seconds - age_seconds)

        return {
            "key": key,
            "created_at": entry.created_at.isoformat(),
            "age_seconds": round(age_seconds, 2),
            "ttl_seconds": entry.ttl_seconds,
            "remaining_seconds": round(remaining_seconds, 2),
            "is_expired": entry.is_expired,
            "entity_exists": entry.data.exists,
            "entity_is_empty": entry.data.is_empty
        }


# Global cache instance for shared use across context service
_global_cache: Optional[ContextCache] = None


def get_context_cache() -> ContextCache:
    """Get the global context cache instance.

    Returns:
        Global ContextCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ContextCache()
    return _global_cache


async def clear_global_cache() -> None:
    """Clear the global context cache."""
    cache = get_context_cache()
    await cache.clear()


async def get_cache_stats() -> Dict[str, Any]:
    """Get global context cache statistics.

    Returns:
        Dictionary with cache performance metrics
    """
    cache = get_context_cache()
    return cache.get_stats()