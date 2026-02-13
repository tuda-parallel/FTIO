import pytest

from ftio.parse.input_template import init_data


def test_init_data_default():
    args = ["a", "b", "c"]
    mode, io_data, io_time = init_data(args)
    assert mode == "write_sync"


def test_init_data_default_write_sync():
    class Args:
        mode = "w sync"

    args = Args()
    mode, io_data, io_time = init_data(args)
    assert mode == "write_sync"


def test_init_data_default_read_async():
    class Args:
        mode = "r async"

    args = Args()
    mode, io_data, io_time = init_data(args)
    assert mode == "read_async_t"


def test_init_data_return():
    class Args:
        mode = "r async"

    args = Args()
    result = init_data(args)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_init_data_empty():
    class Args:
        mode = ""

    args = Args()
    mode, io_data, io_time = init_data(args)
    assert mode == "read_sync"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
