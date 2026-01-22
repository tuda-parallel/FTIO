import os
import tempfile
from ftio.parse.csv_reader import read_csv_file


def test_read_csv_file():
    csv_content = "rank,bandwidth,time,unit\n0,150,1,MB/s\n1,175,2,MB/s\n2,160,0,MB/s\n3,180,3,MB/s"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as file:
        file.write(csv_content)
        path = file.name

    try:
        result = read_csv_file(path)

        # cols
        assert len(result) == 4  # 4
        assert all(key in result for key in ["rank", "bandwidth", "time", "unit"])
        #row
        assert all(len(result[key]) == 4 for key in result)

        # values
        assert result["rank"] == ["0", "1", "2", "3"]
        assert result["bandwidth"] == ["150", "175", "160", "180"]
        assert result["time"] == ["1", "2", "0", "3"]
        assert result["unit"] == ["MB/s", "MB/s", "MB/s", "MB/s"]

    finally:
        os.unlink(path)


def test_read_csv_file_empty():
    csv_content = """col1,col2,col3"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as file:
        file.write(csv_content)
        path = file.name

    try:
        result = read_csv_file(path)

        assert len(result) == 3
        assert result["col1"] == []
        assert result["col2"] == []
        assert result["col3"] == []
    finally:
        os.unlink(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
