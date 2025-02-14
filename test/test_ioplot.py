"""
Functions for testing the ioplot functionality of the ftio package.
"""

import os
from ftio.util.ioplot import main

def test_ioplot():
    """Test the ioplot functionality with no display option."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ioplot", file, "--no_disp"]
    main(args)
    assert True
