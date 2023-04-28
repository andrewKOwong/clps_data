import pandas as pd
from pathlib import Path
import streamlit as st
from clps.constants import survey_vars_keys as SVK
import clps.survey_vars_utils as svu
import clps.transform as tfm
from importlib import reload
reload(svu)
reload(tfm)


DATA_FOLDER = Path('data')
CLPS_DATA_FP = DATA_FOLDER / 'clps.csv'
SURVEY_VARS_FP = DATA_FOLDER / 'survey_vars.json'


COLS_TO_KEEP = ['PUMFID', 'AGEGRP', 'REGION', 'GDRP10', 'WTPP', 'PRIP10H']

VAR_OF_INTEREST = 'PRIP10H'
VALID_SKIP = 'Valid skip'


def main():
    df = pd.read_csv(CLPS_DATA_FP)

    freq_df = tfm.prepare_plotable_df(df, VAR_OF_INTEREST, region_filter=1, plot_weighted=False)

    st.write(freq_df)

    st.bar_chart(data=freq_df, x=None, y='Count')

    wt_freq_df = tfm.prepare_plotable_df(
        df, VAR_OF_INTEREST, region_filter=1, plot_weighted=True)

    st.write(wt_freq_df)

    st.bar_chart(data=wt_freq_df, x=None, y='Weighted Count')


if __name__ == '__main__':
    main()
