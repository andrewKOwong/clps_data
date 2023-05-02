import pandas as pd
from pathlib import Path
import streamlit as st
import altair as alt
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

GROUPBY_DICT = {'Age': 'AGEGRP', 'Gender': 'GDRP10'}


def create_sidebar():
    st.sidebar.title('CLPS Data Explorer')
    st.sidebar.markdown('''
    This is a simple app to explore the CLPS data.
    ''')


def create_groupby():
    return GROUPBY_DICT[st.selectbox('Groupby:', GROUPBY_DICT.keys())]


def main():
    create_sidebar()
    # Choose a variable for display
    selected_var = st.selectbox('Variable Name', [VAR_OF_INTEREST, 'RURURBP'])

    region = st.selectbox('Region', ['National', 1, 2, 3, 4, 5])
    groupby_var = create_groupby()

    # Selector for weighted/unweighted frequency
    plot_weighted = st.checkbox('Plot weighted frequency', value=True)
    remove_valid_skips = st.checkbox('Remove valid skips', value=True)

    df = pd.read_csv(CLPS_DATA_FP)

    if region != 'National':
        df = tfm.filter_by_region(df, region)

    df = df[[selected_var, groupby_var, 'WTPP']]

    if remove_valid_skips:
        df = df.query(f"{selected_var} != 6")

    if not plot_weighted:
        chart = alt.Chart(df).mark_bar().encode(
            x=f"{selected_var}:N",
            y=f'count({selected_var})',
            color=f"{groupby_var}:O"
        )
    else:
        chart = alt.Chart(df).mark_bar().encode(
            x=f"{selected_var}:N",
            y='sum(WTPP)',
            color=f"{groupby_var}:O"
        )

    st.altair_chart(chart, use_container_width=True)

    # Add note about saving as SVG/PNG


if __name__ == '__main__':
    main()
