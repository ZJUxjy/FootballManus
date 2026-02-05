"""Unicode-aware table formatting using wcwidth.

Provides proper alignment for mixed ASCII and CJK (Chinese, Japanese, Korean) text.
"""

from typing import List, Any, Optional
from wcwidth import wcswidth


def display_width(text: str) -> int:
    """Calculate display width considering Unicode characters."""
    return wcswidth(str(text)) if text else 0


def pad_string(text: str, width: int, align: str = "left") -> str:
    """Pad string to specified display width."""
    text = str(text)
    current_width = display_width(text)

    if current_width >= width:
        return text

    padding = " " * (width - current_width)

    if align == "right":
        return padding + text
    elif align == "center":
        left_pad = padding[: len(padding) // 2]
        right_pad = padding[len(padding) // 2 :]
        return left_pad + text + right_pad
    else:  # left
        return text + padding


class UnicodeTable:
    """Table formatter with proper Unicode width support."""

    def __init__(self, headers: List[str], column_widths: Optional[List[int]] = None):
        """
        Initialize table.

        Args:
            headers: Column headers
            column_widths: Optional fixed column widths. If None, auto-calculated.
        """
        self.headers = headers
        self.column_widths = column_widths or []
        self.rows: List[List[str]] = []

        # Calculate widths if not provided
        if not self.column_widths:
            self.column_widths = [display_width(h) + 2 for h in headers]

    def add_row(self, row: List[Any]):
        """Add a row to the table."""
        str_row = [str(cell) for cell in row]
        self.rows.append(str_row)

        # Update column widths
        for i, cell in enumerate(str_row):
            cell_width = display_width(cell) + 2  # +2 for padding
            if i < len(self.column_widths):
                self.column_widths[i] = max(self.column_widths[i], cell_width)
            else:
                self.column_widths.append(cell_width)

    def _format_row(self, cells: List[str], align: str = "left") -> str:
        """Format a row with proper alignment."""
        formatted_cells = []
        for i, cell in enumerate(cells):
            if i < len(self.column_widths):
                width = self.column_widths[i]
                formatted_cells.append(pad_string(cell, width, align))
            else:
                formatted_cells.append(str(cell))
        return " | ".join(formatted_cells)

    def _create_separator(self) -> str:
        """Create separator line."""
        parts = []
        for width in self.column_widths:
            parts.append("-" * width)
        return "-+-".join(parts)

    def render(self) -> str:
        """Render the table as string."""
        lines = []

        # Header
        lines.append(self._format_row(self.headers, "center"))
        lines.append(self._create_separator())

        # Rows
        for row in self.rows:
            lines.append(self._format_row(row, "left"))

        return "\n".join(lines)


def format_player_table(players: List[Any], max_rows: int = 25) -> str:
    """Format player list as a Unicode-aware table."""
    table = UnicodeTable(["#", "Name", "Pos", "Age", "CA", "PA", "Value"])

    for i, player in enumerate(players[:max_rows], 1):
        name = getattr(player, "full_name", "Unknown")[:20]
        pos = getattr(player, "position", "-")
        pos_str = pos if isinstance(pos, str) else getattr(pos, "value", "-")
        age = str(getattr(player, "age", "-"))
        ca = f"{getattr(player, 'current_ability', 0):.1f}"
        pa = f"{getattr(player, 'potential_ability', 0):.1f}"
        value = f"£{getattr(player, 'market_value', 0) / 1_000_000:.1f}M"

        table.add_row([i, name, pos_str, age, ca, pa, value])

    return table.render()


def test_unicode_table():
    """Test Unicode table formatting."""
    print("Testing Unicode Table Formatting")
    print("=" * 80)

    # Test with mixed ASCII and Chinese
    table = UnicodeTable(["Name", "Position", "Value"])

    test_data = [
        ["Son, Heung-Min", "LW", "£300.0M"],
        ["孙兴慜", "左边锋", "£300.0M"],
        ["Bellingham, Jude", "CM", "£150.0M"],
        ["贝林厄姆", "中场", "£150.0M"],
    ]

    for row in test_data:
        table.add_row(row)

    print(table.render())
    print()

    # Test display width calculation
    print("Display Width Tests:")
    test_strings = [
        "Son, Heung-Min",
        "孙兴慜",
        "Bellingham",
        "贝林厄姆",
    ]

    for s in test_strings:
        print(f"  '{s}' -> width: {display_width(s)}")


if __name__ == "__main__":
    test_unicode_table()
