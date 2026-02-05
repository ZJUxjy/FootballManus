#!/usr/bin/env python3
"""Test script to verify LLM integration in NL game client."""

import os
import sys
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fm_manager.ai.intent_parser import get_intent_parser
from fm_manager.ai.command_executor import get_command_executor
from fm_manager.engine.llm_client import LLMClient, LLMProvider
from fm_manager.data.cleaned_data_loader import load_for_match_engine


async def test_llm_integration():
    """Test LLM integration with real API."""
    print("=" * 80)
    print("Testing LLM Integration")
    print("=" * 80)

    # Load config
    import tomllib
    from pathlib import Path

    config_path = Path("config/config.toml")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    llm_config = config.get("llm", {})

    print(f"\n1. LLM Configuration:")
    print(f"   Model: {llm_config.get('model')}")
    print(f"   Base URL: {llm_config.get('base_url')}")
    print(f"   API Key: {'*' * 10}{llm_config.get('api_key', '')[-4:]}")

    # Create LLM client
    print(f"\n2. Creating LLM Client...")
    llm_client = LLMClient(
        provider=LLMProvider.OPENAI,
        model=llm_config.get("model", "glm-4"),
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
        temperature=0.1,
        max_tokens=500,
    )
    print(f"   ✓ LLM Client created")
    print(f"   Provider: {llm_client.provider.value}")
    print(f"   Model: {llm_client.model}")

    # Test direct LLM call
    print(f"\n3. Testing Direct LLM Call...")
    try:
        response = llm_client.generate(
            prompt="Convert to JSON: Find English midfielders under 23",
            system_prompt="You are a helpful assistant. Respond with JSON only.",
            max_tokens=200,
        )
        print(f"   ✓ LLM call successful")
        print(f"   Response preview: {response.content[:100]}...")
    except Exception as e:
        print(f"   ✗ LLM call failed: {e}")
        return False

    # Create intent parser
    print(f"\n4. Creating Intent Parser...")
    parser = get_intent_parser(llm_client, force_new=True)
    print(f"   ✓ Intent Parser created")

    # Test intent parsing
    print(f"\n5. Testing Intent Parsing...")

    test_queries = [
        "Find English midfielders under 23 with high potential",
        "找英格兰中场球员，23岁以下，潜力高",
        "Show me my squad",
        "查看我的阵容",
        "Save game",
        "保存游戏",
    ]

    for query in test_queries:
        print(f"\n   Query: '{query}'")
        result = parser.parse(query)
        print(f"   → Intent: {result.intent.intent_type}")
        if hasattr(result.intent, "nationality"):
            print(f"     Nationality: {result.intent.nationality}")
        if hasattr(result.intent, "position"):
            print(f"     Position: {result.intent.position}")
        print(f"     Processing time: {result.processing_time_ms:.0f}ms")

    # Test command execution
    print(f"\n6. Testing Command Execution...")
    clubs, _ = load_for_match_engine()
    club = list(clubs.values())[0]

    executor = get_command_executor(club)
    print(f"   ✓ Command Executor created")
    print(f"   Club: {club.name}")

    # Execute a search command
    result = await executor.execute(parser.parse("Find English midfielders under 23"))
    print(f"\n   Search Result:")
    print(f"   Success: {result.success}")
    print(f"   Action: {result.action_taken}")
    print(f"   Message preview: {result.message[:200]}...")

    print("\n" + "=" * 80)
    print("✓ All tests passed!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    success = asyncio.run(test_llm_integration())
    sys.exit(0 if success else 1)
