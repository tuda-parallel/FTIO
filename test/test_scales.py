"""
Functions for testing the parsing functionality of the ftio package.
"""

import os
from ftio.freq.helper import get_mode
from ftio.parse.extract import extract_fields, get_time_behavior_and_args
from ftio.parse.scales import Scales


def test_scales():
    """
    Test the Scales class initialization.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/ior/collective/1536_new.json")
    args = [
        "ftio",
        file,
        "-e",
        "no",
    ]
    data = Scales(args)
    assert True


def test_assign_data():  # type: ignore
    """
    Test the assign_data method of the Scales class.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/ior/collective/1536_new.json")
    args = [
        "ftio",
        file,
        "-e",
        "no",
    ]
    data = Scales(args)
    # assign the different fields in data (read/write sync/async and io time)
    data.assign_data()
    # extract mode of interest
    _ = get_mode(data, data.args.mode)
    assert True


def test_get_io_mode():
    """
    Test the get_io_mode method of the Scales class.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/ior/collective/1536_new.json")
    args = [
        "ftio",
        file,
        "-e",
        "no",
    ]
    data = Scales(args)
    # assign the different fields in data (read/write sync/async and io time)
    args = data.args
    df = data.get_io_mode(args.mode)
    assert True


def test_get_time_behavior_and_args():
    """
    Test the get_time_behavior_and_args function.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/ior/collective/1536_new.json")
    args = [
        "ftio",
        file,
        "-e",
        "no",
    ]
    data, args = get_time_behavior_and_args(args)
    assert True


def test_extract_fields():
    """
    Test the extract_fields function.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/ior/collective/1536_new.json")
    args = [
        "ftio",
        file,
        "-e",
        "no",
    ]
    data, args = get_time_behavior_and_args(args)
    b_sampled, time_b, ranks, total_bytes = extract_fields(data)
    assert True
