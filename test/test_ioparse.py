from ftio.util.ioparse import main


def test_ioplot():
    file = "../examples/8.jsonl"
    args = ["ioparse", file]
    main(args)
    assert True
