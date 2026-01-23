from ftio.parse.percent import Percent


def test_basic_percentage():
    class MockTime:
        delta_t_agg=100,
        delta_t_agg_io=50,
        delta_t_awr=25,
    mock = MockTime()

    p = Percent(mock)

    assert p.TAWB == 25.0
    assert p.TAWT == 0
    assert p.TAWD == 0
    assert p.IAWB == 0
    assert p.IAWT == 0
    assert p.IAWD == 0
    assert p.CAWB == 0
    assert p.CAWT == 0
    assert p.CAWD == 0
