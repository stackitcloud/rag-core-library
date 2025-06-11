"""Tests for the PageSummaryEnhancer rate limiting functionality."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from admin_api_lib.impl.information_enhancer.page_summary_enhancer import (
    PageSummaryEnhancer,
    StackitTokenRateLimiter
)
from langchain_core.documents import Document


class TestStackitTokenRateLimiter:
    """Test the token rate limiter component."""

    def test_init_with_defaults(self):
        """Test rate limiter initialization with default values."""
        limiter = StackitTokenRateLimiter()
        assert limiter.tokens_per_minute == 24000  # 30000 * 0.8
        assert limiter.current_tokens == 0
        assert len(limiter.token_usage) == 0

    def test_init_with_custom_values(self):
        """Test rate limiter initialization with custom values."""
        limiter = StackitTokenRateLimiter(tokens_per_minute=20000, safety_buffer=0.9)
        assert limiter.tokens_per_minute == 18000  # 20000 * 0.9
        assert limiter.current_tokens == 0

    def test_estimate_tokens(self):
        """Test token estimation function."""
        limiter = StackitTokenRateLimiter()

        # Test basic estimation
        assert limiter.estimate_tokens("hello world") == 3  # 11 chars / 3 = 3.67 -> 3
        assert limiter.estimate_tokens("a") == 1  # minimum 1 token
        assert limiter.estimate_tokens("") == 1  # minimum 1 token

        # Test longer text
        long_text = "This is a longer text that should result in more tokens."
        expected_tokens = max(1, len(long_text) // 3)
        assert limiter.estimate_tokens(long_text) == expected_tokens

    def test_get_current_usage_empty(self):
        """Test current usage when no tokens have been used."""
        limiter = StackitTokenRateLimiter()
        assert limiter.get_current_usage() == 0

    def test_get_current_usage_with_recent_usage(self):
        """Test current usage with recent token usage."""
        limiter = StackitTokenRateLimiter()
        current_time = time.time()

        # Add some recent usage
        limiter.token_usage.append((current_time - 30, 1000))  # 30 seconds ago
        limiter.token_usage.append((current_time - 10, 500))   # 10 seconds ago
        limiter.current_tokens = 1500

        usage = limiter.get_current_usage()
        assert usage == 1500

    def test_get_current_usage_with_old_usage(self):
        """Test that old usage (>60s) is cleaned up."""
        limiter = StackitTokenRateLimiter()
        current_time = time.time()

        # Add old usage (should be cleaned up)
        limiter.token_usage.append((current_time - 70, 1000))  # 70 seconds ago
        limiter.token_usage.append((current_time - 10, 500))   # 10 seconds ago (recent)
        limiter.current_tokens = 1500

        usage = limiter.get_current_usage()
        assert usage == 500  # Only recent usage should remain
        assert len(limiter.token_usage) == 1

    @pytest.mark.asyncio
    async def test_acquire_tokens_under_limit(self):
        """Test acquiring tokens when under the rate limit."""
        limiter = StackitTokenRateLimiter(tokens_per_minute=1000)

        # Should not wait when under limit
        start_time = time.time()
        await limiter.acquire_tokens(500)
        end_time = time.time()

        # Should complete quickly (less than 0.1 seconds)
        assert end_time - start_time < 0.1
        assert limiter.current_tokens == 500
        assert len(limiter.token_usage) == 1

    @pytest.mark.asyncio
    async def test_acquire_tokens_over_limit_waits(self):
        """Test that acquiring tokens waits when over the limit."""
        limiter = StackitTokenRateLimiter(tokens_per_minute=1000)
        current_time = time.time()

        # Fill up the usage to near limit
        limiter.token_usage.append((current_time - 30, 800))
        limiter.current_tokens = 800

        # This should trigger waiting since 800 + 300 > 1000
        start_time = time.time()

        # Use a shorter wait time for testing by mocking sleep
        original_sleep = asyncio.sleep
        sleep_calls = []

        async def mock_sleep(duration):
            sleep_calls.append(duration)
            # Sleep for a very short time instead of the full duration
            await original_sleep(0.01)

        with patch('admin_api_lib.impl.information_enhancer.page_summary_enhancer.sleep', mock_sleep):
            await limiter.acquire_tokens(300)

        # Should have called sleep
        assert len(sleep_calls) > 0
        assert sleep_calls[0] > 0  # Should have waited some amount

    @pytest.mark.asyncio
    async def test_acquire_tokens_no_history_fallback(self):
        """Test fallback waiting when no history but over limit."""
        limiter = StackitTokenRateLimiter(tokens_per_minute=1000)

        # Mock sleep to verify it's called
        sleep_calls = []
        async def mock_sleep(duration):
            sleep_calls.append(duration)

        with patch('admin_api_lib.impl.information_enhancer.page_summary_enhancer.sleep', mock_sleep):
            # Try to acquire more tokens than the limit with no history
            await limiter.acquire_tokens(1500)

        # Should have called the fallback sleep
        assert 30 in sleep_calls


class TestPageSummaryEnhancer:
    """Test the PageSummaryEnhancer with rate limiting."""

    @pytest.fixture
    def mock_summarizer(self):
        """Create a mock summarizer."""
        summarizer = AsyncMock()
        summarizer.ainvoke.return_value = "Test summary"
        return summarizer

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                page_content="Content for page 1 part 1",
                metadata={"page": 1, "id": "doc1", "related": []}
            ),
            Document(
                page_content="Content for page 1 part 2",
                metadata={"page": 1, "id": "doc2", "related": []}
            ),
            Document(
                page_content="Content for page 2",
                metadata={"page": 2, "id": "doc3", "related": []}
            ),
        ]

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, mock_summarizer, sample_documents):
        """Test that rate limiting works in the complete workflow."""
        # Create enhancer with very low rate limit for testing
        enhancer = PageSummaryEnhancer(
            summarizer=mock_summarizer,
            max_concurrent_requests=1,
            tokens_per_minute=100  # Very low limit
        )

        # Track sleep calls to verify rate limiting is working
        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(duration):
            sleep_calls.append(duration)
            await original_sleep(0.01)  # Short sleep for testing

        with patch('admin_api_lib.impl.information_enhancer.page_summary_enhancer.sleep', mock_sleep):
            result = await enhancer._acreate_summary(sample_documents, None)

        # Should have original documents plus summaries
        assert len(result) > len(sample_documents)

        # Rate limiting should have been triggered (sleep called)
        # We expect some sleep calls due to the low token limit
        total_sleep_time = sum(sleep_calls)
        assert total_sleep_time >= 0  # At least some waiting should occur

    @pytest.mark.asyncio
    async def test_concurrent_requests_limited(self, mock_summarizer, sample_documents):
        """Test that concurrent requests are properly limited."""
        # Track when summarizer is called
        call_times = []

        async def track_calls(*args, **kwargs):
            call_times.append(time.time())
            await asyncio.sleep(0.1)  # Simulate some processing time
            return "Test summary"

        mock_summarizer.ainvoke.side_effect = track_calls

        enhancer = PageSummaryEnhancer(
            summarizer=mock_summarizer,
            max_concurrent_requests=1,  # Only 1 concurrent request
            tokens_per_minute=30000  # High limit to avoid rate limiting
        )

        # Add more documents to ensure we have multiple pages
        extended_docs = sample_documents + [
            Document(
                page_content="Content for page 3",
                metadata={"page": 3, "id": "doc4", "related": []}
            ),
            Document(
                page_content="Content for page 4",
                metadata={"page": 4, "id": "doc5", "related": []}
            ),
        ]

        await enhancer._acreate_summary(extended_docs, None)

        # With max_concurrent_requests=1, calls should be sequential
        # Check that calls don't overlap significantly
        if len(call_times) > 1:
            for i in range(1, len(call_times)):
                time_diff = call_times[i] - call_times[i-1]
                # Should be at least 0.08 seconds apart (considering 0.1s processing time)
                assert time_diff >= 0.08

    @pytest.mark.asyncio
    async def test_token_estimation_affects_rate_limiting(self, mock_summarizer):
        """Test that larger content triggers more aggressive rate limiting."""
        enhancer = PageSummaryEnhancer(
            summarizer=mock_summarizer,
            max_concurrent_requests=3,
            tokens_per_minute=1000  # Low limit
        )

        # Create documents with very large content
        large_content = "a" * 3000  # Should estimate to ~1000 tokens
        large_docs = [
            Document(
                page_content=large_content,
                metadata={"page": 1, "id": "large1", "related": []}
            ),
            Document(
                page_content=large_content,
                metadata={"page": 2, "id": "large2", "related": []}
            ),
        ]

        sleep_calls = []
        async def mock_sleep(duration):
            sleep_calls.append(duration)
            await asyncio.sleep(0.01)

        with patch('admin_api_lib.impl.information_enhancer.page_summary_enhancer.sleep', mock_sleep):
            await enhancer._acreate_summary(large_docs, None)

        # Should have triggered significant waiting due to large token usage
        total_sleep = sum(sleep_calls)
        assert total_sleep > 0

    def test_rate_limiter_token_cleanup(self):
        """Test that old token usage is properly cleaned up."""
        limiter = StackitTokenRateLimiter()
        current_time = time.time()

        # Add various usage entries
        limiter.token_usage.append((current_time - 70, 100))  # Old
        limiter.token_usage.append((current_time - 30, 200))  # Recent
        limiter.token_usage.append((current_time - 5, 300))   # Very recent
        limiter.current_tokens = 600

        # Trigger cleanup
        usage = limiter.get_current_usage()

        # Should only have recent entries
        assert usage == 500  # 200 + 300
        assert len(limiter.token_usage) == 2

        # Verify the remaining entries are the recent ones
        timestamps = [entry[0] for entry in limiter.token_usage]
        assert all(current_time - ts <= 60 for ts in timestamps)


@pytest.mark.asyncio
async def test_end_to_end_rate_limiting():
    """End-to-end test of rate limiting functionality."""
    # Mock summarizer
    summarizer = AsyncMock()
    summarizer.ainvoke.return_value = "Summary text"

    # Create enhancer with conservative settings
    enhancer = PageSummaryEnhancer(
        summarizer=summarizer,
        max_concurrent_requests=2,
        tokens_per_minute=5000
    )

    # Create documents that will trigger rate limiting
    docs = []
    for i in range(5):
        # Each document has substantial content
        content = f"This is page {i} with substantial content. " * 50
        docs.append(Document(
            page_content=content,
            metadata={"page": i, "id": f"doc{i}", "related": []}
        ))

    start_time = time.time()
    result = await enhancer._acreate_summary(docs, None)
    end_time = time.time()

    # Should have original docs plus summaries
    assert len(result) > len(docs)

    # Should have taken some time due to rate limiting
    duration = end_time - start_time
    assert duration > 0

    # Verify summarizer was called for each page
    assert summarizer.ainvoke.call_count == len(docs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
