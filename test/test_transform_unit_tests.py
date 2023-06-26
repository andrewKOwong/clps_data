import pandas as pd
import pytest
from clps.constants import VALID_SKIP, YES, NO, NOT_STATED
from clps.constants import VALID_SKIP_CODES
from clps.transform import _handle_valid_skips


SELECTED_VAR = 'selected_var'
GROUPBY_VAR = 'groupby_var'
WEIGHT = 'weight'

@pytest.fixture
def _handle_valid_skips_sample_data() -> pd.DataFrame:
    data = {
        SELECTED_VAR: pd.Categorical(
            [YES, NO, NOT_STATED, VALID_SKIP], ordered=True),
        GROUPBY_VAR: pd.Categorical(
            ['a', 'a', 'c', 'd'], ordered=True),
        WEIGHT: [1, 2, 3, 4]
    }
    return pd.DataFrame(data)


def test_handle_valid_skips_recode(_handle_valid_skips_sample_data):
    data = _handle_valid_skips_sample_data
    result = (_handle_valid_skips(
        data, SELECTED_VAR, VALID_SKIP_CODES.RECODE)
        [SELECTED_VAR]
        .tolist()
    )
    assert result == [YES, NO, NOT_STATED, NO]


def test_handle_valid_skips_remove(_handle_valid_skips_sample_data):
    data = _handle_valid_skips_sample_data.copy()
    result = (_handle_valid_skips(
        data, SELECTED_VAR, VALID_SKIP_CODES.REMOVE)
        [SELECTED_VAR]
        .tolist()
    )
    assert result == [YES, NO, NOT_STATED]


def test_handle_valid_skips_leave(_handle_valid_skips_sample_data):
    data = _handle_valid_skips_sample_data
    result = (_handle_valid_skips(
        data, SELECTED_VAR, VALID_SKIP_CODES.LEAVE)
        [SELECTED_VAR]
        .tolist()
    )
    assert result == [YES, NO, NOT_STATED, VALID_SKIP]


def test_handle_valid_skips_none(_handle_valid_skips_sample_data):
    data = _handle_valid_skips_sample_data
    data = data.query(f"{SELECTED_VAR} != '{VALID_SKIP}'")
    result = (_handle_valid_skips(
        data, SELECTED_VAR, None)
        [SELECTED_VAR]
        .tolist()
    )
    assert result == [YES, NO, NOT_STATED]
