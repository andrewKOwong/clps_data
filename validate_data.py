import argparse
import json
import pathlib
import pandas as pd
from pandera import Column, DataFrameSchema, Check
from clps.constants import survey_vars_keys as SVK


INPUT_FP_KEY = "input_fp"
SURVEY_VARS_FP_KEY = "survey_vars_fp"
# This survey variable is a special case, as it's codebook actually
# collapses codes 01 - 16 as a "01 - 16" string.
PROBCNTP_KEY = "PROBCNTP"
# This survey variable is a special case, as it's codebook only has a
# date string for its code.
VERDATE_KEY = "VERDATE"


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
    return {e[SVK.VAR_NAME]: e for e in data}


def validate_codes(s: pd.Series, survey_var: dict) -> bool:
    """Helper func to validate codes against the codebook.

    Args:
        s (pd.Series): Column to be validated. Must be intable columbn.
        survey_var (dict): Dictionary of a single survey variable.
    """
    # Codebook extract are strings (e.g. "01"), so convert to int
    codes = [int(e) for e in survey_var[SVK.CODE]]
    return s.isin(codes)


def validate_PROBCNTP_codes(s, survey_var):
    """Helper func to validate PROBCNTP codes.

    This is a special case, as the codebook entry collapses codes 01 - 16
    to a single '01 - 16' text string.

    Args:
        s (pd.Series): Column to be validated.
        survey_var (dict): Dictionary of a single survey variable.
    """
    codes = []
    for c in survey_var[SVK.CODE]:
        try:
            # Normal intable codes
            c = codes.append(int(c))
        except ValueError:
            # Expand '01 - 16' string to list of ints
            c = c.split(" - ")
            c = list(range(int(c[0]), int(c[1]) + 1))
            codes.extend(c)
    return s.isin(codes)


def validate_VERDATE_codes(s, survey_var):
    """Helper func to validate VERDATE codes.

    This is a special case, as VERDATE only has a date string for its code.

    Args:
        s (pd.Series): Column to be validated.
        survey_var (dict): Dictionary of a single survey variable."""
    codes = survey_var[SVK.CODE]
    return s.isin(codes)


def define_schema(survey_vars: dict) -> DataFrameSchema:
    """Define a validation schema for the data.

    Args:
        survey_vars (dict): Dictionary of survey variables, keyed to each
            survey variable name.

    Returns:
        DataFrameSchema: Pandera schema for the data."""
    # These are the variables that don't have answers
    NON_ANSWER_VARS = ['PUMFID', 'WTPP']
    # Schema for non answer variables.
    schema = DataFrameSchema({
        "PUMFID": Column(int, unique=True, coerce=True),
        "WTPP": Column(float, coerce=True),
    })
    # All the other answer-containing variables have answer codes.
    # Check these against the codebook extract.
    # For loop through only variables with answer sections.
    for k in [k for k in survey_vars.keys() if k not in NON_ANSWER_VARS]:
        current_var = survey_vars[k]
        col_kwargs = {'coerce': True}
        if k == VERDATE_KEY:
            # This is a special case, as the codebook entry is a date string
            col_kwargs['dtype'] = str
            col_kwargs['checks'] = Check(
                validate_VERDATE_codes, survey_var=current_var)
        elif k == PROBCNTP_KEY:
            col_kwargs['dtype'] = int
            col_kwargs['checks'] = Check(
                validate_PROBCNTP_codes, survey_var=current_var)
        else:
            col_kwargs['dtype'] = int
            col_kwargs['checks'] = Check(
                validate_codes, survey_var=current_var)
        # Update the schema
        schema = schema.add_columns({k: Column(**col_kwargs)})
    # Note, by default pandera disallows null values, which matches
    # the assumption that this dataset should not have null values.
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
    # Generate validation schema
    schema = define_schema(survey_vars)
    # Validate the data
    schema(raw_df, lazy=True)


if __name__ == "__main__":
    main()
