from ftio.cli.ftio_core import main
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args


def test_ftio():
    args = parse_args(["-e", "no"], "ftio")
    prediction, dfs = core([], args)
    assert True


def test_ftio_zscore():
    file = "../examples/8.jsonl"
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    assert prediction["t_start"] == 0.05309


def test_ftio_dbscan():
    file = "../examples/8.jsonl"
    args = ["ftio", file, "-e", "no", "-o", "dbscan"]
    prediction, args = main(args)
    assert prediction["t_start"] == 0.05309


def test_ftio_lof():
    file = "../examples/8.jsonl"
    args = ["ftio", file, "-e", "no", "-o", "lof"]
    prediction, args = main(args)
    assert prediction["t_start"] == 0.05309
