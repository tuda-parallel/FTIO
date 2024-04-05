from ftio.cli.ftio_core import main
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.post.processing import label_phases

def test_ftio():
    args = parse_args(["-e", "no"], "ftio")
    _ = core([], args)
    assert True

def test_ftio_autocorrelation():
    args = parse_args(["-e", "no", "-c"], "ftio")
    _ = core([], args)
    assert True

def test_ftio_n_freq():
    file = "../examples/8.jsonl"
    args = ["ftio", file, "-e", "no", "-n", "5"]
    _, args = main(args)
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


def test_ftio_plot():
    file = "../examples/8.jsonl"
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    _ = label_phases(prediction, args)
    assert True 


def test_ftio_display_prediction():
    file = "../examples/8.jsonl"
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    display_prediction("ftio", prediction)
    assert True