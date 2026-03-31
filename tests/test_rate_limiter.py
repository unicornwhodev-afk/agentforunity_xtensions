"""Tests for the RateLimiter class."""
import time
import pytest
from src.api.main import RateLimiter


def test_rate_limiter_allows_requests():
    """Test rate limiter allows requests within limit."""
    rl = RateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        assert rl.is_allowed("key1") is True


def test_rate_limiter_blocks_excess():
    """Test rate limiter blocks requests over limit."""
    rl = RateLimiter(max_requests=2, window_seconds=60)
    assert rl.is_allowed("key1") is True
    assert rl.is_allowed("key1") is True
    assert rl.is_allowed("key1") is False


def test_rate_limiter_different_keys():
    """Test rate limiter tracks keys independently."""
    rl = RateLimiter(max_requests=1, window_seconds=60)
    assert rl.is_allowed("key1") is True
    assert rl.is_allowed("key1") is False
    assert rl.is_allowed("key2") is True


def test_rate_limiter_remaining():
    """Test remaining count."""
    rl = RateLimiter(max_requests=3, window_seconds=60)
    assert rl.remaining("key1") == 3
    rl.is_allowed("key1")
    assert rl.remaining("key1") == 2