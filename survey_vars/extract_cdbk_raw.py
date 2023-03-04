import argparse
import pandas as pd
from pathlib import Path

# Data column names
# These are from the headings in the codebook TOC, lowercased
COL_CODE = 'variable'
COL_POSITION = 'position'
COL_DESCRIPTION = 'description'
COL_PAGE = 'page'

# Command line arguments
parser = argparse.ArgumentParser(
    prog="python extract_cdbk_raw.py",
    description="""
    Extracts CLPS codebook table of contents variables.

    Example usage:
    python extract_cdbk_raw.py path_to/cdbk_toc_raw.txt path_to/cdbk.tsv
    """,
    formatter_class=argparse.RawTextHelpFormatter
)
parser.add_argument(
    'cdbk_file',
    help="Path for copy pasted TOC textfile from CLPS codebook."
)
parser.add_argument(
    'out_file',
    help="Path for output file (tab-delimited values), e.g. out.tsv."
)

args = parser.parse_args()
# Get the codebook file path
p = Path(args.cdbk_file)
# Set up dictionary to receive data
data = {COL_CODE: [], COL_POSITION: [], COL_DESCRIPTION: [], COL_PAGE: []}
# Read the data into list of strings per line
with p.open() as f:
    lines = f.readlines()
# Get column data from each line
for line in lines:
    code, pos = line.split(' ')[0:2]
    data[COL_CODE].append(code)
    data[COL_POSITION].append(pos)
    # Description slices off the back dots, slices off the front, then rejoin
    desc = ' '.join(line.split(' .')[0].split(' ')[2:])
    data[COL_DESCRIPTION].append(desc)
    page = line.split(' .')[-1].strip()
    data[COL_PAGE].append(page)

# Check all the columns the same length
try:
    assert (
        len(data[COL_CODE]) == len(data[COL_POSITION])
        == len(data[COL_DESCRIPTION]) == len(data[COL_PAGE])
    )
except AssertionError:
    raise AssertionError(
        f"""
        Data columns do not have matching lengths.
        {COL_CODE}: {len(data[COL_CODE])}
        {COL_POSITION}: {len(data[COL_POSITION])}
        {COL_DESCRIPTION}: {len(data[COL_DESCRIPTION])}
        {COL_PAGE}: {len(data[COL_PAGE])}
        """
    )

# Dump the data as a tsv
# Commas are present in data fields so csv not possible.
df = pd.DataFrame(data)
df.to_csv(args.out_file, index=False, sep='\t')
