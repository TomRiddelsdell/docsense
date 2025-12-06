import pytest
from unittest.mock import patch, AsyncMock

from src.infrastructure.ai.provider_factory import ProviderFactory
from src.infrastructure.ai.base import ProviderType
from src.infrastructure.ai.rate_limiter import RateLimitConfig


class TestProviderFactory:
    @pytest.fixture
    def factory(self):
        return ProviderFactory()

    def test_get_rate_limiter(self, factory):
        limiter1 = factory.get_rate_limiter(ProviderType.GEMINI)
        limiter2 = factory.get_rate_limiter(ProviderType.GEMINI)
        
        assert limiter1 is limiter2

    def test_different_rate_limiters_per_provider(self, factory):
        gemini_limiter = factory.get_rate_limiter(ProviderType.GEMINI)
        openai_limiter = factory.get_rate_limiter(ProviderType.OPENAI)
        
        assert gemini_limiter is not openai_limiter

    def test_get_default_provider(self, factory):
        with patch.dict('os.environ', {
            'AI_INTEGRATIONS_GEMINI_API_KEY': 'test-key',
            'AI_INTEGRATIONS_GEMINI_BASE_URL': 'https://test.api',
        }):
            provider = factory.get_default_provider()
            assert provider.provider_type == ProviderType.GEMINI

    def test_get_gemini_provider(self, factory):
        with patch.dict('os.environ', {
            'AI_INTEGRATIONS_GEMINI_API_KEY': 'test-key',
            'AI_INTEGRATIONS_GEMINI_BASE_URL': 'https://test.api',
        }):
            provider = factory.get_provider(ProviderType.GEMINI)
            assert provider.provider_type == ProviderType.GEMINI

    def test_get_openai_provider(self, factory):
        with patch.dict('os.environ', {
            'AI_INTEGRATIONS_OPENAI_API_KEY': 'test-key',
            'AI_INTEGRATIONS_OPENAI_BASE_URL': 'https://test.api',
        }):
            provider = factory.get_provider(ProviderType.OPENAI)
            assert provider.provider_type == ProviderType.OPENAI

    def test_get_claude_provider(self, factory):
        with patch.dict('os.environ', {
            'AI_INTEGRATIONS_ANTHROPIC_API_KEY': 'test-key',
            'AI_INTEGRATIONS_ANTHROPIC_BASE_URL': 'https://test.api',
        }):
            provider = factory.get_provider(ProviderType.CLAUDE)
            assert provider.provider_type == ProviderType.CLAUDE

    def test_provider_caching(self, factory):
        with patch.dict('os.environ', {
            'AI_INTEGRATIONS_GEMINI_API_KEY': 'test-key',
            'AI_INTEGRATIONS_GEMINI_BASE_URL': 'https://test.api',
        }):
            provider1 = factory.get_provider(ProviderType.GEMINI)
            provider2 = factory.get_provider(ProviderType.GEMINI)
            
            assert provider1 is provider2

    def test_clear_cache(self, factory):
        with patch.dict('os.environ', {
            'AI_INTEGRATIONS_GEMINI_API_KEY': 'test-key',
            'AI_INTEGRATIONS_GEMINI_BASE_URL': 'https://test.api',
        }):
            provider1 = factory.get_provider(ProviderType.GEMINI)
            factory.clear_cache()
            provider2 = factory.get_provider(ProviderType.GEMINI)
            
            assert provider1 is not provider2

    def test_custom_rate_limit_config(self):
        config = RateLimitConfig(requests_per_minute=30)
        factory = ProviderFactory(rate_limit_config=config)
        
        limiter = factory.get_rate_limiter(ProviderType.GEMINI)
        stats = limiter.get_stats()
        
        assert stats["minute_limit"] == 30
