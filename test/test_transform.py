import pandas as pd
from typing import Literal
from clps.transform import transform_data
from clps.survey_vars_utils import SurveyVars
import yaml
from clps.constants.special_vars_names import (
    WEIGHT_KEY, REGION_KEY, VALID_SKIP)


CONFIG_FP = 'config.yaml'


def load_config() -> dict:
    """Load the config file."""
    with open(CONFIG_FP) as f:
        return yaml.safe_load(f)


config = load_config()

svs = SurveyVars(config['data']['survey_vars_file'])
df = pd.read_csv(config['data']['clps_compressed'])

"""
Pick several survey variables, and test them without filtering or grouping.
Correct frequencies and weighted frequencies are hand copies from the codebook.
"""


# Helper function for testing individual raw survey variables
def raw_var_tester(
        df: pd.DataFrame,
        survey_vars: SurveyVars,
        selected_var,
        freqs,
        wt_freqs,
        valid_skip_number: int | None = None):
    """Template tester function for a single raw variable.

    Survey variable of interest is tested weighted/unweighted, and with/without
    valid skips.

    No filtering or grouping is done.

    Args:
        df: Raw CLPS dataframe with survey variables.
        survey_vars: SurveyVars object.
        selected_var: Name of the survey variable to test.
        freqs: Frequencies from the codebook.
        wt_freqs: Weighted frequencies from the codebook.
        valid_skip_number: Number of line item containing valid skip, i.e.
            index of the valid skip in the codebook + 1. E.g. if valid skip
            is the third line item, then valid_skip_number = 3.
            If the variables has no valid skips, pass None.
    """
    # Convert number back to index
    valid_skip_index = (valid_skip_number - 1
                        if valid_skip_number is not None else None)
    # Update the kwargs
    var_kwargs = {
        'df': df,
        'survey_vars': survey_vars,
        'selected_var': selected_var,
        'region': None,
        'groupby_var': None}

    # With valid skips, if present
    result = transform_data(
        **var_kwargs,
        remove_valid_skips=False,
        weighted=False
    )
    assert list(result[WEIGHT_KEY]) == freqs

    result = transform_data(
        **var_kwargs,
        remove_valid_skips=False,
        weighted=True
    )
    assert list(result[WEIGHT_KEY]) == wt_freqs

    # Remove valid skips
    if valid_skip_index is not None:
        freqs.pop(valid_skip_index)
        wt_freqs.pop(valid_skip_index)
        result = transform_data(
            **var_kwargs,
            remove_valid_skips=True,
            weighted=False
        )
        assert list(result[WEIGHT_KEY]) == freqs

        result = transform_data(
            **var_kwargs,
            remove_valid_skips=True,
            weighted=True
        )
        assert list(result[WEIGHT_KEY]) == wt_freqs


def test_raw_var_DSHP20E():
    raw_var_tester(
        df=df,
        survey_vars=svs,
        selected_var='DSHP20E',
        freqs=[108, 416, 20018, 628],
        wt_freqs=[182_456, 589_265, 28_473_965, 846_299],
        valid_skip_number=3)


def test_raw_var_CSTP10EP():
    raw_var_tester(
        df=df,
        survey_vars=svs,
        selected_var='CSTP10EP',
        freqs=[505, 3296, 15_484, 1885],
        wt_freqs=[663_571, 4_645_598, 22_204_983, 2_577_833],
        valid_skip_number=3)


def test_raw_var_AGEGRP():
    raw_var_tester(
        df=df,
        survey_vars=svs,
        selected_var='AGEGRP',
        freqs=[1635, 2638, 3297, 3541, 4348, 5711],
        wt_freqs=[3_288_730, 5_189_659, 5_025_616,
                  4_714_059, 5_201_210, 6_672_711])


def test_raw_var_PRIP05N():
    raw_var_tester(
        df=df,
        survey_vars=svs,
        selected_var='PRIP05N',
        freqs=[950, 19897, 323],
        wt_freqs=[1_122_624, 28_541_717, 427_645]
    )


"""
Given a survey variable, a region, and a demographic grouping variable,
test if the frequency/weighted frequency is correct.
"""


# Helper function for testing survey var subgroups
def var_subgroup_tester(
        df: pd.DataFrame,
        survey_vars: SurveyVars,
        selected_var: str,
        selected_var_category: str,
        selected_var_code: int,
        region: Literal[
            'Atlantic',
            'Québec',
            'Ontario',
            'Prairies',
            'British Columbia'] | None,
        groupby_var: str,
        subgroup_name: str,
        subgroup_code: int,
        is_valid_skip: bool = False):

    """Template tester function for a survey variable subgroup.

    Given a survey variable, a region, and a demographic grouping variable,
    test if the frequency/weighted frequency is correct.

    Note: Demographic variables never have a valid skip.

    Args:
        df: Raw CLPS dataframe with survey variables.
        survey_vars: SurveyVars object.
        selected_var: Name of the survey variable to test.
        selected_var_category: Category of the survey variable to test.
        selected_var_code: Code of the category of the group to test,
            e.g. as according to the codebook.
            Please check that category name and code actually match.
        region: Region string, rather than the int code, for clarity while
            writing tests.
        groupby_var: Name of the demographic grouping variable.
        subgroup_name: Name of the subgroup of the grouping variable. E.g.
            for AGEGRP, one subgroup is '25 to 34 years old'.
        subgroup_code: Code of the subgroup of the grouping variable, e.g.
            as according to the codebook.
            Please check that subgroup name and code actually match.
        is_valid_skip: Whether the subcategory is a valid skip. If False,
            runs test both with and without valid skip removal.
    """
    REGION_LOOKUP = {
        'Atlantic': 1,
        'Québec': 2,
        'Ontario': 3,
        'Prairies': 4,
        'British Columbia': 5
    }

    correct = df.copy()
    # Filter for region
    if region is not None:
        region = REGION_LOOKUP[region]
        correct = correct.loc[correct[REGION_KEY] == region]
    # Filter for the subgroup
    correct = correct.loc[correct[groupby_var] == subgroup_code]
    # Drop unneeded columns
    correct = correct[[selected_var, groupby_var, WEIGHT_KEY]]

    # Aggregate by selected/groupby_var.
    # The only real difference is the count/sum
    correct_freq = (
        correct
        .groupby([selected_var, groupby_var])[WEIGHT_KEY]
        .count()
        .reset_index()
        .loc[lambda df_: df_[selected_var] == selected_var_code, :]
        .loc[lambda df_: df_[groupby_var] == subgroup_code, :]
        [WEIGHT_KEY]
        .iloc[0]
    )
    correct_wt_freq = (
        correct
        .groupby([selected_var, groupby_var])[WEIGHT_KEY]
        .sum()
        .reset_index()
        .loc[lambda df_: df_[selected_var] == selected_var_code, :]
        .loc[lambda df_: df_[groupby_var] == subgroup_code, :]
        [WEIGHT_KEY]
        .iloc[0]
        .round()
    )

    # Update the kwargs
    var_kwargs = {}
    var_kwargs['df'] = df
    var_kwargs['survey_vars'] = survey_vars
    var_kwargs['selected_var'] = selected_var
    var_kwargs['region'] = region
    var_kwargs['groupby_var'] = groupby_var

    def calculate_freq_helper(result):
        """Impure helper for getting [weighted] frequency from results."""
        # Selected var, etc., reaches into outer scope
        return (
            result
            .loc[lambda df_: df_[selected_var] == selected_var_category, :]
            .loc[lambda df_: df_[groupby_var] == subgroup_name, :]
            [WEIGHT_KEY]
            .iloc[0]
        )

    # No valid skip removal, frequency
    result = transform_data(
        **var_kwargs, remove_valid_skips=False, weighted=False)
    assert calculate_freq_helper(result) == correct_freq
    # No valid skip removal, weighted frequency
    result = transform_data(
        **var_kwargs, remove_valid_skips=False, weighted=True)
    assert calculate_freq_helper(result) == correct_wt_freq

    # As above, but with valid skip removal
    if is_valid_skip is not None:
        result = transform_data(
            **var_kwargs, remove_valid_skips=True, weighted=False)
        assert calculate_freq_helper(result) == correct_freq
        result = transform_data(
            **var_kwargs, remove_valid_skips=True, weighted=True)
        assert calculate_freq_helper(result) == correct_wt_freq


def test_var_subgroups_SERPROPB():
    var_subgroup_tester(
        df=df,
        survey_vars=svs,
        selected_var='SERPROBP',
        selected_var_category='Debt or money owed to you',
        selected_var_code=6,
        region='Atlantic',
        groupby_var='AGEGRP',
        subgroup_name='45 to 54 years old',
        subgroup_code=4,
        is_valid_skip=False
    )
