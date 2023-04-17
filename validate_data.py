import argparse
import json
import pathlib
import pandas as pd
from pandera import Column, DataFrameSchema
from clps.constants import survey_vars_keys as svk


INPUT_FP_KEY = "input_fp"
SURVEY_VARS_FP_KEY = "survey_vars_fp"


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
    parser.add_argument(
        "-s", "--survey_vars_fp",
        help="Path to the survey variables JSON file.",
        default="data/survey_vars.json",
        dest=SURVEY_VARS_FP_KEY
    )
    # Return dict of command line arguments
    return vars(parser.parse_args())


def check_file_exists(fp: str) -> None:
    """Raise if file does not exist or isn't a file."""
    p = pathlib.Path(fp)
    try:
        assert p.exists()
    except AssertionError:
        raise FileNotFoundError(f"File not found: {fp}")
    try:
        assert p.is_file()
    except AssertionError:
        raise FileNotFoundError(f"Not a file: {fp}")


def read_data(fp: str) -> pd.DataFrame:
    """Read data from CSV file and return as pandas DataFrame. """
    check_file_exists(fp)
    return pd.read_csv(fp)


def read_survey_vars(fp: str) -> dict:
    """Read survey variables from JSON file.

    Args:
        fp (str): Path to the JSON file.

    Returns:
        dict: Dictionary of survey variables, keyed to each survey variable
            name.
    """
    check_file_exists(fp)
    # Load the JSON file
    with open(fp, "r") as f:
        data = json.load(f)
    # Format the JSON to key by variable name
    return {e[svk.VAR_NAME]: e for e in data}


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
    # Read survey variables JSON
    survey_vars_fp = args[SURVEY_VARS_FP_KEY]
    survey_vars = read_survey_vars(survey_vars_fp)
    # Define a pandera schema
    schema = define_schema()
    # Validate the data
    schema(raw_df, lazy=True)


if __name__ == "__main__":
    main()
