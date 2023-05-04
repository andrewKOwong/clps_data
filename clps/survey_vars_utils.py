import json
from pathlib import Path
from typing import Literal
from clps.constants import survey_vars_keys as SVK
from clps.constants import special_vars_names as N


class _SurveyVar:
    """A class to represent a survey variable for convenient access.

    Handles dealing with special cases like PROBCNTP and VERDATE.

    Extensible to add more getters.
    """
    PROBCNTP_KEY = N.PROBCNTP
    VERDATE_KEY = N.VERDATE

    def __init__(self, survey_var: dict):
        """
        Args:
            survey_var: A survey variable dictionary, i.e. individual list
                items.
        """
        # Original dict
        raw = self._raw = survey_var.copy()
        # Data
        self._name = raw[SVK.VAR_NAME]
        self._length = raw[SVK.LENGTH]
        self._position = raw[SVK.POSITION]
        self._question_name = raw[SVK.QUESTION_NAME]
        self._concept = raw[SVK.CONCEPT]
        self._question_text = raw[SVK.QUESTION_TEXT]
        self._universe = raw[SVK.UNIVERSE]
        self._note = raw[SVK.NOTE]
        self._source = raw[SVK.SOURCE]
        # Skip answer section entirely for vars where it doesn't exist.
        try:
            raw[SVK.ANSWER_CATEGORIES]
        except KeyError:
            pass
        else:
            self._ans_cats = raw[SVK.ANSWER_CATEGORIES]
            match self._name:
                # VERDATE has a string date code
                case self.VERDATE_KEY:
                    self._codes = raw[SVK.CODE]
                case self.PROBCNTP_KEY:
                    # TODO - PROBCNTP has a special format
                    self._codes = raw[SVK.CODE]
                case _:
                    self._codes = [int(c) for c in raw[SVK.CODE]]
            self._frequency = raw[SVK.FREQUENCY]
            self._weighted_frequency = raw[SVK.WEIGHTED_FREQUENCY]
            self._percent = raw[SVK.PERCENT]
            self._total = raw[SVK.TOTAL]
            self._ans_lookup = self._generate_lookup_by_code('answer')
            self._freq_lookup = self._generate_lookup_by_code('freq')
            self._wt_freq_lookup = self._generate_lookup_by_code('wtfreq')
            self._percent_lookup = self._generate_lookup_by_code('percent')

    def _generate_lookup_by_code(
            self,
            type: Literal['answer', 'freq', 'wtfreq', 'percent']) -> str:
        """"""
        match type:
            case 'answer':
                other = self.answer_categories
            case 'freq':
                other = self.freqs
            case 'wtfreq':
                other = self.wt_freqs
            case 'percent':
                other = self.percents
            case _:
                raise ValueError(f'Invalid type: {type}')
        return {c: a for c, a in zip(self.codes, other)}

    def _lookup_by_code(
            self,
            code: int | str,
            type: Literal['answer', 'freq', 'wtfreq', 'percent'],
            suppress_missing: bool = True) -> str:
        """"""
        try:
            match type:
                case 'answer':
                    lookup = self._ans_lookup
                case 'freq':
                    lookup = self._freq_lookup
                case 'wtfreq':
                    lookup = self._wt_freq_lookup
                case 'percent':
                    lookup = self._percent_lookup
                case _:
                    raise ValueError(f'Invalid type: {type}')
        except AttributeError as e:
            if suppress_missing:
                return None
            else:
                raise AttributeError(
                    "This variable doesn't have an answer section") from e
        return lookup[code]

    def lookup_answer(
            self, code: int | str, suppress_missing: bool = True) -> str:
        return self._lookup_by_code(code, 'answer', suppress_missing)

    def lookup_freq(
            self, code: int | str, suppress_missing: bool = True) -> str:
        return self._lookup_by_code(code, 'freq', suppress_missing)

    def lookup_wt_freq(
            self, code: int | str, suppress_missing: bool = True) -> str:
        return self._lookup_by_code(code, 'wtfreq', suppress_missing)

    def lookup_percent(
            self, code: int | str, suppress_missing: bool = True) -> str:
        return self._lookup_by_code(code, 'percent', suppress_missing)

    # Read only data
    @property
    def raw(self):
        return self._raw

    @property
    def name(self):
        return self._name

    @property
    def var_name(self):
        return self._name

    @property
    def length(self):
        return self._length

    @property
    def position(self):
        return self._position

    @property
    def question_name(self):
        return self._question_name

    @property
    def concept(self):
        return self._concept

    @property
    def question_text(self):
        return self._question_text

    @property
    def universe(self):
        return self._universe

    @property
    def note(self):
        return self._note

    @property
    def source(self):
        return self._source

    @property
    def ans_cats(self):
        return self._ans_cats

    @property
    def answer_categories(self):
        return self._ans_cats

    @property
    def codes(self):
        return self._codes

    @property
    def frequencies(self):
        return self._frequency

    @property
    def freqs(self):
        return self._frequency

    @property
    def wt_freqs(self):
        return self._weighted_frequency

    @property
    def weighted_frequencies(self):
        return self._weighted_frequency

    @property
    def percents(self):
        return self._percent

    @property
    def totals(self):
        return self._total


class SurveyVars:
    """A class to represent survey variables for convenient access.

    I.e. from survey_vars.json extracted from the CLPS codebook.
    """
    REGION_KEY = N.REGION

    def __init__(self, survey_vars_fp: str | Path):
        """
        Args:
            survey_vars_fp: Path to the survey variables JSON file.
        """
        # JSON as a dictionary with var name keys
        self._survey_vars_raw = load_keyed_survey_vars(survey_vars_fp)
        # Keyed survey variables where each survey variable has been
        # initialized as a _SurveyVar object
        self._survey_vars = {
            k: _SurveyVar(v) for k, v in self._survey_vars_raw.items()}

    def __getitem__(self, key: str) -> _SurveyVar:
        """[] indexer to get a survey variable by its key."""
        return self._survey_vars[key]

    def get_var(self, key: str) -> _SurveyVar:
        """Get a survey variable by its key."""
        return self._survey_vars[key]

    def get_region(self):
        """Get a region by its key."""
        return self._survey_vars[self.REGION_KEY]


class SurveyVar:
    """A class to represent a survey variable for convenient access.
    """
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
