#!/usr/bin/env python3
"""
Test script for LLM-powered AI Manager using YAML configuration.

Demonstrates:
- Loading LLM config from YAML
- Creating AI Manager with YAML-configured LLM
- Feature-specific LLM settings
"""

import sys
from datetime import date, datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

from fm_manager.config import load_llm_config, create_llm_client_from_config
from fm_manager.core.models import Club, Player, Position
from fm_manager.engine.llm_client import LLMClient, LLMProvider
from fm_manager.engine.ai_manager import (
    AIManager, AIManagerController, AIPersonality
)

console = Console()


def test_yaml_configured_manager():
    """Test AI Manager with YAML configuration."""
    console.print(Panel("[bold blue]🎮 Testing YAML-Configured AI Manager[/]", border_style="blue"))
    
    # Load config
    config = load_llm_config()
    
    console.print(f"\n[bold]Loaded Configuration:[/]")
    console.print(f"  Provider: [cyan]{config.provider}[/]")
    console.print(f"  AI Manager Enabled: [green]{config.ai_manager_enabled}[/]")
    console.print(f"  LLM Adoption Rate: [yellow]{config.llm_adoption_rate}[/]")
    
    # Create LLM client from config
    llm = create_llm_client_from_config()
    
    console.print(f"\n[bold]Created LLMClient:[/]")
    console.print(f"  Provider: [cyan]{llm.provider.value}[/]")
    console.print(f"  Temperature: [cyan]{llm.temperature}[/]")
    
    # Create club
    club = Club(
        id=1,
        name="Manchester United",
        reputation=8800,
        balance=200_000_000,
    )
    
    # Create LLM-powered manager
    manager = AIManager(
        club=club,
        personality=AIPersonality.LLM_POWERED,
        llm_client=llm,
    )
    
    console.print(f"\n[bold]Manager Created:[/]")
    console.print(f"  Club: {manager.club.name}")
    console.print(f"  Personality: [magenta]{manager.personality.value}[/]")
    console.print(f"  Has LLM Decision Maker: [green]{manager.llm_decision_maker is not None}[/]")
    
    # Test squad assessment
    players = [
        Player(first_name="Bruno", last_name="Fernandes", position=Position.CAM, current_ability=88, nationality="Portugal"),
        Player(first_name="Marcus", last_name="Rashford", position=Position.LW, current_ability=85, nationality="England"),
        Player(first_name="Casemiro", last_name="", position=Position.CDM, current_ability=87, nationality="Brazil"),
    ]
    
    assessment = manager.assess_squad(players)
    console.print(f"\n[bold]Squad Assessment:[/]")
    console.print(f"  Midfield: {assessment.midfield_strength}")
    console.print(f"  Attack: {assessment.attack_strength}")


def test_controller_with_yaml_config():
    """Test AIManagerController with YAML config."""
    console.print(Panel("[bold green]🎯 Testing Controller with YAML Config[/]", border_style="green"))
    
    # Load config and create client
    config = load_llm_config()
    llm = create_llm_client_from_config()
    
    # Create controller with LLM from config
    controller = AIManagerController(llm_client=llm)
    
    clubs = [
        Club(id=1, name="Liverpool", reputation=9000, balance=250_000_000),
        Club(id=2, name="Arsenal", reputation=8500, balance=200_000_000),
        Club(id=3, name="Chelsea", reputation=8200, balance=300_000_000),
    ]
    
    console.print(f"\n[bold]Creating Managers (Adoption Rate: {config.llm_adoption_rate}):[/]")
    
    # Create managers - some will use LLM based on adoption rate
    import random
    random.seed(42)  # For reproducible demo
    
    for club in clubs:
        # Simulate adoption rate
        use_llm = random.random() < config.llm_adoption_rate
        
        if use_llm:
            manager = controller.create_manager(club, use_llm=True)
            status = f"[green]LLM ({manager.personality.value})[/]"
        else:
            manager = controller.create_manager(club, use_llm=False)
            status = f"[yellow]Rule-based ({manager.personality.value})[/]"
        
        console.print(f"  {club.name}: {status}")


def test_feature_specific_settings():
    """Test feature-specific LLM settings."""
    console.print(Panel("[bold yellow]⚙️ Testing Feature-Specific Settings[/]", border_style="yellow"))
    
    config = load_llm_config()
    
    console.print(f"\n[bold]Feature Settings from YAML:[/]")
    
    console.print(f"\n  [cyan]Narrative Engine:[/]")
    console.print(f"    Enabled: {config.narrative_enabled}")
    console.print(f"    Temperature: {config.temperature}")
    console.print(f"    Max Tokens: {config.max_tokens}")
    
    console.print(f"\n  [cyan]AI Manager:[/]")
    console.print(f"    Enabled: {config.ai_manager_enabled}")
    console.print(f"    Temperature: {config.ai_manager_temperature}")
    console.print(f"    Max Tokens: {config.ai_manager_max_tokens}")
    
    console.print(f"\n  [cyan]News System:[/]")
    console.print(f"    Enabled: {config.news_enabled}")
    
    # Demonstrate creating clients with different settings for different features
    console.print(f"\n[bold]Creating Feature-Specific Clients:[/]")
    
    # Default client
    default_client = create_llm_client_from_config()
    console.print(f"  Default: temp={default_client.temperature}, max_tokens={default_client.max_tokens}")
    
    # AI Manager client (lower temperature for more consistent decisions)
    if config.ai_manager_enabled:
        ai_client = LLMClient(
            provider=default_client.provider,
            model=default_client.model,
            temperature=config.ai_manager_temperature,
            max_tokens=config.ai_manager_max_tokens,
            enable_cache=config.enable_cache,
        )
        console.print(f"  AI Manager: temp={ai_client.temperature}, max_tokens={ai_client.max_tokens}")


def show_yaml_structure():
    """Show the YAML configuration structure."""
    console.print(Panel("[bold cyan]📄 YAML Configuration Structure[/]", border_style="cyan"))
    
    yaml_content = """
# config/llm_config.yaml

llm:
  provider: openai          # openai, anthropic, local, mock
  model: gpt-3.5-turbo      # model name
  temperature: 0.7
  max_tokens: 1000
  enable_cache: true

providers:
  openai:
    api_key: ""              # Or use OPENAI_API_KEY env var
    base_url: ""             # Optional: for Azure OpenAI
  
  anthropic:
    api_key: ""              # Or use ANTHROPIC_API_KEY env var
  
  local:
    base_url: http://localhost:8000/v1

features:
  narrative:
    enabled: true
    temperature: 0.8
  
  ai_manager:
    enabled: true
    temperature: 0.3        # Lower for consistent decisions
    llm_adoption_rate: 0.2  # 20% of AI managers use LLM
  
  news:
    enabled: true
"""
    
    console.print(f"[dim]{yaml_content}[/]")


def main():
    """Run all YAML configuration tests."""
    console.print("\n" + "=" * 70)
    console.print("[bold]LLM MANAGER WITH YAML CONFIG TEST SUITE[/]")
    console.print("=" * 70 + "\n")
    
    test_yaml_configured_manager()
    console.print("\n")
    
    test_controller_with_yaml_config()
    console.print("\n")
    
    test_feature_specific_settings()
    console.print("\n")
    
    show_yaml_structure()
    
    console.print("\n" + "=" * 70)
    console.print("[bold green]YAML Config tests completed![/]")
    console.print("=" * 70)
    
    console.print("\n[bold cyan]Configuration Tips:[/]")
    console.print("  • Edit config/llm_config.local.yaml for your settings")
    console.print("  • API keys can be in YAML or environment variables")
    console.print("  • Lower temperature (0.3) for AI Manager = more consistent decisions")
    console.print("  • Adjust llm_adoption_rate to control how many AI managers use LLM")
    console.print("  • Use 'mock' provider for testing without API calls")


if __name__ == "__main__":
    main()
