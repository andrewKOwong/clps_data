import argparse
from pathlib import Path
from bs4 import BeautifulSoup, Tag

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

parser = argparse.ArgumentParser()

parser.add_argument(
    'cdbk_html',
    help="pdf2txt.py codebook.pdf -o codebook.html --output_type html"
)

args = parser.parse_args()

p = Path(args.cdbk_html)

with p.open() as f:
    soup = BeautifulSoup(f, 'html.parser')

soup = soup.body.extract()

# This is the div whose child is an anchor for the start of page 9
start_div = soup.select(f'a[name="{START_PAGE}"]')[0].parent
# Regenerating just the data pages
# by finding all siblings of the start div,
# and iterating through and appending until we get the div that
# is right after the ending data page,
# then reconstituting the strings into another soup object.
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

with open("test.html", 'w') as f:
    f.write(soup.prettify())
