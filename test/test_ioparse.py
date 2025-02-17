"""
Functions for testing the ioparse functionality of the ftio package.
"""

import os
from ftio.util.ioparse import main

def test_ioparse():
    """Test the ioparse functionality."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ioparse", file]
    main(args)
    assert True


