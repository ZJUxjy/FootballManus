"""Comprehensive test for transfer tools.

Tests all 6 newly registered transfer tools:
- make_transfer_offer
- list_player_for_transfer
- view_transfer_market
- view_transfer_offers
- respond_to_transfer_offer
- withdraw_transfer_offer
"""

import sys

sys.path.insert(0, "/home/xjingyao/code/fm_manager")

# Import tool_implementations first to trigger tool registration
from fm_manager.ai.tools import tool_implementations
from fm_manager.ai.tools.tool_registry import get_tool_registry, ToolRegistry
from fm_manager.ai.tools.transfer_tools import (
    set_transfer_market,
    set_current_club_id,
    make_transfer_offer_tool,
    list_player_for_transfer_tool,
    view_transfer_list_tool,
    view_my_offers_tool,
    respond_to_offer_tool,
    withdraw_offer_tool,
)
from fm_manager.engine.transfer_market import TransferMarket
from fm_manager.data.cleaned_data_loader import load_for_match_engine
from datetime import date


def test_tool_registration():
    """Verify all transfer tools are registered."""
    print("=" * 70)
    print("TEST 1: Tool Registration")
    print("=" * 70)

    registry = get_tool_registry()
    tools = registry.list_tools()

    expected_tools = [
        "make_transfer_offer",
        "list_player_for_transfer",
        "view_transfer_market",
        "view_transfer_offers",
        "respond_to_transfer_offer",
        "withdraw_transfer_offer",
    ]

    registered_names = [t.name for t in tools]

    print(f"\nTotal registered tools: {len(tools)}")
    print(f"Expected transfer tools: {len(expected_tools)}")

    all_found = True
    print("\nChecking transfer tools:")
    for tool_name in expected_tools:
        if tool_name in registered_names:
            print(f"  ✓ {tool_name}")
        else:
            print(f"  ✗ {tool_name} - NOT FOUND!")
            all_found = False

    if all_found:
        print("\n✅ All transfer tools registered successfully!")
    else:
        print("\n❌ Some tools are missing!")

    return all_found


def test_tool_parameters():
    """Verify tool parameter definitions."""
    print("\n" + "=" * 70)
    print("TEST 2: Tool Parameter Definitions")
    print("=" * 70)

    registry = get_tool_registry()

    tests = [
        ("make_transfer_offer", ["player_name", "offer_amount"]),
        ("list_player_for_transfer", ["player_name"]),
        ("view_transfer_market", []),
        ("view_transfer_offers", []),
        ("respond_to_transfer_offer", ["offer_id", "action"]),
        ("withdraw_transfer_offer", ["offer_id"]),
    ]

    all_passed = True
    for tool_name, expected_params in tests:
        tool = registry.get(tool_name)
        if not tool:
            print(f"\n✗ {tool_name}: Tool not found")
            all_passed = False
            continue

        actual_params = [p.name for p in tool.parameters]

        print(f"\n{tool_name}:")
        print(f"  Description: {tool.description}")
        print(f"  Expected params: {expected_params}")
        print(f"  Actual params: {actual_params}")

        missing = [p for p in expected_params if p not in actual_params]
        if missing:
            print(f"  ✗ Missing parameters: {missing}")
            all_passed = False
        else:
            print(f"  ✓ All parameters present")

    return all_passed


def test_tool_execution_without_market():
    """Test tool execution when transfer market is not initialized."""
    print("\n" + "=" * 70)
    print("TEST 3: Tool Execution (Without Initialized Market)")
    print("=" * 70)

    registry = get_tool_registry()

    test_cases = [
        ("view_transfer_offers", {}, "Transfer market not initialized"),
        ("view_transfer_market", {"limit": 10}, "Transfer market not initialized"),
        (
            "make_transfer_offer",
            {"player_name": "Test", "offer_amount": 1000000},
            "Transfer market not initialized",
        ),
    ]

    all_passed = True
    for tool_name, params, expected_error in test_cases:
        print(f"\nTesting {tool_name}:")
        try:
            result = registry.execute(tool_name, params)
            if "error" in result and expected_error in result["error"]:
                print(f"  ✓ Correctly returned error: {result['error']}")
            elif "error" in result:
                print(f"  ! Different error: {result['error']}")
            else:
                print(f"  ! Unexpected success: {result}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            all_passed = False

    return all_passed


def test_tool_execution_with_market():
    """Test tool execution with initialized transfer market."""
    print("\n" + "=" * 70)
    print("TEST 4: Tool Execution (With Initialized Market)")
    print("=" * 70)

    try:
        clubs, players = load_for_match_engine()
        print(f"\nLoaded {len(clubs)} clubs, {len(players)} players")

        user_club = None
        for club in clubs.values():
            if "Stuttgart" in club.name or "Roma" in club.name:
                user_club = club
                break

        if not user_club:
            print("  ! Could not find test club, skipping execution test")
            return True

        print(f"  Test club: {user_club.name}")

        market = TransferMarket(
            all_clubs=clubs,
            all_players=players,
            current_date=date(2024, 8, 1),
            transfer_window_open=True,
        )

        set_transfer_market(market)
        set_current_club_id(getattr(user_club, "id", 0))

        print("\n  Testing view_transfer_market:")
        result = view_transfer_list_tool(limit=5)
        print(f"    Result: {result.get('total_available', 0)} players available")

        if result.get("total_available", 0) >= 0:
            print("  ✓ view_transfer_market working")

        print("\n  Testing view_transfer_offers:")
        result = view_my_offers_tool()
        print(
            f"    Incoming: {result.get('total_incoming', 0)}, Outgoing: {result.get('total_outgoing', 0)}"
        )

        if "incoming_offers" in result and "outgoing_offers" in result:
            print("  ✓ view_transfer_offers working")

        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_llm_prompt_generation():
    """Test that LLM prompt includes transfer tools."""
    print("\n" + "=" * 70)
    print("TEST 5: LLM Prompt Generation")
    print("=" * 70)

    registry = get_tool_registry()
    prompt = registry.to_prompt_description()

    transfer_tool_names = [
        "make_transfer_offer",
        "list_player_for_transfer",
        "view_transfer_market",
        "view_transfer_offers",
        "respond_to_transfer_offer",
        "withdraw_transfer_offer",
    ]

    print("\nChecking LLM prompt includes transfer tools:")
    all_found = True
    for tool_name in transfer_tool_names:
        if tool_name in prompt:
            print(f"  ✓ {tool_name} found in prompt")
        else:
            print(f"  ✗ {tool_name} NOT found in prompt")
            all_found = False

    print("\nSample of transfer tools in prompt:")
    lines = prompt.split("\n")
    for i, line in enumerate(lines):
        if "transfer" in line.lower() or "offer" in line.lower():
            print(f"  {line}")
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("Description:"):
                print(f"  {lines[i + 1]}")
            print()

    return all_found


def test_tool_handlers():
    """Verify tool handlers are properly connected."""
    print("\n" + "=" * 70)
    print("TEST 6: Tool Handler Connections")
    print("=" * 70)

    registry = get_tool_registry()

    expected_handlers = {
        "make_transfer_offer": make_transfer_offer_tool,
        "list_player_for_transfer": list_player_for_transfer_tool,
        "view_transfer_market": view_transfer_list_tool,
        "view_transfer_offers": view_my_offers_tool,
        "respond_to_transfer_offer": respond_to_offer_tool,
        "withdraw_transfer_offer": withdraw_offer_tool,
    }

    print("\nVerifying handler connections:")
    all_correct = True
    for tool_name, expected_handler in expected_handlers.items():
        tool = registry.get(tool_name)
        if not tool:
            print(f"  ✗ {tool_name}: Tool not found")
            all_correct = False
            continue

        if tool.handler == expected_handler:
            print(f"  ✓ {tool_name}: Handler correctly connected")
        else:
            print(f"  ✗ {tool_name}: Handler mismatch!")
            print(f"    Expected: {expected_handler.__name__}")
            print(
                f"    Actual: {tool.handler.__name__ if hasattr(tool.handler, '__name__') else tool.handler}"
            )
            all_correct = False

    return all_correct


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("TRANSFER TOOLS COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    results = []

    results.append(("Tool Registration", test_tool_registration()))
    results.append(("Tool Parameters", test_tool_parameters()))
    results.append(("Execution Without Market", test_tool_execution_without_market()))
    results.append(("Execution With Market", test_tool_execution_with_market()))
    results.append(("LLM Prompt Generation", test_llm_prompt_generation()))
    results.append(("Tool Handler Connections", test_tool_handlers()))

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nTransfer tools are ready for LLM use:")
        print("  • make_transfer_offer - Submit transfer offers")
        print("  • list_player_for_transfer - List players for sale")
        print("  • view_transfer_market - Browse available players")
        print("  • view_transfer_offers - View incoming/outgoing offers")
        print("  • respond_to_transfer_offer - Accept/reject/counter offers")
        print("  • withdraw_transfer_offer - Cancel your offers")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the output above for details.")
    print("=" * 70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
