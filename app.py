import pandas as pd
from pathlib import Path
import streamlit as st

DATA_FOLDER = Path('data') 
CLPS_DATA = DATA_FOLDER / 'clps.csv'

SURVEY_VARS_FOLDER = Path('survey_vars')
CODEBOOK_TOC = SURVEY_VARS_FOLDER / 'cdbk.tsv'
CODEBOOK_SEP = '\t'


df = pd.read_csv(CLPS_DATA)

st.write(df.head())