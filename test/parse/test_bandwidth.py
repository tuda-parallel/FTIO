import numpy as np
import pytest

from ftio.parse.bandwidth import overlap, overlap_core_safe, overlap_two_series_safe, merge_overlaps_safe


def test_overlap_return_lists():
    b = [100.0, 200.0]
    t_s = [0.0, 5.0]
    t_e = [10.0, 15.0]

    b_out, t_out = overlap(b, t_s, t_e)

    assert isinstance(b_out, list)
    assert isinstance(t_out, list)


def test_overlap():
    b = [50.0]
    t_s = [1.0]
    t_e = [3.0]

    b_out, t_out = overlap(b, t_s, t_e)

    assert b_out == [50.0, 0.0]
    assert t_out == [1.0, 3.0]


def test_overlap_core_safe_one_operation():
    b = np.array([100.0])
    t_s = np.array([0.0])
    t_e = np.array([10.0])
    id_s = np.argsort(t_s)
    id_e = np.argsort(t_e)

    b_out, t_out = overlap_core_safe(b, t_s, t_e, id_s, id_e)

    assert b_out == [100.0, 0.0]
    assert t_out == [0.0, 10.0]


def test_overlap_core_safe_mult_operation():
    b = np.array([10.0, 20.0, 30.0])
    t_s = np.array([0.0, 2.0, 4.0])
    t_e = np.array([10.0, 8.0, 6.0])
    id_s = np.argsort(t_s)
    id_e = np.argsort(t_e)

    b_out, t_out = overlap_core_safe(b, t_s, t_e, id_s, id_e)

    assert b_out == [10.0, 30.0, 60.0, 30.0, 10.0, 0.0]
    assert t_out == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]


def test_overlap_core_safe_unsorted():
    b = np.array([200.0, 100.0])
    t_s = np.array([5.0, 0.0])
    t_e = np.array([15.0, 10.0])
    id_s = np.argsort(t_s)
    id_e = np.argsort(t_e)

    b_out, t_out = overlap_core_safe(b, t_s, t_e, id_s, id_e)

    assert b_out == [100.0, 300.0, 200.0, 0.0]
    assert t_out == [0.0, 5.0, 10.0, 15.0]


def test_overlap_two_series_safe_non_overlapping():
    b1 = [100.0, 0.0]
    t1 = [0.0, 5.0]
    b2 = [200.0, 0.0]
    t2 = [10.0, 15.0]

    b_out, t_out = overlap_two_series_safe(b1, t1, b2, t2)

    assert np.array_equal(b_out, [100.0, 0.0, 200.0, 0.0])
    assert np.array_equal(t_out, [0.0, 5.0, 10.0, 15.0])


def test_overlap_two_series_safe_overlapping():
    b1 = [100.0, 0.0]
    t1 = [0.0, 10.0]
    b2 = [50.0, 0.0]
    t2 = [5.0, 15.0]

    b_out, t_out = overlap_two_series_safe(b1, t1, b2, t2)

    assert np.array_equal(b_out, [100.0, 150.0, 50.0, 0.0])
    assert np.array_equal(t_out, [0.0, 5.0, 10.0, 15.0])


def test_overlap_two_series_safe_same_timestamp():
    b1 = [100.0]
    t1 = [5.0]
    b2 = [200.0]
    t2 = [5.0]

    b_out, t_out = overlap_two_series_safe(b1, t1, b2, t2)

    assert np.array_equal(b_out, [300.0])
    assert np.array_equal(t_out, [5.0])


def test_overlap_two_series_safe_empty_series():
    b1 = [100.0, 50.0]
    t1 = [0.0, 5.0]
    b2 = []
    t2 = []

    b_out, t_out = overlap_two_series_safe(b1, t1, b2, t2)

    assert np.array_equal(b_out, [100.0, 50.0])
    assert np.array_equal(t_out, [0.0, 5.0])


def test_merge_overlaps_safe_no_duplicate():
    b = [10.0, 20.0, 30.0]
    t = [1.0, 2.0, 3.0]

    b_out, t_out = merge_overlaps_safe(b, t)

    np.testing.assert_array_equal(b_out, [10.0, 20.0, 30.0])
    np.testing.assert_array_equal(t_out, [1.0, 2.0, 3.0])


def test_merge_overlaps_safe_one():
    b = [10.0, 20.0, 30.0]
    t = [1.0, 1.0, 2.0]

    b_out, t_out = merge_overlaps_safe(b, t)

    np.testing.assert_array_equal(b_out, [30.0, 30.0])
    np.testing.assert_array_equal(t_out, [1.0, 2.0])


def test_merge_overlaps_safe_mult():
    b = [5.0, 10.0, 15.0, 20.0]
    t = [3.0, 3.0, 3.0, 3.0]

    b_out, t_out = merge_overlaps_safe(b, t)

    np.testing.assert_array_equal(b_out, [50.0])
    np.testing.assert_array_equal(t_out, [3.0])


def test_merge_overlaps_safe_unsorted():
    b = [30.0, 10.0, 20.0]
    t = [3.0, 1.0, 1.0]

    b_out, t_out = merge_overlaps_safe(b, t)

    np.testing.assert_array_equal(b_out, [30.0, 30.0])
    np.testing.assert_array_equal(t_out, [1.0, 3.0])


def test_merge_overlaps_safe_empty():
    b = []
    t = []

    b_out, t_out = merge_overlaps_safe(b, t)

    assert len(b_out) == 0
    assert len(t_out) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])