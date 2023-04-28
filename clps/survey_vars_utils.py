import json
from pathlib import Path
from clps.constants import survey_vars_keys as SVK


class SurveyVar:
    """A class to represent a survey variable for convenient access."""
    # TODO deal with verdate and probcntp issue

    def _generate_answer_lookup(self) -> dict:
        """Generate a lookup table for the codes of each variable."""
        return {c: a for c, a in zip(self.codes, self.ans_cats)}

    def __init__(self, survey_var: dict):
        """
        Args:
            survey_var: A survey variable dictionary, i.e. individual list
                items.
        """
        raw = self.raw = survey_var.copy()
        self.codes = [int(c) for c in raw[SVK.CODE]]
        self.ans_cats = raw[SVK.ANSWER_CATEGORIES]
        self._code_lookup = self._generate_answer_lookup()

    def get_answer(self, code: int) -> str:
        """Get a corresponding answer for an answer code."""
        return self._code_lookup[code]


def load_survey_vars(fp: str | Path) -> list:
    """Load the survey variables from the JSON file as a list."""
    if isinstance(fp, str):
        fp = Path(fp)
    with fp.open() as f:
        return json.load(f)


def load_keyed_survey_vars(fp: str | Path) -> dict:
    """Load the survey variables from the JSON file with var name keys."""
    if isinstance(fp, str):
        fp = Path(fp)
    with fp.open() as f:
        data = json.load(f)
    return {e[SVK.VAR_NAME]: e for e in data}


def extract_survey_var(survey_vars: dict, key: str) -> dict:
    """Extract the survey variable from the survey vars dictionary."""
    return survey_vars[key]
