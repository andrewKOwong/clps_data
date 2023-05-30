from clps.survey_vars_utils import SurveyVars, load_keyed_survey_vars
import yaml
import clps.constants.survey_vars_keys as SVK
from clps.constants.special_vars_names import VALID_SKIP


CONFIG_FP = 'config.yaml'


def load_config() -> dict:
    """Load the config file."""
    with open(CONFIG_FP) as f:
        return yaml.safe_load(f)


config = load_config()

svs = SurveyVars(config['data']['survey_vars_file'])
raw_svs = load_keyed_survey_vars(config['data']['survey_vars_file'])


def test_has_valid_skips():
    for sv, raw_sv in zip(svs, raw_svs.values()):
        try:
            raw_sv[SVK.ANSWER_CATEGORIES]
        except KeyError:
            continue
        assert (sv.has_valid_skips() ==
                (VALID_SKIP in raw_sv[SVK.ANSWER_CATEGORIES]))
