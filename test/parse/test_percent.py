from ftio.parse.percent import Percent


def test_basic_percentage():
    class MockTime:
        delta_t_agg = 100
        delta_t_agg_io = 50
        delta_t_com = 50
        delta_t_awr = 25
        delta_t_awa = 0
        delta_t_aw_lost = 0
        delta_t_arr = 0
        delta_t_ara = 0
        delta_t_ar_lost = 0
        delta_t_sw = 0
        delta_t_sr = 0
        delta_t_overhead = 0

    mock = MockTime()
    p = Percent(mock)

    assert p.TAWB == 25.0
    assert p.IAWB == 50.0
    assert p.CAWB == 50.0
