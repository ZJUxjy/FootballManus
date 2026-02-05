"""LLM Client for FM Manager.

Provides unified interface for multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Local LLM support (via compatible API)

Features:
- Response caching
- Token usage tracking
- Retry with exponential backoff
- Prompt templates
"""

import json
import os
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

# Try to import optional dependencies
try:
    import openai

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    MOCK = "mock"  # For testing


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    provider: LLMProvider
    model: str
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "provider": self.provider.value,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
        }


@dataclass
class TokenUsage:
    """Track token usage for cost monitoring."""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    requests_count: int = 0
    cache_hits: int = 0

    # Pricing per 1K tokens (approximate)
    PRICING = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
        "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
    }

    def add_usage(self, response: LLMResponse, model: str) -> None:
        """Add usage from a response."""
        if response.cached:
            self.cache_hits += 1
            return

        self.total_prompt_tokens += response.prompt_tokens
        self.total_completion_tokens += response.completion_tokens
        self.total_tokens += response.tokens_used
        self.requests_count += 1

        # Estimate cost
        pricing = self.PRICING.get(model, {"prompt": 0.002, "completion": 0.002})
        cost = (
            response.prompt_tokens / 1000 * pricing["prompt"]
            + response.completion_tokens / 1000 * pricing["completion"]
        )
        self.estimated_cost_usd += cost

    def to_dict(self) -> dict:
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "requests_count": self.requests_count,
            "cache_hits": self.cache_hits,
        }


class ResponseCache:
    """Simple in-memory cache for LLM responses."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[LLMResponse, float]] = {}

    def _make_key(self, prompt: str, model: str, **kwargs) -> str:
        """Create cache key from prompt and parameters."""
        key_data = {"prompt": prompt, "model": model, **kwargs}
        import hashlib

        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    def get(self, prompt: str, model: str, **kwargs) -> LLMResponse | None:
        """Get cached response if exists and not expired."""
        key = self._make_key(prompt, model, **kwargs)
        if key in self._cache:
            response, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                # Return cached response with cached flag
                cached_response = LLMResponse(
                    content=response.content,
                    provider=response.provider,
                    model=response.model,
                    cached=True,
                )
                return cached_response
            else:
                del self._cache[key]
        return None

    def set(self, prompt: str, model: str, response: LLMResponse, **kwargs) -> None:
        """Cache a response."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        key = self._make_key(prompt, model, **kwargs)
        self._cache[key] = (response, time.time())

    def clear(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class LLMClient:
    """Unified LLM client with multiple provider support."""

    # Default models
    DEFAULT_MODELS = {
        LLMProvider.OPENAI: "gpt-3.5-turbo",
        LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
        LLMProvider.LOCAL: "local-model",
        LLMProvider.MOCK: "mock-model",
    }

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.MOCK,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        enable_cache: bool = True,
        max_retries: int = 3,
    ):
        self.provider = provider
        self.model = model or self.DEFAULT_MODELS[provider]
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.enable_cache = enable_cache

        # Initialize cache
        self.cache = ResponseCache() if enable_cache else None
        self.usage = TokenUsage()

        # Initialize provider-specific client
        self._init_provider(api_key, base_url)

    def _init_provider(self, api_key: str | None, base_url: str | None) -> None:
        """Initialize the specific provider client."""
        if self.provider == LLMProvider.OPENAI:
            if not HAS_OPENAI:
                raise ImportError("OpenAI package not installed. Run: pip install openai")

            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")

            # Standard OpenAI client - works with OpenAI-compatible APIs
            # including Volces/Ark, OpenRouter, etc.
            self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

        elif self.provider == LLMProvider.ANTHROPIC:
            # Anthropic client initialization
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env var.")

            try:
                import anthropic

                self.client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")

        elif self.provider == LLMProvider.LOCAL:
            # Local LLM via OpenAI-compatible API
            base_url = base_url or "http://localhost:8000/v1"
            if HAS_OPENAI:
                self.client = openai.OpenAI(api_key="dummy", base_url=base_url)
            else:
                self.client = None

        elif self.provider == LLMProvider.MOCK:
            # Mock client for testing
            self.client = None

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        use_cache: bool = True,
        **kwargs,
    ) -> LLMResponse:
        """Generate text from LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            use_cache: Whether to use cache
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated content and metadata
        """
        # Check cache
        if use_cache and self.cache and self.enable_cache:
            cached = self.cache.get(prompt, self.model, temperature=temperature, **kwargs)
            if cached:
                self.usage.add_usage(cached, self.model)
                return cached

        # Generate with retry
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                if self.provider == LLMProvider.OPENAI:
                    response = self._generate_openai(prompt, system_prompt, temp, max_tok, **kwargs)
                elif self.provider == LLMProvider.ANTHROPIC:
                    response = self._generate_anthropic(
                        prompt, system_prompt, temp, max_tok, **kwargs
                    )
                elif self.provider == LLMProvider.LOCAL:
                    response = self._generate_local(prompt, system_prompt, temp, max_tok, **kwargs)
                else:
                    response = self._generate_mock(prompt, system_prompt, temp, max_tok, **kwargs)

                response.latency_ms = (time.time() - start_time) * 1000

                # Cache response
                if use_cache and self.cache and self.enable_cache:
                    self.cache.set(prompt, self.model, response, temperature=temp, **kwargs)

                # Track usage
                self.usage.add_usage(response, self.model)

                return response

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2**attempt)  # Exponential backoff

        raise RuntimeError("Max retries exceeded")

    def _generate_openai(
        self, prompt: str, system_prompt: str | None, temperature: float, max_tokens: int, **kwargs
    ) -> LLMResponse:
        """Generate using OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Handle empty or invalid response
        if not response or not response.choices or len(response.choices) == 0:
            raise RuntimeError(f"Empty response from API: {response}")

        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("Response content is None")

        return LLMResponse(
            content=content,
            provider=LLMProvider.OPENAI,
            model=self.model,
            tokens_used=getattr(response.usage, "total_tokens", 0) if response.usage else 0,
            prompt_tokens=getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
            completion_tokens=getattr(response.usage, "completion_tokens", 0)
            if response.usage
            else 0,
        )

    def _generate_anthropic(
        self, prompt: str, system_prompt: str | None, temperature: float, max_tokens: int, **kwargs
    ) -> LLMResponse:
        """Generate using Anthropic API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        return LLMResponse(
            content=response.content[0].text,
            provider=LLMProvider.ANTHROPIC,
            model=self.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

    def _generate_local(
        self, prompt: str, system_prompt: str | None, temperature: float, max_tokens: int, **kwargs
    ) -> LLMResponse:
        """Generate using local LLM."""
        if not HAS_OPENAI or not self.client:
            return self._generate_mock(prompt, system_prompt, temperature, max_tokens, **kwargs)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            provider=LLMProvider.LOCAL,
            model=self.model,
            tokens_used=getattr(response.usage, "total_tokens", 0),
            prompt_tokens=getattr(response.usage, "prompt_tokens", 0),
            completion_tokens=getattr(response.usage, "completion_tokens", 0),
        )

    def _generate_mock(
        self, prompt: str, system_prompt: str | None, temperature: float, max_tokens: int, **kwargs
    ) -> LLMResponse:
        """Generate mock response for testing."""
        # Simulate latency
        time.sleep(0.1)

        # Generate a simple mock response based on prompt content
        mock_responses = [
            "This is a mock response for testing purposes.",
            "The simulation suggests this is a reasonable outcome.",
            "Based on the available data, this appears to be the case.",
            "Analysis indicates this is the most likely scenario.",
        ]

        content = random.choice(mock_responses)

        return LLMResponse(
            content=content,
            provider=LLMProvider.MOCK,
            model=self.model,
            tokens_used=len(prompt.split()) + len(content.split()),
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(content.split()),
        )

    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        stats = self.usage.to_dict()
        stats["cache_size"] = self.cache.size if self.cache else 0
        return stats

    def reset_usage(self) -> None:
        """Reset usage statistics."""
        self.usage = TokenUsage()


class PromptTemplate:
    """Template for LLM prompts with variable substitution."""

    def __init__(self, template: str, variables: list[str] | None = None):
        self.template = template
        self.variables = variables or self._extract_variables(template)

    def _extract_variables(self, template: str) -> list[str]:
        """Extract variable names from template."""
        import re

        return re.findall(r"\{(\w+)\}", template)

    def format(self, **kwargs) -> str:
        """Format template with variables."""
        return self.template.format(**kwargs)

    def validate(self, **kwargs) -> bool:
        """Check if all required variables are provided."""
        return all(var in kwargs for var in self.variables)


# Pre-built prompts for FM Manager
class FMPrompts:
    """Collection of prompts for Football Manager use cases."""

    MATCH_NARRATIVE = PromptTemplate("""
You are a football match commentator. Describe this match moment in an exciting, broadcast-style narrative.

Match: {home_team} vs {away_team}
Minute: {minute}'
Event: {event_type}
Details: {details}

Provide a vivid 2-3 sentence description suitable for a match report.
""")

    PLAYER_PROFILE = PromptTemplate("""
Create a brief personality profile for this footballer:

Name: {player_name}
Position: {position}
Age: {age}
Key Attributes: {attributes}

Describe their playing style, personality, and reputation in 3-4 sentences.
""")

    TRANSFER_RUMOR = PromptTemplate("""
Generate a realistic transfer rumor news snippet:

Player: {player_name}
Current Club: {current_club}
Linked Club: {linked_club}
Rumor Strength: {strength} (weak/moderate/strong)

Write a short 2-3 sentence news item in the style of a football transfer journalist.
""")

    SEASON_REVIEW = PromptTemplate("""
Write a brief season review for {club_name}:

Final Position: {position}
Key Achievements: {achievements}
Notable Players: {notable_players}

Provide a 4-5 sentence summary capturing the essence of their season.
""")


def create_client_from_env() -> LLMClient:
    """Create LLM client from environment variables."""
    provider_str = os.getenv("LLM_PROVIDER", "mock").lower()

    provider_map = {
        "openai": LLMProvider.OPENAI,
        "anthropic": LLMProvider.ANTHROPIC,
        "claude": LLMProvider.ANTHROPIC,
        "local": LLMProvider.LOCAL,
        "mock": LLMProvider.MOCK,
    }

    provider = provider_map.get(provider_str, LLMProvider.MOCK)
    model = os.getenv("LLM_MODEL")

    return LLMClient(
        provider=provider,
        model=model,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
    )


def create_client_from_yaml(config_path: str | None = None) -> LLMClient:
    """Create LLM client from YAML configuration file.

    Args:
        config_path: Path to YAML config file. If None, uses default locations.

    Returns:
        Configured LLMClient instance

    Example:
        # Load from default config/llm_config.yaml
        client = create_client_from_yaml()

        # Load from specific file
        client = create_client_from_yaml("./my_config.yaml")
    """
    try:
        from fm_manager.config import load_llm_config

        config = load_llm_config(config_path)

        provider_map = {
            "openai": LLMProvider.OPENAI,
            "anthropic": LLMProvider.ANTHROPIC,
            "local": LLMProvider.LOCAL,
            "mock": LLMProvider.MOCK,
        }

        kwargs = config.to_client_kwargs()
        kwargs["provider"] = provider_map.get(config.provider, LLMProvider.MOCK)

        return LLMClient(**kwargs)
    except ImportError:
        # Fallback to env-based if config module not available
        return create_client_from_env()
