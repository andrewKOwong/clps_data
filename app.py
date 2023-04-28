import pandas as pd
from pathlib import Path
import streamlit as st
import json
from clps.transform import *
from clps.constants import survey_vars_keys as SVK

DATA_FOLDER = Path('data')
CLPS_DATA_FP = DATA_FOLDER / 'clps.csv'
SURVEY_VARS_FP = DATA_FOLDER / 'survey_vars.json'


COLS_TO_KEEP = ['PUMFID', 'AGEGRP', 'REGION', 'GDRP10', 'WTPP', 'PRIP10H']

VAR_OF_INTEREST = 'PRIP10H'
VALID_SKIP = 'Valid skip'

df = pd.read_csv(CLPS_DATA_FP)

sv = json.load(SURVEY_VARS_FP.open())
sv = {e[SVK.VAR_NAME]: e for e in sv}

df = df[COLS_TO_KEEP]
df = df[df['REGION'] == 1]
st.write(df.head())
disp_df = df[VAR_OF_INTEREST].value_counts().rename('freq')

st.write(disp_df)

# Reorder the index
order = [int(e) for e in sv[VAR_OF_INTEREST][SVK.CODE]]
disp_df = disp_df.reindex(order)
st.write('Reorder')
st.write(disp_df)


def extract_survey_vars_dict(survey_vars: dict, key: str) -> dict:
    """Extract the survey variables from the survey variables dictionary."""
    return survey_vars[key]


def generate_code_lookup(sv: dict) -> dict:
    """Generate a lookup table for the codes of each variable."""
    return {int(code): ans_cat
            for code, ans_cat in zip(sv[SVK.CODE], sv[SVK.ANSWER_CATEGORIES])}


code_lookup = generate_code_lookup(
        extract_survey_vars_dict(sv, VAR_OF_INTEREST))


disp_df = disp_df.rename(code_lookup)


st.write(disp_df)

# Remove valid skips
disp_df = disp_df.drop(index=VALID_SKIP)

st.write(disp_df)


st.bar_chart(data=disp_df, x=None, y='freq')
