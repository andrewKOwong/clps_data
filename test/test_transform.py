import pandas as pd
from clps.transform import transform_data
from clps.survey_vars_utils import SurveyVars
import yaml
from clps.constants.special_vars_names import WEIGHT_KEY


CONFIG_FP = 'config.yaml'


def load_config() -> dict:
    """Load the config file."""
    with open(CONFIG_FP) as f:
        return yaml.safe_load(f)


config = load_config()

svs = SurveyVars(config['data']['survey_vars_file'])
df = pd.read_csv(config['data']['clps_compressed'])


def test_var_raw():
    """Pick several survey variables, without filtering/grouping.

    For these survey variables, test weighted/unweighted, and with/without
    valid skips.
    """
    # Generic kwargs for these these tests
    kwargs = {
        'df': df,
        'survey_vars': svs,
        'region': None,
        'groupby_var': None,
    }

    def run_test_var_raw_helper(
            kwargs,
            selected_var,
            freqs,
            wt_freqs,
            valid_skip_number: int | None = None):
        """Helper function for test_var_raw.

        Args:
            kwargs: Generic keyword args package.
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
        var_kwargs = kwargs.copy()
        var_kwargs['selected_var'] = selected_var

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
    """
    Testing DSHP20E
    """
    run_test_var_raw_helper(
        kwargs=kwargs,
        selected_var='DSHP20E',
        freqs=[108, 416, 20018, 628],
        wt_freqs=[182_456, 589_265, 28_473_965, 846_299],
        valid_skip_number=3)
    """
    Testing CSTP10EP
    """
    run_test_var_raw_helper(
        kwargs=kwargs,
        selected_var='CSTP10EP',
        freqs=[505, 3296, 15_484, 1885],
        wt_freqs=[663_571, 4_645_598, 22_204_983, 2_577_833],
        valid_skip_number=3)
    """
    Testing AGEGRP
    """
    run_test_var_raw_helper(
        kwargs=kwargs,
        selected_var='AGEGRP',
        freqs=[1635, 2638, 3297, 3541, 4348, 5711],
        wt_freqs=[3_288_730, 5_189_659, 5_025_616,
                  4_714_059, 5_201_210, 6_672_711]
    )
    """
    Testing PRIP05N
    """
    run_test_var_raw_helper(
        kwargs=kwargs,
        selected_var='PRIP05N',
        freqs=[950, 19897, 323],
        wt_freqs=[1_122_624, 28_541_717, 427_645]
    )
