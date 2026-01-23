import numpy as np
import pytest
from ftio.plot.units import set_unit

"""
Tests for class ftio/plot/units.py
"""

def test_units_empty():
    arr = np.array([])
    unit, order = set_unit(arr)
    assert unit == 'B/s'
    assert order == 1


def test_units_gigabyte():
    arr = np.array([10000000000.0, 20000000000.0])
    unit, order = set_unit(arr)
    assert unit == 'GB/s'
    assert order == 1e-09


def test_units_megabyte():
    arr = np.array([10000000.0, 20000000.0])
    unit, order = set_unit(arr)
    assert unit == 'MB/s'
    assert order == 1e-06


def test_units_kilobyte():
    arr = np.array([10000.0, 20000.0])
    unit, order = set_unit(arr)
    assert unit == 'KB/s'
    assert order == 0.001


def test_units_byte():
    arr = np.array([100, 200])
    unit, order = set_unit(arr)
    assert unit == 'B/s'
    assert order == 1


def test_units_suffix():
    arr = np.array([10000000000.0])
    unit, order = set_unit(arr, suffix='tuda')
    assert unit == 'Gtuda'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])