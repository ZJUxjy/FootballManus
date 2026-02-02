"""Configuration management for FM Manager.

Supports loading configuration from YAML files.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    provider: str = "mock"
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 1000
    max_retries: int = 3
    timeout: int = 30
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 1000
    
    # Provider-specific
    api_key: str = ""
    base_url: str = ""
    organization: str = ""
    
    # Feature flags
    narrative_enabled: bool = True
    ai_manager_enabled: bool = True
    news_enabled: bool = True
    
    # AI Manager settings
    ai_manager_temperature: float = 0.3
    ai_manager_max_tokens: int = 300
    llm_adoption_rate: float = 0.2
    
    # Debug
    verbose_logging: bool = False
    save_prompts: bool = False
    prompts_dir: str = "./logs/llm_prompts"
    simulate_latency_ms: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> "LLMConfig":
        """Create config from dictionary."""
        config = cls()
        
        # Load main LLM settings
        llm_section = data.get("llm", {})
        config.provider = llm_section.get("provider", "mock")
        config.model = llm_section.get("model", "default")
        config.temperature = llm_section.get("temperature", 0.7)
        config.max_tokens = llm_section.get("max_tokens", 1000)
        config.max_retries = llm_section.get("max_retries", 3)
        config.timeout = llm_section.get("timeout", 30)
        config.enable_cache = llm_section.get("enable_cache", True)
        config.cache_ttl_seconds = llm_section.get("cache_ttl_seconds", 3600)
        config.cache_max_size = llm_section.get("cache_max_size", 1000)
        
        # Load provider-specific settings
        providers = data.get("providers", {})
        provider_config = providers.get(config.provider, {})
        config.api_key = provider_config.get("api_key", "")
        config.base_url = provider_config.get("base_url", "")
        config.organization = provider_config.get("organization", "")
        
        # Load feature settings
        features = data.get("features", {})
        
        narrative = features.get("narrative", {})
        config.narrative_enabled = narrative.get("enabled", True)
        
        ai_manager = features.get("ai_manager", {})
        config.ai_manager_enabled = ai_manager.get("enabled", True)
        config.ai_manager_temperature = ai_manager.get("temperature", 0.3)
        config.ai_manager_max_tokens = ai_manager.get("max_tokens", 300)
        config.llm_adoption_rate = ai_manager.get("llm_adoption_rate", 0.2)
        
        news = features.get("news", {})
        config.news_enabled = news.get("enabled", True)
        
        # Load debug settings
        debug = data.get("debug", {})
        config.verbose_logging = debug.get("verbose_logging", False)
        config.save_prompts = debug.get("save_prompts", False)
        config.prompts_dir = debug.get("prompts_dir", "./logs/llm_prompts")
        config.simulate_latency_ms = debug.get("simulate_latency_ms", 0)
        
        return config
    
    def get_api_key(self) -> str:
        """Get API key from config or environment variable."""
        if self.api_key:
            return self.api_key
        
        # Try environment variables
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "local": "LOCAL_LLM_API_KEY",
        }
        
        env_var = env_vars.get(self.provider)
        if env_var:
            return os.getenv(env_var, "")
        
        return ""
    
    def to_client_kwargs(self) -> dict:
        """Convert to kwargs for LLMClient constructor."""
        return {
            "provider": self.provider,
            "model": None if self.model == "default" else self.model,
            "api_key": self.get_api_key() or None,
            "base_url": self.base_url or None,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_retries": self.max_retries,
            "enable_cache": self.enable_cache,
        }


class ConfigManager:
    """Manages application configuration."""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "llm_config.yaml"
    LOCAL_CONFIG_PATH = Path(__file__).parent.parent / "config" / "llm_config.local.yaml"
    
    def __init__(self):
        self._llm_config: LLMConfig | None = None
    
    def load_yaml(self, path: Path | str) -> dict:
        """Load YAML configuration file."""
        if not HAS_YAML:
            raise ImportError(
                "PyYAML is required for YAML configuration. "
                "Install with: pip install pyyaml"
            )
        
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    def load_llm_config(self, path: Path | str | None = None) -> LLMConfig:
        """Load LLM configuration.
        
        Priority:
        1. Specified path
        2. config/llm_config.local.yaml (if exists)
        3. config/llm_config.yaml
        """
        if path is not None:
            data = self.load_yaml(path)
            self._llm_config = LLMConfig.from_dict(data)
            return self._llm_config
        
        # Try local config first
        if self.LOCAL_CONFIG_PATH.exists():
            data = self.load_yaml(self.LOCAL_CONFIG_PATH)
            self._llm_config = LLMConfig.from_dict(data)
            return self._llm_config
        
        # Fall back to default config
        if self.DEFAULT_CONFIG_PATH.exists():
            data = self.load_yaml(self.DEFAULT_CONFIG_PATH)
            self._llm_config = LLMConfig.from_dict(data)
            return self._llm_config
        
        # Return default config if no file found
        self._llm_config = LLMConfig()
        return self._llm_config
    
    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration (load if not already loaded)."""
        if self._llm_config is None:
            return self.load_llm_config()
        return self._llm_config
    
    def reload(self) -> None:
        """Reload configuration from files."""
        self._llm_config = None
        self.load_llm_config()
    
    def create_local_config_template(self) -> Path:
        """Create a local config template from default config."""
        if not self.DEFAULT_CONFIG_PATH.exists():
            raise FileNotFoundError("Default config not found")
        
        if self.LOCAL_CONFIG_PATH.exists():
            return self.LOCAL_CONFIG_PATH
        
        data = self.load_yaml(self.DEFAULT_CONFIG_PATH)
        
        # Modify for local use
        data["llm"]["provider"] = "openai"  # Suggest OpenAI for local config
        data["llm"]["model"] = "gpt-3.5-turbo"  # Cheaper default
        
        with open(self.LOCAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        return self.LOCAL_CONFIG_PATH


# Global config manager instance
_config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """Get the global config manager instance."""
    return _config_manager


def load_llm_config(path: Path | str | None = None) -> LLMConfig:
    """Convenience function to load LLM configuration."""
    return _config_manager.load_llm_config(path)


def create_llm_client_from_config(path: Path | str | None = None):
    """Create an LLMClient from configuration file."""
    from fm_manager.engine.llm_client import LLMClient, LLMProvider
    
    config = load_llm_config(path)
    
    # Map string provider to enum
    provider_map = {
        "openai": LLMProvider.OPENAI,
        "anthropic": LLMProvider.ANTHROPIC,
        "local": LLMProvider.LOCAL,
        "mock": LLMProvider.MOCK,
    }
    
    kwargs = config.to_client_kwargs()
    kwargs["provider"] = provider_map.get(config.provider, LLMProvider.MOCK)
    
    return LLMClient(**kwargs)


# Example usage
if __name__ == "__main__":
    # Load configuration
    config = load_llm_config()
    
    print("LLM Configuration:")
    print(f"  Provider: {config.provider}")
    print(f"  Model: {config.model}")
    print(f"  Temperature: {config.temperature}")
    print(f"  Max Tokens: {config.max_tokens}")
    print(f"  API Key set: {bool(config.get_api_key())}")
    
    print("\nFeature Settings:")
    print(f"  Narrative: {config.narrative_enabled}")
    print(f"  AI Manager: {config.ai_manager_enabled}")
    print(f"  News: {config.news_enabled}")
    print(f"  LLM Adoption Rate: {config.llm_adoption_rate}")
