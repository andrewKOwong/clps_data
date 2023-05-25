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
    PROBCNTP_AGGREGATE_CODE = N.PROBCNTP_AGGREGATE_CODE

    def __init__(self, survey_var: dict, attempt_int_conversion: bool = True):
        """
        Args:
            survey_var: A survey variable dictionary, i.e. individual list
                items.
            attempt_int_conversion: Whether to attempt to convert codes to
                integers. If this fails, codes will be left as strings.
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
            if self._name == N.PROBCNTP:
                self._handle_PROBCNTP_answer_section()
                # Don't generate freq etc. lookups
                self._generate_ans_lookup_by_code()
            else:
                self._handle_answer_section(attempt_int_conversion)
                self._generate_lookup_by_code()

    def _handle_answer_section(self, attempt_int_conversion: bool) -> None:
        self._ans_cats = self._raw[SVK.ANSWER_CATEGORIES]
        self._codes = self._raw[SVK.CODE]
        if attempt_int_conversion:
            try:
                self._codes = [int(c) for c in self._codes]
            except ValueError:
                pass
        self._frequency = self._raw[SVK.FREQUENCY]
        self._weighted_frequency = self._raw[SVK.WEIGHTED_FREQUENCY]
        self._percent = self._raw[SVK.PERCENT]
        self._total = self._raw[SVK.TOTAL]

    def _handle_PROBCNTP_answer_section(self) -> None:
        raw = self._raw
        self._aggregate_ans_cats = raw[SVK.ANSWER_CATEGORIES]
        self._aggregate_codes = raw[SVK.CODE]
        self._aggregate_freqs = raw[SVK.FREQUENCY]
        self._aggregate_wt_freqs = raw[SVK.WEIGHTED_FREQUENCY]
        self._aggregate_percents = raw[SVK.PERCENT]
        self._aggregate_totals = raw[SVK.TOTAL]
        # Copy out the aggregate codes
        codes = self._aggregate_codes.copy()
        # Position of the 01-16 str code
        sum_idx = codes.index(self.PROBCNTP_AGGREGATE_CODE)
        # Remove the aggregate code
        agg_code = codes.pop(sum_idx)
        # This might as well be hard coded, but it's the 1 and 16
        start, end = tuple([int(c) for c in agg_code.split('-')])
        indiv_codes = list(range(start, end + 1))
        # Insert the individual codes
        indiv_codes.reverse()
        for c in indiv_codes:
            codes.insert(sum_idx, c)
        codes = [int(c) for c in codes]

        # Copy out the aggregate answer categories
        ans_cats = self._aggregate_ans_cats.copy()
        # Remove the aggregate answer category
        ans_cats.pop(sum_idx)
        # Insert the NEW individual answer categories.
        # Originally, was going to append the code to the "Number of ..."
        # string, but that makes the labels kind of repetitive.
        # Instead, just use the code, as the x axis label explains
        # it anyways.
        indiv_ans_cats = [f'{c}' for c in indiv_codes]
        for a in indiv_ans_cats:
            ans_cats.insert(sum_idx, a)

        self._ans_cats = ans_cats
        self._codes = codes

        def error_func(self):
            raise NotImplementedError(
                "PROBCNTP frequency/weighted frequency/percent lookup is not "
                "implemented yet."
            )
        self.lookup_freq = self.lookup_wt_freq = error_func
        self.lookup_percent = error_func

    def _generate_lookup_by_code(self) -> str:
        """"""
        self._ans_lookup = {
            c: a for c, a in zip(self.codes, self.answer_categories)}
        self._freq_lookup = {
            c: a for c, a in zip(self.codes, self.freqs)}
        self._wt_freq_lookup = {
            c: a for c, a in zip(self.codes, self.wt_freqs)}
        self._percent_lookup = {
            c: a for c, a in zip(self.codes, self.percents)}

    def _generate_ans_lookup_by_code(self) -> dict:
        self._ans_lookup = {
            c: a for c, a in zip(self.codes, self.answer_categories)}

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
            self, code: int | str, suppress_missing: bool = True) -> int:
        return int(self._lookup_by_code(code, 'freq', suppress_missing))

    def lookup_wt_freq(
            self, code: int | str, suppress_missing: bool = True) -> int:
        return int(self._lookup_by_code(code, 'wtfreq', suppress_missing))

    def lookup_percent(
            self, code: int | str, suppress_missing: bool = True) -> float:
        return float(self._lookup_by_code(code, 'percent', suppress_missing))

    def has_valid_skips(self) -> bool:
        """True if the survey variable has a 'Valid skip' category.

        False if it does not have a 'Valid skip' category, or has no
        answer categories at all.
        """
        # Check if answer categories exists
        try:
            self.ans_cats
        except AttributeError:
            return False
        # Check for valid skips
        return N.VALID_SKIP in self.ans_cats

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
    PROBCNTP_AGGREGATE_CODE = N.PROBCNTP_AGGREGATE_CODE
    PRIP10_YES_CODE = N.PRIP10_YES_CODE
    PRIP10_KEYS = N.PROBCNTP_COMPONENTS

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
