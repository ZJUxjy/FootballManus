"""TOML Configuration for FM Manager - Compatible with OpenManus style."""

import os
import tomllib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class LLMSettings:
    """LLM configuration settings."""
    model: str = "gpt-3.5-turbo"
    base_url: str = ""
    api_key: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    api_type: str = ""  # openai, azure, aws, ollama
    api_version: str = ""


@dataclass
class FeatureSettings:
    """Feature-specific settings."""
    ai_manager_enabled: bool = True
    ai_manager_temperature: float = 0.3
    ai_manager_max_tokens: int = 300
    llm_adoption_rate: float = 0.2
    
    narrative_enabled: bool = True
    narrative_temperature: float = 0.8
    narrative_max_tokens: int = 500
    
    news_enabled: bool = True
    news_temperature: float = 0.7
    news_max_tokens: int = 400


class Config:
    """Configuration manager - OpenManus compatible."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = False
            self._llm: Optional[LLMSettings] = None
            self._features: Optional[FeatureSettings] = None
            self._load_config()
    
    def _get_config_path(self) -> Path:
        """Get configuration file path."""
        root = Path(__file__).resolve().parent.parent
        
        # Try config.toml first
        config_path = root / "config" / "config.toml"
        if config_path.exists():
            return config_path
        
        # Fall back to llm_config.local.yaml
        local_yaml = root / "config" / "llm_config.local.yaml"
        if local_yaml.exists():
            return local_yaml
        
        # Fall back to llm_config.yaml
        default_yaml = root / "config" / "llm_config.yaml"
        if default_yaml.exists():
            return default_yaml
        
        raise FileNotFoundError("No configuration file found")
    
    def _load_config(self):
        """Load configuration from file."""
        config_path = self._get_config_path()
        
        if config_path.suffix == '.toml':
            self._load_toml_config(config_path)
        else:
            self._load_yaml_config(config_path)
    
    def _load_toml_config(self, path: Path):
        """Load TOML configuration (OpenManus style)."""
        with open(path, 'rb') as f:
            raw_config = tomllib.load(f)
        
        # Load LLM settings
        llm_section = raw_config.get("llm", {})
        self._llm = LLMSettings(
            model=llm_section.get("model", "gpt-3.5-turbo"),
            base_url=llm_section.get("base_url", ""),
            api_key=llm_section.get("api_key", ""),
            max_tokens=llm_section.get("max_tokens", 4096),
            temperature=llm_section.get("temperature", 0.7),
            api_type=llm_section.get("api_type", ""),
            api_version=llm_section.get("api_version", ""),
        )
        
        # Load feature settings
        features_section = raw_config.get("features", {})
        self._features = FeatureSettings(
            ai_manager_enabled=features_section.get("ai_manager_enabled", True),
            ai_manager_temperature=features_section.get("ai_manager_temperature", 0.3),
            ai_manager_max_tokens=features_section.get("ai_manager_max_tokens", 300),
            llm_adoption_rate=features_section.get("llm_adoption_rate", 0.2),
            narrative_enabled=features_section.get("narrative_enabled", True),
            narrative_temperature=features_section.get("narrative_temperature", 0.8),
            narrative_max_tokens=features_section.get("narrative_max_tokens", 500),
            news_enabled=features_section.get("news_enabled", True),
            news_temperature=features_section.get("news_temperature", 0.7),
            news_max_tokens=features_section.get("news_max_tokens", 400),
        )
    
    def _load_yaml_config(self, path: Path):
        """Load YAML configuration (legacy style)."""
        import yaml
        
        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
        
        llm_section = raw_config.get("llm", {})
        providers = raw_config.get("providers", {})
        
        provider = llm_section.get("provider", "openai")
        provider_config = providers.get(provider, {})
        
        self._llm = LLMSettings(
            model=llm_section.get("model", "gpt-3.5-turbo"),
            base_url=provider_config.get("base_url", ""),
            api_key=provider_config.get("api_key", ""),
            max_tokens=llm_section.get("max_tokens", 4096),
            temperature=llm_section.get("temperature", 0.7),
            api_type=provider if provider != "openai" else "",
        )
        
        features = raw_config.get("features", {})
        ai_manager = features.get("ai_manager", {})
        narrative = features.get("narrative", {})
        news = features.get("news", {})
        
        self._features = FeatureSettings(
            ai_manager_enabled=ai_manager.get("enabled", True),
            ai_manager_temperature=ai_manager.get("temperature", 0.3),
            ai_manager_max_tokens=ai_manager.get("max_tokens", 300),
            llm_adoption_rate=ai_manager.get("llm_adoption_rate", 0.2),
            narrative_enabled=narrative.get("enabled", True),
            narrative_temperature=narrative.get("temperature", 0.8),
            narrative_max_tokens=narrative.get("max_tokens", 500),
            news_enabled=news.get("enabled", True),
            news_temperature=news.get("temperature", 0.7),
            news_max_tokens=news.get("max_tokens", 400),
        )
    
    @property
    def llm(self) -> LLMSettings:
        """Get LLM settings."""
        if self._llm is None:
            self._load_config()
        return self._llm
    
    @property
    def features(self) -> FeatureSettings:
        """Get feature settings."""
        if self._features is None:
            self._load_config()
        return self._features
    
    def reload(self):
        """Reload configuration."""
        self._llm = None
        self._features = None
        self._load_config()


# Global config instance
_config = Config()


def get_config() -> Config:
    """Get global config instance."""
    return _config


def load_llm_config():
    """Load LLM configuration - compatible with old API."""
    return _config.llm


def create_llm_client_from_config():
    """Create LLM client from config - OpenManus compatible."""
    from fm_manager.engine.llm_client import LLMClient, LLMProvider
    
    llm_config = _config.llm
    
    # Determine provider
    if llm_config.api_type == "azure":
        provider = LLMProvider.OPENAI  # Azure uses OpenAI client
    elif llm_config.api_type == "ollama":
        provider = LLMProvider.LOCAL
    else:
        provider = LLMProvider.OPENAI
    
    return LLMClient(
        provider=provider,
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url if llm_config.base_url else None,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        enable_cache=True,
    )
