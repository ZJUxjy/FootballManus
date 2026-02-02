#!/usr/bin/env python3
"""
Test script for YAML configuration system.

Demonstrates:
- Loading configuration from YAML files
- Creating LLMClient from YAML config
- Configuration priority (local > default)
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

from fm_manager.config import (
    load_llm_config,
    create_llm_client_from_config,
    ConfigManager,
)

console = Console()


def test_config_loading():
    """Test loading configuration from YAML."""
    console.print(Panel("[bold blue]📄 Testing YAML Config Loading[/]", border_style="blue"))
    
    # Test loading default config
    console.print("\n[bold]Loading Default Config:[/]")
    config = load_llm_config()
    
    console.print(f"  Provider: [cyan]{config.provider}[/]")
    console.print(f"  Model: [cyan]{config.model}[/]")
    console.print(f"  Temperature: [cyan]{config.temperature}[/]")
    console.print(f"  Max Tokens: [cyan]{config.max_tokens}[/]")
    console.print(f"  Enable Cache: [cyan]{config.enable_cache}[/]")
    
    # Test feature settings
    console.print(f"\n[bold]Feature Settings:[/]")
    console.print(f"  Narrative Enabled: [green]{config.narrative_enabled}[/]")
    console.print(f"  AI Manager Enabled: [green]{config.ai_manager_enabled}[/]")
    console.print(f"  News Enabled: [green]{config.news_enabled}[/]")
    console.print(f"  LLM Adoption Rate: [yellow]{config.llm_adoption_rate}[/]")
    
    # Test debug settings
    console.print(f"\n[bold]Debug Settings:[/]")
    console.print(f"  Verbose Logging: [red]{config.verbose_logging}[/]")
    console.print(f"  Save Prompts: [red]{config.save_prompts}[/]")


def test_config_to_client_kwargs():
    """Test converting config to client kwargs."""
    console.print(Panel("[bold green]⚙️ Testing Config to Client Kwargs[/]", border_style="green"))
    
    config = load_llm_config()
    kwargs = config.to_client_kwargs()
    
    console.print("\n[bold]Client Kwargs:[/]")
    for key, value in kwargs.items():
        if key == "api_key" and value:
            value = "***"  # Hide API key
        console.print(f"  {key}: [cyan]{value}[/]")


def test_create_client():
    """Test creating LLM client from YAML config."""
    console.print(Panel("[bold yellow]🤖 Testing Create LLMClient from YAML[/]", border_style="yellow"))
    
    try:
        from fm_manager.engine.llm_client import create_client_from_yaml
        
        client = create_client_from_yaml()
        
        console.print(f"\n[bold]Created LLMClient:[/]")
        console.print(f"  Provider: [cyan]{client.provider.value}[/]")
        console.print(f"  Model: [cyan]{client.model}[/]")
        console.print(f"  Temperature: [cyan]{client.temperature}[/]")
        console.print(f"  Cache Enabled: [cyan]{client.enable_cache}[/]")
        
        # Test generation
        console.print(f"\n[bold]Testing Generation:[/]")
        response = client.generate("Say hello", max_tokens=50)
        console.print(f"  Response: [green]{response.content[:50]}...[/]")
        console.print(f"  Tokens: [yellow]{response.tokens_used}[/]")
        
    except Exception as e:
        console.print(f"  [red]Error: {e}[/]")


def test_config_manager():
    """Test ConfigManager features."""
    console.print(Panel("[bold magenta]🛠️ Testing ConfigManager[/]", border_style="magenta"))
    
    manager = ConfigManager()
    
    # Show config paths
    console.print(f"\n[bold]Config Paths:[/]")
    console.print(f"  Default: [dim]{manager.DEFAULT_CONFIG_PATH}[/]")
    console.print(f"  Local: [dim]{manager.LOCAL_CONFIG_PATH}[/]")
    console.print(f"  Default exists: [green]{manager.DEFAULT_CONFIG_PATH.exists()}[/]")
    console.print(f"  Local exists: [red]{manager.LOCAL_CONFIG_PATH.exists()}[/]")
    
    # Test creating local config template
    if not manager.LOCAL_CONFIG_PATH.exists():
        console.print(f"\n[bold]Creating Local Config Template:[/]")
        try:
            path = manager.create_local_config_template()
            console.print(f"  Created: [green]{path}[/]")
            console.print(f"  [yellow]Edit this file to customize your LLM settings[/]")
            
            # Show content
            with open(path) as f:
                content = f.read()
                lines = content.split("\n")[:20]
                console.print(f"\n[dim]First 20 lines:[/]")
                for line in lines:
                    console.print(f"    {line}")
                    
        except Exception as e:
            console.print(f"  [red]Error: {e}[/]")
    else:
        console.print(f"\n[bold]Local Config:[/] [green]Already exists[/]")


def show_config_examples():
    """Show example configurations."""
    console.print(Panel("[bold cyan]📝 Example Configurations[/]", border_style="cyan"))
    
    examples = {
        "OpenAI GPT-4": """
llm:
  provider: openai
  model: gpt-4
  temperature: 0.7

providers:
  openai:
    api_key: "sk-..."  # Or set OPENAI_API_KEY env var
""",
        "Anthropic Claude": """
llm:
  provider: anthropic
  model: claude-3-sonnet
  temperature: 0.7

providers:
  anthropic:
    api_key: "..."  # Or set ANTHROPIC_API_KEY env var
""",
        "Local LLM": """
llm:
  provider: local
  model: llama-2-70b
  temperature: 0.7

providers:
  local:
    base_url: "http://localhost:8000/v1"
""",
    }
    
    for name, config in examples.items():
        console.print(f"\n[bold]{name}:[/]")
        console.print(f"[dim]{config}[/]")


def main():
    """Run all YAML config tests."""
    console.print("\n" + "=" * 70)
    console.print("[bold]YAML CONFIGURATION TEST SUITE[/]")
    console.print("=" * 70 + "\n")
    
    test_config_loading()
    console.print("\n")
    
    test_config_to_client_kwargs()
    console.print("\n")
    
    test_create_client()
    console.print("\n")
    
    test_config_manager()
    console.print("\n")
    
    show_config_examples()
    
    console.print("\n" + "=" * 70)
    console.print("[bold green]YAML Config tests completed![/]")
    console.print("=" * 70)
    
    console.print("\n[bold cyan]Quick Start:[/]")
    console.print("  1. Copy config/llm_config.yaml to config/llm_config.local.yaml")
    console.print("  2. Edit the file to set your API keys")
    console.print("  3. Run: python scripts/test_yaml_config.py")


if __name__ == "__main__":
    main()
