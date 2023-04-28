import pandas as pd
from clps.constants import survey_vars_keys as SVK

REGION_KEY = 'REGION'


def filter_by_variable(df: pd.DataFrame, cols_to_keep: list) -> pd.DataFrame:
    """Filter a dataframe by a list of columns to keep."""
    return df[cols_to_keep].copy()


def filter_by_region(df: pd.DataFrame, region: int) -> pd.DataFrame:
    """Filter a dataframe by a region code."""
    return df[df[REGION_KEY] == region].copy()
