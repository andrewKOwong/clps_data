import pandas as pd
from clps.constants.special_vars_names import (
    REGION_KEY, VALID_SKIP, WEIGHT_KEY)
from clps.survey_vars_utils import SurveyVars


def filter_by_region(df: pd.DataFrame, region: int | None) -> pd.DataFrame:
    """Filter a dataframe by a region code.
    Args:
        df: Dataframe to filter. Region column must be ints.
        region: Region code to filter by. If `None`, no filtering is done.
    Returns:
        Filtered dataframe.
    """
    if region is not None:
        df = df[df[REGION_KEY] == region].copy()
    return df


def filter_by_selected_and_groupby(
        df: pd.DataFrame,
        selected_var: str,
        groupby_var: str | None) -> pd.DataFrame:
    """Filter for the selected variable of interest, the groupby variable, and
    the respondent weights.
    Args:
        df: Dataframe with survey variables.
        selected_var: Name of the survey variable to filter for.
        groupby_var: Name of the groupby variable to filter for.
    """
    if groupby_var is None:
        df = df[[selected_var, WEIGHT_KEY]]
    else:
        df = df[[selected_var, groupby_var, WEIGHT_KEY]]
    return df


def create_ordered_dtype(s: pd.Series) -> pd.CategoricalDtype:
    """From an integer-containing column, create an ordered categorical dtype.
    Args:
        s: Series corresponding to a survey variable, with integer codes.
    Returns:
        Ordered categorical dtype, with categories in ascending integer order.
        """
    return pd.CategoricalDtype(
        categories=s.sort_values().unique(),
        ordered=True)


def order_and_convert_code(
        s: pd.Series,
        survey_vars: SurveyVars) -> pd.Series:
    """Converts a series of codes to text labels, as ordered categorical.
    Used as a helper func for `convert_to_categorical`.
    Args:
        s: Series corresponding to a survey variable, with integer codes.
        survey_vars: SurveyVars object, with survey variable metadata.
    Returns:
        Series with text labels as an ordered categorical. Order is determined
        by the order of the integers, which corresponds to the order found
        in the survey variable metadata.
    """
    # Change ints to ordered categorical to preserve order,
    # then convert to text labels.
    # Mapping automatically converts categorical info.
    return (s
            .astype(create_ordered_dtype(s))
            .cat.rename_categories(
                survey_vars[s.name].lookup_answer))


def convert_to_categorical(
        df: pd.DataFrame,
        svs: SurveyVars,
        selected_var: str,
        groupby_var: str | None):
    """Converted survey variable columns to ordered categorical dtype.
    Args:
        df: Dataframe with survey variable columns. These columns are still in
            integer code form.
        svs: SurveyVars object, with survey variable metadata.
        selected_var: Name of the survey variable column to convert.
        groupby_var: Name of the groupby column to convert, if any.
    Returns:
        Dataframe with survey variable columns converted to ordered categorical
        dtype, as text labels. Order is determined by the integer order, which
        corresponds to the order found in the survey variable metadata.
    """
    df = df.assign(**{
        selected_var: lambda d: (
            order_and_convert_code(d[selected_var], svs))})
    if groupby_var is not None:
        df = df.assign(**{
            groupby_var: lambda d: (
                order_and_convert_code(d[groupby_var], svs))})
    return df


def filter_valid_skips(
        df: pd.DataFrame,
        selected_var: str,
        remove_valid_skips: bool) -> pd.DataFrame:
    """Filter out valid skips from the data.
    If remove_valid_skips is `False` or `None`, this filter does nothing.
    Args:
        df: Dataframe with survey variable columns, converted to str ordered
        categorical dtype.
        selected_var: Name of the survey variable column of interest.
        remove_valid_skips: Whether to remove valid skips from the data.
    Returns:
    """
    if remove_valid_skips:
        df = df.query(f"{selected_var} != '{VALID_SKIP}'")
        df = df.assign(**{
            selected_var:
                lambda d: d[selected_var].cat.remove_unused_categories()
        })
    return df


def groupby_and_aggregate(
        df: pd.DataFrame,
        selected_var: str,
        groupby_var: str | None,
        weighted: bool,
        ) -> pd.DataFrame:
    """Groupby and aggregate the dataframe."""
    # Assemble grouping variables
    groupby_list = [selected_var]
    if groupby_var is not None:
        groupby_list.append(groupby_var)
    # Groupby and aggregate
    # Count the weight column to get the number of actual respondents
    # otherwise sum up the weights.
    grpby = df.groupby(groupby_list)[[WEIGHT_KEY]]  # groupby object
    if weighted:
        out = grpby.sum()
    else:
        out = grpby.count()
    # Note, streamlit appears to have issue with categorical indexes (possibly)
    # after groupbys, displaying a warning that "The value is not part of the
    # allowed options" along with a yellow exclamtion mark.
    # Resetting the index to get a clean dataframe here, then worry about
    # styling during display.
    return (out
            .round()
            .astype(int)
            .reset_index()
            )


def transform_data(
        df: pd.DataFrame,
        survey_vars: SurveyVars,
        region: int,
        selected_var: str,
        groupby_var: str | None,
        remove_valid_skips: bool | None,
        weighted: bool) -> pd.DataFrame:
    # BEGIN: DATA TRANSFORMATIONS
    # Filter region rows
    df = filter_by_region(df, region)
    # Filter survey var columns
    df = filter_by_selected_and_groupby(df, selected_var, groupby_var)

    df = convert_to_categorical(df, survey_vars, selected_var, groupby_var)

    df = filter_valid_skips(df, selected_var, remove_valid_skips)
    df = groupby_and_aggregate(df, selected_var, groupby_var, weighted)
    # END: DATA TRANSFORMATIONS
    return df
