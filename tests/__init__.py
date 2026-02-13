#!/usr/bin/env python3
"""单元测试套件 for Football Manager

运行所有测试:
    pytest tests/ -v

运行特定测试:
    pytest tests/test_tactics_engine.py -v
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
