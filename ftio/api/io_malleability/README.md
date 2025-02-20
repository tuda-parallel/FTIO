# XLSX to JSON Converter

This Python script converts an Excel file (XLSX format) to a JSON file. It extracts specific data from the Excel sheet, such as I/O bandwidth, time stamps, rank, and total bytes, and outputs them in a structured JSON format.

## Requirements

- Python 3.x
- pandas

You can install the required dependencies using pip:

```bash
pip install pandas openpyxl
```

## Usage

To run the script, simply execute the Python file from the command line. You can optionally specify the path to the Excel file and use the interactive mode to select the relevant field for the bandwidth.

```bash
python parse_xlsx.py --file <path_to_excel_file> [--interactive]
```

If no file is provided, the default file `IOTraces.xlsx` will be used.

### Example

```bash
python parse_xlsx.py --file IOTraces.xlsx
```

This will convert the data from `IOTraces.xlsx` to `output.json`.

### Interactive Mode Example

```bash
python parse_xlsx.py --file IOTraces.xlsx --interactive
```

This will prompt you to select the column to map to the bandwidth.

## Output

The script will generate a `output.json` file containing the following structure:

```json
{
    "write_sync": {
        "total_bytes": <total_bytes_value>,
        "number_of_ranks": <ranks_value>,
        "bandwidth": {
            "b_overlap_avr": [<bandwidth_values>],
            "t_overlap": [<time_stamp_values>]
        }
    }
}
```

Afterwards simply call `ftio`:

```bash
ftio output.json
```
