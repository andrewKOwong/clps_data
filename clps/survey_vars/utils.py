import json
from pathlib import Path
from typing import Literal
from clps.survey_vars import json_keys as SVK
import clps.constants as N
from copy import deepcopy


class _SurveyVar:
    """A class to represent a survey variable for convenient access.

    Handles dealing with PROBCNTP as a special case.
    """

    def __init__(
            self,
            survey_var: dict,
            attempt_int_conversion: bool = True) -> None:
        """
        Args:
            survey_var: A survey variable dictionary, i.e. individual list
                items.
            attempt_int_conversion: Whether to attempt to convert codes to
                integers. If this fails, codes will be left as strings.
        """
        # Make a copy of the original dict
        raw = self._raw = survey_var.copy()
        # Insert the data
        self._name = raw[SVK.VAR_NAME]
        self._length = raw[SVK.LENGTH]
        self._position = raw[SVK.POSITION]
        self._question_name = raw[SVK.QUESTION_NAME]
        self._concept = raw[SVK.CONCEPT]
        self._question_text = raw[SVK.QUESTION_TEXT]
        self._universe = raw[SVK.UNIVERSE]
        self._note = raw[SVK.NOTE]
        self._source = raw[SVK.SOURCE]
        # Skip answer section entirely for survey vars where it doesn't exist.
        try:
            raw[SVK.ANSWER_CATEGORIES]
        except KeyError:
            pass
        else:
            # Handle PROBCNTP as a special case
            if self._name == N.PROBCNTP_KEY:
                self._handle_PROBCNTP_answer_section()
                # PROCNTP has only aggregated frequencies etc,
                # so don't generate those lookups.
                self._generate_lookup_by_code(
                    freq=False, wt_freq=False, percent=False
                )
            else:
                self._handle_answer_section(attempt_int_conversion)
                self._generate_lookup_by_code()

    def __repr__(self) -> str:
        # Use the underlying dict's repr
        return self._raw.__repr__()

    def __str__(self) -> str:
        # Use the underlying dict's str
        return self._raw.__str__()

    def _handle_answer_section(self, attempt_int_conversion: bool) -> None:
        """Handle the answer section of the survey variable.

        Args:
            attempt_int_conversion: Whether to attempt to convert codes to
                integers. If this fails, codes will be left as strings.
        """
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
        """Handles the answer section of the PROBCNTP survey variable.

        Creates several private attributes for the aggregated data. Replaces
        the aggregated '01-16' code with individual codes and corresponding
        answer categories.

        Frequency etc. lookups are not generated for PROBCNTP, as this cannot
        be inferred from codebook information alone.
        """
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
        agg_code_idx = codes.index(N.PROBCNTP_AGGREGATE_CODE)
        # Remove the aggregate code
        agg_code = codes.pop(agg_code_idx)
        # Generate individual codes from '01-16'.
        # This probably could be hard coded instead.
        start, end = tuple([int(c) for c in agg_code.split('-')])
        indiv_codes = list(range(start, end + 1))
        # Insert the individual codes back into the code list.
        indiv_codes.reverse()
        for c in indiv_codes:
            codes.insert(agg_code_idx, c)
        codes = [int(c) for c in codes]

        # Copy out the aggregate answer category, then remove it.
        ans_cats = self._aggregate_ans_cats.copy()
        # Remove the aggregate answer category
        ans_cats.pop(agg_code_idx)
        # Insert the NEW individual answer categories.
        # Originally, was going to append the code to the "Number of ..."
        # string, but that makes the labels kind of repetitive.
        # Instead, just use the code, as the x axis label explains
        # it anyways.
        indiv_ans_cats = [f'{c}' for c in indiv_codes]
        for a in indiv_ans_cats:
            ans_cats.insert(agg_code_idx, a)

        self._ans_cats = ans_cats
        self._codes = codes

        # Raise if user tries to access frequency lookups etc.
        def error_func(self) -> None:
            raise NotImplementedError(
                "PROBCNTP frequency/weighted frequency/percent lookup is not "
                "implemented yet."
            )
        self.lookup_freq = error_func
        self.lookup_wt_freq = error_func
        self.lookup_percent = error_func

    def _generate_lookup_by_code(
            self,
            ans: bool = True,
            freq: bool = True,
            wt_freq: bool = True,
            percent: bool = True) -> str:
        """Generate code lookup dicts for answer categories, etc.

        Args:
            ans: Whether to generate the answer category lookup.
            freq: Whether to generate the frequency lookup.
            wt_freq: Whether to generate the weighted frequency lookup.
            percent: Whether to generate the percent lookup.
        """
        if ans:
            self._ans_lookup = {
                c: a for c, a in zip(self.codes, self.answer_categories)}
        if freq:
            self._freq_lookup = {
                c: a for c, a in zip(self.codes, self.freqs)}
        if wt_freq:
            self._wt_freq_lookup = {
                c: a for c, a in zip(self.codes, self.wt_freqs)}
        if percent:
            self._percent_lookup = {
                c: a for c, a in zip(self.codes, self.percents)}

    def _lookup_by_code(
            self,
            code: int | str,
            type: Literal['answer', 'freq', 'wtfreq', 'percent'],
            suppress_missing: bool = True) -> str | None:
        """Lookup answer category, frequency etc. by code.

        Backend for public lookup methods.

        Args:
            code: The code to lookup. Most codes are ints, occasionally codes
                are strings (e.g. VERDATE).
            type: The type of lookup to perform.
            suppress_missing: If the code doesn't exist, return None.
        """
        # This try/except handles the case where the survey variable doesn't
        # have an answer section.
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
        # This try/except handles the case where the code doesn't exist in the
        # survey_variable
        try:
            return lookup[code]
        except KeyError as e:
            if suppress_missing:
                return None
            else:
                raise KeyError(
                    f"Code {code} not found in answer section") from e

    def lookup_answer(
            self,
            code: int | str,
            suppress_missing: bool = True) -> str | None:
        """Lookup answer category by code.

        Args
            code: The code to lookup. Most codes are ints, occasionally codes
                are strings (e.g. VERDATE).
            suppress_missing: If the code doesn't exist, return None.

        Returns:
            The answer category corresponding to the code.
        """
        return self._lookup_by_code(code, 'answer', suppress_missing)

    def lookup_freq(
            self,
            code: int | str,
            suppress_missing: bool = True) -> int | None:
        """Lookup answer category by code.

        Args
            code: The code to lookup. Most codes are ints, occasionally codes
                are strings (e.g. VERDATE).
            suppress_missing: If the code doesn't exist, return None.

        Returns:
            Frequency corresponding to the code.
        """
        return int(self._lookup_by_code(code, 'freq', suppress_missing))

    def lookup_wt_freq(
            self,
            code: int | str,
            suppress_missing: bool = True) -> int:
        """Lookup answer category by code.

        Args
            code: The code to lookup. Most codes are ints, occasionally codes
                are strings (e.g. VERDATE).
            suppress_missing: If the code doesn't exist, return None.

        Returns:
            Weighted frequency corresponding to the code.
        """
        return int(self._lookup_by_code(code, 'wtfreq', suppress_missing))

    def lookup_percent(
            self,
            code: int | str,
            suppress_missing: bool = True) -> float:
        """Lookup answer category by code.

        Args
            code: The code to lookup. Most codes are ints, occasionally codes
                are strings (e.g. VERDATE).
            suppress_missing: If the code doesn't exist, return None.

        Returns:
            Percent corresponding to the code.
        """
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

    """
    Use properties to make the data read-only. For lists/dicts, return a copy
    so the original list is not mutated by accident.
    """
    @property
    def raw(self) -> dict:
        return deepcopy(self._raw)

    @property
    def name(self) -> str:
        return self._name

    @property
    def var_name(self) -> str:
        return self._name

    @property
    def length(self) -> str:
        return self._length

    @property
    def position(self) -> str:
        return self._position

    @property
    def question_name(self) -> str:
        return self._question_name

    @property
    def concept(self) -> str:
        return self._concept

    @property
    def question_text(self) -> str:
        return self._question_text

    @property
    def universe(self) -> str:
        return self._universe

    @property
    def note(self) -> str:
        return self._note

    @property
    def source(self) -> str:
        return self._source

    @property
    def ans_cats(self) -> list[str] | None:
        try:
            return deepcopy(self._ans_cats)
        except AttributeError:
            return None

    @property
    def answer_categories(self) -> list[str] | None:
        return self.ans_cats

    @property
    def codes(self) -> list[int] | list[str] | None:
        try:
            return deepcopy(self._codes)
        except AttributeError:
            return None

    @property
    def freqs(self) -> list[int] | None:
        try:
            return deepcopy(self._frequency)
        except AttributeError:
            return None

    @property
    def frequencies(self) -> list[int] | None:
        return deepcopy(self._freqs)

    @property
    def wt_freqs(self) -> list[int] | None:
        try:
            return deepcopy(self._weighted_frequency)
        except AttributeError:
            return None

    @property
    def weighted_frequencies(self) -> list[int] | None:
        return self.wt_freqs

    @property
    def percents(self) -> list[float] | None:
        try:
            return deepcopy(self._percent)
        except AttributeError:
            return None

    @property
    def totals(self) -> dict:
        try:
            return deepcopy(self._total)
        except AttributeError:
            return None


class SurveyVars:
    """A class to represent survey variables for convenient access.

    I.e. from survey_vars.json extracted from the CLPS codebook.
    Supports [ ] indexing by variable name. Iteration will iterate over a list
    of the individual _SurveyVar objects.
    """

    def __init__(self, survey_vars_fp: str | Path):
        """
        Args:
            survey_vars_fp: Path to the survey variables JSON file.
        """
        # Save the original file path
        self._fp = survey_vars_fp
        # JSON as a dictionary with var name keys
        self._survey_vars_raw = load_keyed_survey_vars(survey_vars_fp)
        # Keyed survey variables where each survey variable has been
        # initialized as a _SurveyVar object
        self._survey_vars = {
            k: _SurveyVar(v) for k, v in self._survey_vars_raw.items()}

    def __repr__(self):
        return f"SurveyVars('{self._fp}')"

    def __str__(self):
        return f"SurveyVars('{self._fp}') containing {len(self)} variables."

    def __len__(self):
        return len(self._survey_vars)

    def __getitem__(self, key: str) -> _SurveyVar:
        """[] indexer to get a survey variable by its key."""
        return self._survey_vars[key]

    def __iter__(self):
        return iter(self._survey_vars.values())

    def get_var(self, key: str) -> _SurveyVar:
        """Get a survey variable by its name/key."""
        return self._survey_vars[key]

    def get_all_var_names(self) -> list[str]:
        """Get all survey variable names/keys.

        Returns:
            A list of all survey variable names, in order of appearance in the
            survey variables JSON file.
        """
        return list(self._survey_vars.keys())

    def get_region(self):
        """Get the _SurveyVar object for the REGION survey variable."""
        return self._survey_vars[N.REGION_KEY]


def load_survey_vars(fp: str | Path) -> list:
    """Load the survey variables from the JSON file as a list.

    Args:
        fp: Path to the survey variables JSON file.

    Returns:
        A list of survey variables.
    """
    if isinstance(fp, str):
        fp = Path(fp)
    with fp.open() as f:
        return json.load(f)


def load_keyed_survey_vars(fp: str | Path) -> dict:
    """Load the survey variables from the JSON file with var name keys.

    Args:
        fp: Path to the survey variables JSON file.

    Returns:
        A dictionary of survey variables with var name keys.
    """
    if isinstance(fp, str):
        fp = Path(fp)
    with fp.open() as f:
        data = json.load(f)
    return {e[SVK.VAR_NAME]: e for e in data}
