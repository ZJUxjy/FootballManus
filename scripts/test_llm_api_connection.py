#!/usr/bin/env python3
"""Test LLM API Connection.

This script tests if the LLM API configured in config.toml can connect successfully.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_config():
    """Load LLM config from config.toml."""
    import tomllib

    config_path = project_root / "config" / "config.toml"

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config.get("llm", {})


def test_openai_connection(config: dict):
    """Test connection using OpenAI-compatible API."""
    try:
        from fm_manager.engine.llm_client import LLMClient, LLMProvider

        print("=" * 60)
        print("Testing LLM API Connection")
        print("=" * 60)

        # Fix base_url: remove /chat/completions if present
        # OpenAI client automatically appends /chat/completions
        base_url = config.get('base_url', '')
        original_url = base_url
        if base_url and '/chat/completions' in base_url:
            base_url = base_url.replace('/chat/completions', '').rstrip('/')

        # Display config (hide API key)
        print(f"\nConfiguration:")
        print(f"  Model: {config.get('model', 'N/A')}")
        print(f"  Base URL: {base_url or '(default)'}")
        if base_url != original_url and original_url:
            print(f"  [Auto-fixed from: {original_url}]")
        api_key = config.get('api_key', '')
        print(f"  API Key: {'*' * 20}{api_key[-4:] if api_key and len(api_key) > 4 else 'N/A'}")
        print(f"  Max Tokens: {config.get('max_tokens', 'N/A')}")
        print(f"  Temperature: {config.get('temperature', 'N/A')}")

        # Create client
        print(f"\nInitializing LLM client...")
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=base_url if base_url else None,
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 1000),
            enable_cache=False,
        )

        # Test prompts
        test_prompts = [
            {
                "name": "Simple Greeting",
                "prompt": "Say 'Hello, this is a test!' in one sentence.",
                "system": "You are a helpful assistant."
            },
            {
                "name": "Math Question",
                "prompt": "What is 25 + 17?",
                "system": "You are a helpful assistant. Give brief answers."
            },
            {
                "name": "Football Question",
                "prompt": "What is offside in football?",
                "system": "You are a football expert. Explain briefly in 2-3 sentences."
            }
        ]

        print(f"\nRunning {len(test_prompts)} test queries...\n")

        for i, test in enumerate(test_prompts, 1):
            print(f"Test {i}: {test['name']}")
            print(f"Prompt: {test['prompt']}")
            print("-" * 40)

            try:
                start_time = time.time()
                response = client.generate(
                    prompt=test["prompt"],
                    system_prompt=test["system"],
                    use_cache=False
                )
                elapsed = time.time() - start_time

                print(f"Status: SUCCESS")
                print(f"Response: {response.content[:200]}{'...' if len(response.content) > 200 else ''}")
                print(f"Tokens: {response.tokens_used} (prompt: {response.prompt_tokens}, completion: {response.completion_tokens})")
                print(f"Latency: {response.latency_ms:.0f}ms ({elapsed:.2f}s)")

            except Exception as e:
                print(f"Status: FAILED")
                print(f"Error: {type(e).__name__}: {e}")

            print()

        # Show usage stats
        stats = client.get_usage_stats()
        print("=" * 60)
        print("Usage Statistics:")
        print(f"  Total Requests: {stats['requests_count']}")
        print(f"  Total Tokens: {stats['total_tokens']}")
        print(f"  Estimated Cost: ${stats['estimated_cost_usd']:.4f}")
        print("=" * 60)

        return True

    except ImportError as e:
        print(f"Error: {e}")
        print("\nMake sure openai package is installed: pip install openai")
        return False
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    config = load_config()

    if not config:
        print("Error: No LLM configuration found in config.toml")
        sys.exit(1)

    success = test_openai_connection(config)

    if success:
        print("\n✓ API connection test completed")
        sys.exit(0)
    else:
        print("\n✗ API connection test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
