import pandas as pd
import clps.survey_vars_utils as svu

REGION_KEY = 'REGION'
WEIGHT_KEY = 'WTPP'
VALID_SKIP = 'Valid skip'


def filter_by_variable(df: pd.DataFrame, cols_to_keep: list) -> pd.DataFrame:
    """Filter a dataframe by a list of columns to keep."""
    return df[cols_to_keep].copy()


def filter_by_region(df: pd.DataFrame, region: int) -> pd.DataFrame:
    """Filter a dataframe by a region code."""
    return df[df[REGION_KEY] == region].copy()


def prepare_plotable_df(
        clps_df: pd.DataFrame,
        var_to_plot: str,
        plot_weighted: bool = True,
        region_filter: int | None = None,
        groupby_key: str | None = None,
        weighted_index_name: str = 'Weighted Count',
        unweighted_index_name: str = 'Count',
        remove_valid_skips: bool = True,
        ) -> pd.DataFrame:
    """Prepare the data for plotting."""
    # TODO unmagic the filepath
    svs = svu.load_keyed_survey_vars('data/survey_vars.json')
    sv = svu.extract_survey_var(svs, var_to_plot)
    sv = svu.SurveyVar(sv)

    df = clps_df
    # Filter by region
    if region_filter is not None:
        df = filter_by_region(df, region_filter)
    weights = df[WEIGHT_KEY]

    # Filter by variable
    df = filter_by_variable(df, [var_to_plot, WEIGHT_KEY])

    # Count frequency
    df = df[var_to_plot].value_counts().rename(unweighted_index_name)

    # Reorder by the original codes
    df = df.reindex(sv.codes)
    # Rename codes to answer categories
    df = df.rename(sv.get_answer)

    # Remove valid skip answers
    if remove_valid_skips:
        df = df.drop(index=VALID_SKIP)

    return df
