from ftio.util.ioplot import main


def test_ioplot():
    file = "../examples/tmio/8.jsonl"
    args = ["ioplot", file, "--no_disp"]
    main(args)
    assert True
