from clps.survey_vars.utils import SurveyVars, load_keyed_survey_vars
import yaml
import clps.constants.survey_vars_keys as SVK
from clps.constants.special_vars_names import VALID_SKIP, NOT_STATED
import clps.constants.special_vars_names as N
import pytest


CONFIG_FP = 'config.yaml'


def load_config() -> dict:
    """Load the config file."""
    with open(CONFIG_FP) as f:
        return yaml.safe_load(f)


config = load_config()

# Load a SurveyVars object as well as a dictionary version of the raw JSON.
# The raw dict will be used as a testing reference.
svs = SurveyVars(config['data']['survey_vars_file'])
raw_svs = load_keyed_survey_vars(config['data']['survey_vars_file'])


# Test if valid skips are correctly identified by _SurveyVar.has_valid_skips()
def test_has_valid_skips() -> None:
    for sv, raw_sv in zip(svs, raw_svs.values()):
        try:
            raw_sv[SVK.ANSWER_CATEGORIES]
        except KeyError:
            continue
        assert (sv.has_valid_skips() ==
                (VALID_SKIP in raw_sv[SVK.ANSWER_CATEGORIES]))


"""
This section tests several picked survey variables to check various aspects of
their correctness.

Testing is not exhaustive for each survey variable, but should try to cover all
the different attribute access points over the set of tests.
"""


def test_PUMFID() -> None:
    # Check that PUMFID has no answer section
    assert svs[N.ID_KEY].answer_categories is None
    assert (svs[N.ID_KEY].concept ==
            'Randomly generated sequence number for'
            ' the public use microdata file')


def test_WTPP() -> None:
    assert svs[N.WEIGHT_KEY].answer_categories is None
    assert (svs[N.WEIGHT_KEY].universe ==
            'All respondents')


def test_AGEGRPP() -> None:
    sv = svs[N.AGE_KEY]
    assert sv.note == 'Based on AGE'
    assert sv.ans_cats[2] == '35 to 44 years old'
    assert sv.codes[4] == 5
    assert sv.lookup_answer(1) == 'Less than 25 years old'
    assert sv.lookup_wt_freq(5) == 5_201_210
    assert len(sv.codes) == 6


def test_VERDATE() -> None:
    sv = svs[N.VERDATE_KEY]
    assert sv.universe == 'All respondents'
    assert sv.ans_cats == ['']
    assert len(sv.codes) == 1
    assert sv.lookup_answer('28/02/2022') == ''
    assert sv.lookup_answer(2) is None
    # This fails if no exception is raise, as there is no code 1
    with pytest.raises(KeyError):
        sv.lookup_answer(2, suppress_missing=False)


def test_PROBCNTP() -> None:
    sv = svs[N.PROBCNTP_KEY]
    assert sv.question_name == ''
    assert sv.question_text == ''
    assert sv.source == ''
    assert len(sv.codes) == 18
    # PROCNTP has its freqs disabled because it's a special case
    # where the codebook aggregates values 1-16. The original value
    # is stored in private attribute ._aggregate_freqs, but public
    # end points are not implemented yet.
    with pytest.raises(NotImplementedError):
        sv.lookup_freq(0)
    with pytest.raises(NotImplementedError):
        sv.lookup_wt_freq(6)
    with pytest.raises(NotImplementedError):
        sv.lookup_percent(3)
    assert sv.lookup_answer(0) == 'No serious problems reported'
    assert sv.lookup_answer(99) == NOT_STATED


def test_SERPROBP() -> None:
    sv = svs[N.SERPROBP_KEY]
    assert sv.universe == 'At least one of PRI_Q10A to PRI_Q10S = 1'
    assert len(sv.ans_cats) == 21
    assert sv.lookup_answer(96) == VALID_SKIP
    assert sv.lookup_answer(99) == NOT_STATED
    assert sv.lookup_answer(16) == 'Civil court or legal action'
    assert sv.lookup_wt_freq(13) == 95_230
    assert sv.lookup_percent(10) == 0.6


def test_PRIP10G() -> None:
    sv = svs['PRIP10G']
    assert sv.universe == 'PRI_Q05G = 1'
    assert sv.question_text == (
        "Were the following disputes or problems"
        " serious and not easy to fix? - "
        "Getting social or housing assistance, "
        "receiving Old Age Security, Guaranteed Income Supplement or other "
        "government assistance payments, or problems with the amount received")
    assert len(sv.ans_cats) == 4
    assert sv.lookup_answer(1) == 'Yes'
    assert sv.lookup_freq(2) == 353
    assert sv.lookup_wt_freq(6) == 28_837_397
    assert sv.lookup_percent(9) == 1.5


def test_ASTP10G() -> None:
    sv = svs['ASTP10G']
    assert sv.length == '1.0'
    assert sv.position == '150'
    assert sv.lookup_answer(2) == 'No'
    assert sv.lookup_freq(6) == 15_484
    assert sv.totals[SVK.FREQUENCY] == '21170'


def test_LGAP40P() -> None:
    sv = svs['LGAP40P']
    assert sv.lookup_answer(7) == 'Don’t know'
    assert sv.lookup_wt_freq(2) == 4_188_071


def test_CSTP10NP() -> None:
    sv = svs['CSTP10NP']
    assert sv.lookup_answer(1) == 'Yes'
    assert sv.lookup_freq(1) == 407
    assert sv.lookup_wt_freq(1) == 590_844
    assert sv.lookup_percent(1) == 2.0
