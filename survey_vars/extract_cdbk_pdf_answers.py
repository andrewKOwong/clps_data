import argparse
from pathlib import Path
from bs4 import BeautifulSoup, Tag
import re

FIELDS = {
    'variable_name': 'Variable Name',
    'length': 'Length',
    'position': 'Position',
    'question_name': 'Question',
    'concept': 'Concept',
    'question_text': 'Question Text',
    'universe': 'Universe',
    'note': 'Note',
    'source': 'Source',
    'answer_categories': 'Answer Categories',
    'code': 'Code',
    'frequency': 'Frequency',
    'weighted_frequency': 'Weighted Frequency',
    'percent': '%'
}

START_PAGE = 9  # First data page
END_PAGE = 126  # Last data page (inclusive)


# Shim this in between steps of the pipeline during debugging
# to write out an html file for inspection.
def debug_shim(soup: BeautifulSoup, out: str = 'debug.html') -> None:
    with open(out, 'w') as f:
        f.write(soup.prettify())


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


# For the remaining elements, rewrite the html
# to use new divs with type attributes of text/divider,
# and left/top attributes for positioning information.
html_doc = ""
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
        left = re.search(r"(?<=left:)\d+?(px;)", style).group(0)
        top = re.search(r"(?<=top:)\d+?(px;)", style).group(0)
        if left is None or top is None:
            raise ValueError(
                f"Did not find a left/top value."
                f"\n\nTag contents:\n"
                f"{str(tag)}"
                f"\n\nStyle attribute contents:\n"
                f"{str(style)}"
            )
        # Create new type attribute distinguishing
        # top level divs that have text fields
        # and top level spans that are dividers
        match tag.name:
            case 'div':
                type_val = 'text'
            case 'span':
                type_val = 'divider'
            case _:
                raise ValueError("Unexpected non div/span element.")
        html_doc += (
            f'<div type="{type_val}"'
            f' left="{left}" top="{top}">'
            f'{tag.text}'
            f'</div>')


soup = BeautifulSoup(html_doc, 'html.parser')


debug_shim(soup)
