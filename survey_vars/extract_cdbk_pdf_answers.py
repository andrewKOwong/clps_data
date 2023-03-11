import argparse
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from enum import Enum
import re


class Field(Enum):
    """Data fields for questions.

    Field names can be used as dict keys or col names.
    Field values are used to extract data out of the original data.
    """
    variable_name = 'Variable Name:'
    length = 'Length:'
    position = 'Position:'
    question_name = 'Question:'
    concept = 'Concept:'
    question_text = 'Question Text:'
    universe = 'Universe:'
    note = 'Note:'
    source = 'Source:'
    answer_categories = 'Answer Categories'
    code = 'Code'
    frequency = 'Frequency'
    weighted_frequency = 'Weighted Frequency'
    percent = '%'


START_PAGE = 9  # First data page
END_PAGE = 126  # Last data page (inclusive)


# Shim this in between steps of the pipeline during debugging
# to write out an html file for inspection.
def debug_shim(soup: BeautifulSoup, out: str = 'debug.html') -> None:
    with open(out, 'w') as f:
        f.write(soup.prettify())


# Use this to save the lists of data during extraction for debugging.
def debug_listed_data(data: list, out: str = 'debug.txt') -> None:
    with open(out, 'w') as f:
        for e in data:
            f.write(str(e))
            f.write('\n')


# Parse args
parser = argparse.ArgumentParser()
parser.add_argument(
    'cdbk_html',
    help="pdf2txt.py codebook.pdf -o codebook.html --output_type html"
)
args = parser.parse_args()

# Open and extract html
p = Path(args.cdbk_html)
with p.open() as f:
    soup = BeautifulSoup(f, 'html.parser')
soup = soup.body.extract()

# Regenerating just the data pages
# by finding all siblings of the start div,
# and iterating through and appending until we get the div that
# is right after the ending data page,
# then reconstituting the strings into another soup object.
# start_div whose child is an anchor for the start of page 9
start_div = soup.select(f'a[name="{START_PAGE}"]')[0].parent
html_doc = str(start_div)
for tag in start_div.next_siblings:
    if (isinstance(tag, Tag)
            and tag.a is not None
            and tag.a['name'] == str(END_PAGE + 1)):
        break
    else:
        html_doc += str(tag)
soup = BeautifulSoup(html_doc, 'html.parser')


# Filter out all horizontal lines that aren't dividers for the variables.
# Helper filter func.
def is_non_divider_hline(tag: Tag) -> bool:
    """Filter function for non-divider hline spans.

    Dividers are horizontal lines drawn between each data variable.
    Also checks if the span is not a text containing span.

    Args:
        tag: BeautifulSoup html element.

    Returns:
        True if the span element is not a divider.
    """
    DIVIDER_LEFT_MATCH = 'left:36px'
    DIVIDER_HEIGHT_MATCH = 'height:0px'
    FF_MATCH = 'font-family'
    # Consider only span tags
    if tag.name != 'span':
        return False
    # Style attribute of the span tag
    style = tag['style']
    # Text fields contain a font family style, so use to exclude
    if FF_MATCH in style:
        return False
    # Exclude dividers
    elif DIVIDER_LEFT_MATCH in style and DIVIDER_HEIGHT_MATCH in style:
        return False
    else:
        return True


# Run loop to extract all the non-hlines.
for tag in [e for e in soup.children]:
    if isinstance(tag, Tag) and is_non_divider_hline(tag):
        tag.extract()

# Filter out header and footers
for tag in soup.children:
    if (isinstance(tag, Tag)
            and tag.span is not None
            and ("CLPS 2021 - Data Dictionary" in tag.span.text
                 or "Totals may not add up due to rounding" in tag.span.text
                 or re.search(r"Page.*\-", tag.span.text) is not None)):
        tag.extract()

# Remove page divs
for tag in soup.children:
    if (isinstance(tag, Tag) and tag.a is not None):
        tag.extract()


# For the remaining elements, pull out text and left/top info
# and place into a list of Element dataclass objects.
@dataclass
class Element:
    TEXT_TYPE = 'text'
    DIVIDER_TYPE = 'divider'
    elem_type: str
    left: int  # Left position of the original html element
    top: int  # Top position of the original html element
    text: str = ''

    def __post_init__(self):
        # Left and top are strs to be converted
        self.left = int(self.left)
        self.top = int(self.top)


# Create Element objects with loop.
elements = []
for tag in soup.children:
    # Check tags to see if they have attributes,
    # and if they have left and top styles.
    if isinstance(tag, Tag):
        try:
            style = tag['style']
        except AttributeError as e:
            raise AttributeError(
                f"Tag did not have a style attribute."
                f"\n\nTag contents:\n\n"
                f"{str(tag)}"
                ) from e
        # Left and top specify the corner of the box for the element.
        # Get 1 or more digits between left/top: and px;
        left = re.search(r"(?<=left:)\d+?(?=px;)", style).group(0)
        top = re.search(r"(?<=top:)\d+?(?=px;)", style).group(0)
        if left is None or top is None:
            raise ValueError(
                f"Did not find a left/top value."
                f"\n\nTag contents:\n"
                f"{str(tag)}"
                f"\n\nStyle attribute contents:\n"
                f"{str(style)}"
            )
        # Element type distinguishes
        # top level divs that have text fields
        # and top level spans that are dividers
        match tag.name:
            case 'div':
                type_val = Element.TEXT_TYPE
            case 'span':
                type_val = Element.DIVIDER_TYPE
            case _:
                raise ValueError("Unexpected non div/span element.")
        elements.append(Element(type_val, left, top, tag.text))


# Sorted elements will be in top to bottom order,
# then left to right order for ties.
elements = sorted(elements, key=lambda e: int(e.left))
elements = sorted(elements, key=lambda e: int(e.top))

# Remove leading/trailing whitespace from text fields
for e in elements:
    e.text = e.text.strip()

debug_listed_data(elements, 'debug_elements.txt')


# Extract the data over several steps.
# Step 1: Group the elements into units corresponding
# to each question. These are separated by divider elements.
def group_elements(elements: list[Element]) -> list:
    """Group elements into units corresponding to question.

    Args:
        elements: a list of Elements.
    Returns:
        A list of lists of Elements, with each sublist corresponding
        to a questionnaire question, as separated by divider Elements.
    """
    units = []
    current_unit = []
    for e in elements:
        # Complete a unit when encountering a divider
        if e.elem_type == Element.DIVIDER_TYPE:
            units.append(current_unit)
            current_unit = []
        # Otherwise add to current unit
        else:
            current_unit.append(e)
    return units


units = group_elements(elements)

debug_listed_data(units, 'debug_units.txt')

# Step 2: initalize a list of dicts to hold question answers.
questions = [{} for i in range(0, len(units))]


# Step 3: loop over units to extract data into questions list.
def get_elem_by_text(unit: list, text: str) -> Element:
    """Search a list of Elements for text in element text."""
    for e in unit:
        if text in e.text:
            return e


def get_variable_name(unit: list, tol=5) -> str:
    # Set up triangulation boundaries
    left_elem = get_elem_by_text(unit, Field.variable_name.value)
    right_elem = get_elem_by_text(unit, Field.length.value)
    l, t = left_elem.left, left_elem.top
    r = right_elem.left
    out = []
    for e in unit:
        if (l < e.left < r) and (t - 5 < e.top < t + 5):
            out.append(e.text)
    # Should only find one element
    try:
        assert len(out) == 1
    except AssertionError:
        raise AssertionError(
            f"Found more than one element between "
            f"{l}, {r}, and within {tol}px of {t}."
            f"\nElements Founds:\n{out}"
            )
    return out[0]


def get_length(unit: list):
    return (get_elem_by_text(unit, Field.length.value)
            .text.split(':')[1].strip())


def get_position(unit: list):
    return (get_elem_by_text(unit, Field.position.value)
            .text.split(':')[1].strip())


for unit, q in zip(units, questions):
    q[Field.variable_name.name] = get_variable_name(unit)
    q[Field.length.name] = get_length(unit)
    q[Field.position.name] = get_position(unit)

debug_listed_data(questions, 'debug_questions.txt')
