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
            self._ans_cats = raw[SVK.ANSWER_CATEGORIES]
            self._codes = raw[SVK.CODE]
            if attempt_int_conversion:
                try:
                    self._codes = [int(c) for c in self._codes]
                except ValueError:
                    pass
            self._frequency = raw[SVK.FREQUENCY]
            self._weighted_frequency = raw[SVK.WEIGHTED_FREQUENCY]
            self._percent = raw[SVK.PERCENT]
            self._total = raw[SVK.TOTAL]
            self._generate_lookup_by_code()

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

        self._expand_PROBCNTP_codes()

    def __getitem__(self, key: str) -> _SurveyVar:
        """[] indexer to get a survey variable by its key."""
        return self._survey_vars[key]

    def _expand_PROBCNTP_codes(self):
        """Expand the aggregated PROBCNTP code.

        PROBCNTP contains an aggregated code '01 - 16'. This code is drawn from
        survey variables PRIP10A to PRIP10S. This method draws from the
        individual survey variables in order to expand the aggregated code into
        int-able codes.
        Note: this can only be called after the main _survey_vars dict is
        initialized.
        """
        # First move old attributes to aggregated attributes
        probcntp = self.get_var(N.PROBCNTP)
        probcntp._aggregate_codes = probcntp.codes.copy()
        probcntp._aggregate_ans_cats = probcntp.ans_cats.copy()
        probcntp._aggregate_freqs = probcntp.freqs.copy()
        probcntp._aggregate_wt_freqs = probcntp.wt_freqs.copy()
        probcntp._aggregate_percents = probcntp.percents.copy()
        probcntp._aggregate_totals = probcntp.totals.copy()
        # Position of the 01-16 str code
        sum_idx = probcntp._aggregate_codes.index(self.PROBCNTP_AGGREGATE_CODE)
        # This might as well be hard coded, but it's the 1 and 16
        start, end = tuple([
            int(c) for c in probcntp._aggregate_codes[sum_idx].split(' - ')])
        # Get ans_cats, codes, freqs, wt_freqs, percents, totals to insert
        # New answer categories are concepts from the PRIP components.
        # Reverse for later insertion.
        prip_ans_cats = [
            self._survey_vars[k].concept for k in self.PRIP10_KEYS][::-1]
        print(prip_ans_cats)
        print(len(prip_ans_cats))
        prip_codes = list(range(start, len(prip_ans_cats) + 1))[::-1]
        prip_freqs = [
            self.get_var(k).lookup_freq(self.PRIP10_YES_CODE)
            for k in self.PRIP10_KEYS][::-1]
        prip_wt_freqs = [
            self.get_var(k).lookup_wt_freq(self.PRIP10_YES_CODE)
            for k in self.PRIP10_KEYS][::-1]
        prip_percents = [
            self.get_var(k).lookup_percent(self.PRIP10_YES_CODE)
            for k in self.PRIP10_KEYS][::-1]

        fields = [probcntp._ans_cats, probcntp._codes, probcntp._frequency,
                  probcntp._weighted_frequency, probcntp._percent]
        prips = [prip_ans_cats, prip_codes, prip_freqs, prip_wt_freqs,
                 prip_percents]

        for f, prip in zip(fields, prips):
            f.pop(sum_idx)
            for e in prip:
                f.insert(sum_idx, e)
        probcntp._codes = [int(c) for c in probcntp._codes]
        probcntp._generate_lookup_by_code()

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
