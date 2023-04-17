import argparse
import pathlib
import pandas as pd
from pandera import Column, DataFrameSchema


INPUT_FP_KEY = "input_fp"


def get_args() -> dict:
    """Parse command line arguments and return as dict."""
    # Set up parser
    parser = argparse.ArgumentParser(
        description="Validate CLPS data."
    )
    parser.add_argument(
        "-i", "--input_fp",
        help="Path to the input data CSV file.",
        default="data/clps.csv",
        dest=INPUT_FP_KEY
    )
    # Return dict of command line arguments
    return vars(parser.parse_args())


def read_data(fp: str) -> pd.DataFrame:
    """Read data from CSV file and return as pandas DataFrame. """
    # Check file exists and is a file
    p = pathlib.Path(fp)
    try:
        assert p.exists()
    except AssertionError:
        raise FileNotFoundError(f"File not found: {fp}")
    try:
        assert p.is_file()
    except AssertionError:
        raise FileNotFoundError(f"Not a file: {fp}")
    # Otherwise read the data
    return pd.read_csv(fp)


def define_schema() -> DataFrameSchema:
    schema = DataFrameSchema({
        "PUMFID": Column(int, unique=True)
    })
    return schema


def main() -> None:
    """Main entry point for the script."""
    # Parse arguments and get input file path, and read data.
    args = get_args()
    input_fp = args[INPUT_FP_KEY]
    raw_df = read_data(input_fp)
    # Define a pandera schema
    schema = define_schema()
    # Validate the data
    schema(raw_df, lazy=True)


if __name__ == "__main__":
    main()
