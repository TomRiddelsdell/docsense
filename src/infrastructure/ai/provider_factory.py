from typing import TYPE_CHECKING

from .base import AIProvider, ProviderType
from .rate_limiter import RateLimiter, RateLimitConfig

if TYPE_CHECKING:
    from .gemini_provider import GeminiProvider
    from .openai_provider import OpenAIProvider
    from .claude_provider import ClaudeProvider


class ProviderFactory:
    _instances: dict[ProviderType, AIProvider] = {}
    _rate_limiters: dict[ProviderType, RateLimiter] = {}

    def __init__(self, rate_limit_config: RateLimitConfig | None = None):
        self._rate_limit_config = rate_limit_config or RateLimitConfig()

    def get_provider(self, provider_type: ProviderType) -> AIProvider:
        if provider_type not in self._instances:
            self._instances[provider_type] = self._create_provider(provider_type)
        return self._instances[provider_type]

    def get_rate_limiter(self, provider_type: ProviderType) -> RateLimiter:
        if provider_type not in self._rate_limiters:
            self._rate_limiters[provider_type] = RateLimiter(self._rate_limit_config)
        return self._rate_limiters[provider_type]

    def _create_provider(self, provider_type: ProviderType) -> AIProvider:
        rate_limiter = self.get_rate_limiter(provider_type)
        
        if provider_type == ProviderType.GEMINI:
            from .gemini_provider import GeminiProvider
            return GeminiProvider(rate_limiter=rate_limiter)
        elif provider_type == ProviderType.OPENAI:
            from .openai_provider import OpenAIProvider
            return OpenAIProvider(rate_limiter=rate_limiter)
        elif provider_type == ProviderType.CLAUDE:
            from .claude_provider import ClaudeProvider
            return ClaudeProvider(rate_limiter=rate_limiter)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def get_default_provider(self) -> AIProvider:
        return self.get_provider(ProviderType.GEMINI)

    async def get_available_providers(self) -> list[ProviderType]:
        available = []
        for provider_type in ProviderType:
            try:
                provider = self.get_provider(provider_type)
                if await provider.is_available():
                    available.append(provider_type)
            except Exception:
                continue
        return available

    def clear_cache(self) -> None:
        self._instances.clear()
        self._rate_limiters.clear()
