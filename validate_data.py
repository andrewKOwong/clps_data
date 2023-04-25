import argparse
import json
import pathlib
import pandas as pd
from pandera import Column, DataFrameSchema, Check
# from pandera.errors import SchemaErrors
from clps.constants import survey_vars_keys as SVK

# Command line argument keys
INPUT_FP_KEY = "input_fp"
SURVEY_VARS_FP_KEY = "survey_vars_fp"
# Respondents id
PUMFID_KEY = "PUMFID"
# Respondents weights
WTPP_KEY = "WTPP"
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
        description="Script for validating CLPS data. Invalid checks will"
        " raise Pandera SchemaErrors. Consider piping error output to file"
        "for easier inspection, "
        "e.g. `python validate_data.py 2> validate_test_err.txt`."
    )
    parser.add_argument(
        "-i", "--input_fp",
        help="Path to the input data CSV file. Defaults to `data/clps.csv`.",
        default="data/clps.csv",
        dest=INPUT_FP_KEY
    )
    parser.add_argument(
        "-s", "--survey_vars_fp",
        help="Path to the survey variables JSON file."
             " Defaults to `data/survey_vars.json`.",
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

    This file is generated from extraction of the CLPS codebook.
    See: https://github.com/andrewKOwong/clps_survey_vars

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

    To be used as a Pandera Column Check function.

    Args:
        s (pd.Series): Column to be validated. Must be int-able columbn.
        survey_var (dict): Dictionary of a single survey variable.
    """
    # Codebook extract are strings (e.g. "01"), so convert to int
    codes = [int(e) for e in survey_var[SVK.CODE]]
    return s.isin(codes)


def expand_PROBCNTP_str_code(code: str) -> list[int]:
    """Helper func to expand PROBCNTP string code to a list of ints.

    Args:
        code (str): PROBCNTP code to be expanded, i.e. "01 - 16".

    Returns:
        list[int]: List of ints, i.e. [1, 2, ..., 16].
    """
    expanded = code.split(" - ")
    expanded = list(range(int(expanded[0]),
                          int(expanded[1]) + 1))
    return expanded


def validate_PROBCNTP_codes(s, survey_var):
    """Helper func to validate PROBCNTP codes.

    To be used as a Pandera Column Check function.
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
            codes.extend(expand_PROBCNTP_str_code(c))
    return s.isin(codes)


def validate_VERDATE_codes(s, survey_var):
    """Helper func to validate VERDATE codes.

    To be used as a Pandera Column Check function.
    This is a special case, as VERDATE only has a date string for its code.

    Args:
        s (pd.Series): Column to be validated.
        survey_var (dict): Dictionary of a single survey variable."""
    codes = survey_var[SVK.CODE]
    return s.isin(codes)


def validate_freqs(s: pd.Series, survey_var: dict) -> bool:
    """Helper func to validate frequencies against the codebook.

    To be used as a Pandera Column Check function.

    Args:
        s (pd.Series): Column to be validated.
        survey_var (dict): Dictionary of a single survey variable.

    Returns:
        bool: True if frequencies match, False otherwise."""
    # Get value counts of the column, and reorder according to their order
    # in the codebook.
    codes = [int(e) for e in survey_var[SVK.CODE]]
    freqs = [int(e) for e in survey_var[SVK.FREQUENCY]]
    # Reorder the value_counts according to the codebook,
    # then drop the index to compare.
    s = s.value_counts().reindex(codes)
    s = s.reset_index(drop=True)
    # Compare to the frequencies in the codebook.
    return s.equals(pd.Series(freqs))


def validate_PROBCNTP_freqs(s: pd.Series, survey_var: dict):
    """Helper func to validate PROBCNTP frequencies.


    To be used as a Pandera Column Check function.
    This is a special case, as the codebook entry collapses codes 01 - 16
    to a single '01 - 16' text string.

    Args:
        s (pd.Series): Column to be validated.
        survey_var (dict): Dictionary of a single survey variable.

    Returns:
        bool: True if frequencies match, False otherwise."""
    # The strategy here is to take all the codes that fall under the range
    # 01 - 16, and sum their frequencies. Then, compare the sum to the
    # frequency of the '01 - 16' code.

    # A placeholder indexer for the summed frequencies.
    SUMMED_CODE = -1
    # Get frequencies
    freqs = [int(e) for e in survey_var[SVK.FREQUENCY]]
    # Get the raw codes, and split into intable codes and the string code
    raw_codes = survey_var[SVK.CODE]
    int_codes = [int(e) for e in raw_codes if e.isdigit()]
    str_code = [e for e in raw_codes if not e.isdigit()]
    # Check that there should only be one string code.
    try:
        assert len(str_code) == 1
    except AssertionError:
        raise ValueError("Expected only one string code in PROBCNTP codes.")
    # Expand the string code into a list of ints
    expand_str_code = expand_PROBCNTP_str_code(str_code[0])
    # Final codes are what the indexes of the final pandas series will be.
    # Convert int-able raw codes, otherwise use the summed code placeholder
    final_codes = [int(e) if e.isdigit() else SUMMED_CODE for e in raw_codes]
    # Now work with the actual data column.
    s = s.value_counts()
    # Split the data into int-able codes and the codes that fall under the
    # string code range.
    int_s = s[s.index.isin(int_codes)]
    str_s = s[s.index.isin(expand_str_code)]
    # Sum the string code frequencies and reindex them with the placeholder
    # indexer.
    str_s = pd.Series([str_s.sum()], index=[SUMMED_CODE])
    # Put everything back together, reindex into the original order of the
    # codebook..
    final_s = pd.concat([int_s, str_s])
    final_s = final_s.reindex(final_codes)
    # Drop the indexes now that the order is correct, and compare.
    final_s = final_s.reset_index(drop=True)
    return final_s.equals(pd.Series(freqs))


def validate_VERDATE_freqs(s, survey_var):
    """Helper func to validate VERDATE frequencies.

    To be used as a Pandera Column Check function.
    This is a special case, as VERDATE only has a date string for its code.

    Args:
        s (pd.Series): Column to be validated.
        survey_var (dict): Dictionary of a single survey variable.

    Returns:
        bool: True if frequencies match, False otherwise."""
    freqs = [int(e) for e in survey_var[SVK.FREQUENCY]]
    # Get value counts of the column, and reorder according to their order
    # in the codebook.
    s = s.value_counts().reindex(survey_var[SVK.CODE])
    # Reset index now that order is correct.
    s = s.reset_index(drop=True)
    # Compare to the frequencies in the codebook.
    return s.equals(pd.Series(freqs))


def validate_wt_freqs(
        df: pd.DataFrame,
        col_key: str,
        survey_var: dict) -> bool:
    """Wide DataFrame check function to validate weighted frequencies.

    This is meant to be used for checks that operate on the entire dataframe,
    e.g. under DataFrameSchema(checks=[...]). The reason for using this rather
    than a Column check is that weighted frequencies require the weight column
    and a survey variable column simultaneously (i.e. a weighted frequency is a
    sum of the weights grouped by answer codes.)

    Args:
        df (pd.DataFrame): input DataFrame to be validated."""
    # Ordered codes and weighted frequencies from codebook
    codes = [int(e) for e in survey_var[SVK.CODE]]
    wt_freqs = [int(e) for e in survey_var[SVK.WEIGHTED_FREQUENCY]]
    # Get the column and the weights, sum the weights,
    # and reorder according to the codebook.
    out = (
        df[[col_key, WTPP_KEY]].copy()
        .groupby(col_key)
        .sum()
        [WTPP_KEY]
        .reindex(codes)
        .reset_index(drop=True)
        # Weights are many decimal places, so round to match codebook.
        .round()
        .astype(int)
    )
    # Compare to the weighted frequencies in the codebook.
    return out.equals(pd.Series(wt_freqs))


def validate_VERDATE_wt_freqs(
        df: pd.DataFrame,
        col_key: str,
        survey_var: dict) -> bool:
    """Wide DataFrame check function to validate VERDATE weighted frequencies.

    This is basically the same as validate_wt_freqs, but without inting the
    codes, as VERDATE only has a date string for its code.

    Args:
        df (pd.DataFrame): input DataFrame to be validated."""
    # Ordered codes and weighted frequencies from codebook
    codes = survey_var[SVK.CODE]
    wt_freqs = [int(e) for e in survey_var[SVK.WEIGHTED_FREQUENCY]]
    # Get the column and the weights, sum the weights,
    # and reorder according to the codebook.
    out = (
        df[[col_key, WTPP_KEY]].copy()
        .groupby(col_key)
        .sum()
        [WTPP_KEY]
        .reindex(codes)
        .reset_index(drop=True)
        # Weights are many decimal places, so round to match codebook.
        .round()
        .astype(int)
    )
    # Compare to the weighted frequencies in the codebook.
    return out.equals(pd.Series(wt_freqs))


def validate_PROBCNTP_wt_freqs(
        df: pd.DataFrame,
        col_key: str,
        survey_var: dict) -> bool:
    """Wide DataFrame check function to validate PROBCNTP weighted frequencies.

    This is a special case, as the codebook entry collapses codes 01 - 16
    to a single '01 - 16' text string.

    Args:
        df (pd.DataFrame): input DataFrame to be validated.
        survey_var (dict): Dictionary of a single survey variable.

    Returns:
        bool: True if frequencies match, False otherwise."""
    SUMMED_CODE = -1
    # Ordered codes and weighted frequencies from codebook
    wt_freqs = [int(e) for e in survey_var[SVK.WEIGHTED_FREQUENCY]]

    raw_codes = survey_var[SVK.CODE]
    str_code = [e for e in raw_codes if not e.isdigit()]
    try:
        assert len(str_code) == 1
    except AssertionError:
        raise ValueError("Expected only one string code in PROBCNTP codes.")
    expand_str_code = expand_PROBCNTP_str_code(str_code[0])
    final_codes = [int(e) if e.isdigit() else SUMMED_CODE for e in raw_codes]
    # Get the column and the weights, sum the weights,
    # and reorder according to the codebook.
    out = (
        df[[col_key, WTPP_KEY]].copy()
        .assign(
            **{col_key: lambda df:
                df[col_key].replace(to_replace=expand_str_code,
                                    value=SUMMED_CODE)})
        .groupby(col_key)
        .sum()
        [WTPP_KEY]
        .reindex(final_codes)
        .reset_index(drop=True)
        # Weights are many decimal places, so round to match codebook.
        .round()
        .astype(int)
    )
    # Compare to the weighted frequencies in the codebook.
    return out.equals(pd.Series(wt_freqs))


def define_schema(survey_vars: dict) -> DataFrameSchema:
    """Define a validation schema for the data.

    Args:
        survey_vars (dict): Dictionary of survey variables, keyed to each
            survey variable name.

    Returns:
        DataFrameSchema: Pandera schema for the data."""
    # These are the variables that don't have answers
    NON_ANSWER_VARS = [PUMFID_KEY, WTPP_KEY]

    SPECIAL_VARS = [PUMFID_KEY, WTPP_KEY, PROBCNTP_KEY, VERDATE_KEY]
    probcntp = survey_vars[PROBCNTP_KEY]
    verdate = survey_vars[VERDATE_KEY]
    survey_vars_normal = {
        k: v for k, v in survey_vars.items() if k not in SPECIAL_VARS}

    # Wide data checks to handle the weighted frequencies.
    wt_freq_checks = []
    for k in survey_vars_normal:
        current_var = survey_vars_normal[k]
        col_kwargs = {'coerce': True}
        check = Check(
            validate_wt_freqs, survey_var=current_var, col_key=k)
        wt_freq_checks.append(check)

    # Add wt_freq checks for VERDATE
    wt_freq_checks.append(
        Check(
            validate_VERDATE_wt_freqs,
            survey_var=verdate,
            col_key=VERDATE_KEY)
    )
    # Add wt_freq checks for PROBCNTP
    wt_freq_checks.append(
        Check(
            validate_PROBCNTP_wt_freqs,
            survey_var=probcntp,
            col_key=PROBCNTP_KEY)
    )
    # Schema for non answer variables.
    schema = DataFrameSchema(
        columns={
            PUMFID_KEY: Column(int, unique=True, coerce=True),
            WTPP_KEY: Column(float, coerce=True)},
        checks=wt_freq_checks
    )
    # All the other answer-containing variables have answer codes.
    # Check these against the codebook extract.
    # For loop through only variables with answer sections.
    for k in [k for k in survey_vars.keys() if k not in NON_ANSWER_VARS]:
        current_var = survey_vars[k]
        col_kwargs = {'coerce': True}
        if k == VERDATE_KEY:
            # This is a special case, as the codebook entry is a date string
            col_kwargs['dtype'] = str
            col_kwargs['checks'] = [
                Check(validate_VERDATE_codes, survey_var=current_var),
                Check(validate_VERDATE_freqs, survey_var=current_var)]
        elif k == PROBCNTP_KEY:
            col_kwargs['dtype'] = int
            col_kwargs['checks'] = [
                Check(validate_PROBCNTP_codes, survey_var=current_var),
                Check(validate_PROBCNTP_freqs, survey_var=current_var)]
        else:
            col_kwargs['dtype'] = int
            col_kwargs['checks'] = [
                Check(validate_codes, survey_var=current_var),
                Check(validate_freqs, survey_var=current_var)]
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
    schema.validate(raw_df, lazy=True)
    # try:
    #     schema.validate(raw_df, lazy=True)
    # except SchemaErrors as err:
    #     global failure_cases
    #     failure_cases = err.failure_cases
    #     global error_data
    #     error_data = err.data
    #     raise err


if __name__ == "__main__":
    main()
