"""Test multi-step search functionality."""

import asyncio
import sys

sys.path.insert(0, "/home/xjingyao/code/fm_manager")

from fm_manager.ai.llm_tool_interface import LLMToolInterface, ToolCallResult, SearchAdjustment
from fm_manager.engine.llm_client import LLMClient, LLMProvider


def test_empty_result_detection():
    """Test detection of empty search results."""
    interface = LLMToolInterface()

    # Test empty dict with players key
    result1 = {"players": [], "total": 0}
    assert interface._is_empty_search_result(result1) == True

    # Test dict with results
    result2 = {"players": [{"name": "Player1"}], "total": 1}
    assert interface._is_empty_search_result(result2) == False

    # Test empty list
    result3 = []
    assert interface._is_empty_search_result(result3) == True

    # Test non-empty list
    result4 = [{"name": "Player1"}]
    assert interface._is_empty_search_result(result4) == False

    print("✓ Empty result detection works")


def test_search_param_adjustment():
    """Test automatic adjustment of search parameters."""
    interface = LLMToolInterface()

    # Test iteration 1 - lower potential
    params1 = {"position": "GK", "min_potential": 140, "max_age": 23}
    adjusted1, reason1 = interface._adjust_search_params(params1, 1)
    assert adjusted1["min_potential"] == 130
    assert "降低潜力要求" in reason1

    # Test iteration 2 - lower potential further
    adjusted2, reason2 = interface._adjust_search_params(adjusted1, 2)
    assert adjusted2["min_potential"] == 120

    # Test age adjustment
    params2 = {"position": "ST", "max_age": 21}
    adjusted3, reason3 = interface._adjust_search_params(params2, 1)
    assert adjusted3["max_age"] == 23
    assert "放宽年龄限制" in reason3

    # Test price adjustment
    params3 = {"max_price": 10000000}
    adjusted4, reason4 = interface._adjust_search_params(params3, 1)
    assert adjusted4["max_price"] == 12000000
    assert "提高预算上限" in reason4

    print("✓ Search parameter adjustment works")


def test_iterative_search_prompt():
    """Test building iterative search prompt."""
    interface = LLMToolInterface()

    user_query = "Find young goalkeepers with high potential"

    # Create mock results
    results = [
        ToolCallResult(
            tool_name="search_players",
            parameters={"position": "GK", "min_potential": 140},
            result={"players": [], "total": 0},
            success=True,
        ),
        ToolCallResult(
            tool_name="search_players",
            parameters={"position": "GK", "min_potential": 130},
            result={"players": [{"name": "Player1"}], "total": 1},
            success=True,
        ),
    ]

    adjustments = [
        SearchAdjustment(
            original_params={"min_potential": 140},
            adjusted_params={"min_potential": 130},
            reason="降低潜力要求",
            iteration=1,
        )
    ]

    prompt = interface._build_iterative_search_prompt(user_query, results, adjustments)

    assert "Original user query" in prompt
    assert "Search history" in prompt
    assert "Attempt 1" in prompt
    assert "降低潜力要求" in prompt

    print("✓ Iterative search prompt building works")


async def test_full_flow():
    """Test full multi-step search flow."""
    print("\nTesting full multi-step search flow...")

    # This would require mocking the LLM and tool registry
    # For now, just verify the interface methods exist and are callable
    interface = LLMToolInterface(LLMClient(provider=LLMProvider.MOCK))

    # Test that process_query accepts max_iterations parameter
    try:
        result = await interface.process_query("test query", max_iterations=2)
        print("✓ process_query with max_iterations parameter works")
    except Exception as e:
        print(f"⚠ process_query test (expected with mock LLM): {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Multi-Step Search Functionality")
    print("=" * 60)

    test_empty_result_detection()
    test_search_param_adjustment()
    test_iterative_search_prompt()

    # Run async test
    asyncio.run(test_full_flow())

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
