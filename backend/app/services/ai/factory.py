from app.services.ai.base import AIProvider
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class AIProviderFactory:
    _providers: dict[str, AIProvider] = {}

    @classmethod
    def get_provider(cls, provider_name: str | None = None) -> AIProvider:
        settings = get_settings()
        name = provider_name or settings.ai_provider

        if name in cls._providers:
            return cls._providers[name]

        provider = cls._create_provider(name)
        cls._providers[name] = provider
        logger.info("ai_provider_created", provider=name)
        return provider

    @classmethod
    def _create_provider(cls, name: str) -> AIProvider:
        if name == "mock":
            return MockAIProvider()
        elif name == "openai":
            return OpenAIProvider()
        elif name == "gemini":
            return cls._create_gemini_provider()
        elif name == "anthropic":
            return cls._create_anthropic_provider()
        else:
            logger.warning("unknown_ai_provider_fallback_mock", provider=name)
            return MockAIProvider()

    @classmethod
    def _create_gemini_provider(cls) -> AIProvider:
        from app.services.ai.gemini_provider import GeminiProvider
        settings = get_settings()
        if not settings.gemini_api_key:
            logger.warning("gemini_api_key_missing_fallback_mock")
            return MockAIProvider()
        return GeminiProvider(api_key=settings.gemini_api_key)

    @classmethod
    def _create_anthropic_provider(cls) -> AIProvider:
        from app.services.ai.anthropic_provider import AnthropicProvider
        settings = get_settings()
        if not settings.anthropic_api_key:
            logger.warning("anthropic_api_key_missing_fallback_mock")
            return MockAIProvider()
        return AnthropicProvider(api_key=settings.anthropic_api_key)

    @classmethod
    def clear_cache(cls) -> None:
        cls._providers.clear()