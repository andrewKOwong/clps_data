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

ID_KEY = 'PUMFID'
AGE_KEY = 'AGEGRP'
REGION_KEY = 'REGION'
GENDER_KEY = 'GDRP10'
WEIGHT_KEY = 'WTPP'
VAR_OF_INTEREST = 'PRIP10H'

VALID_SKIP = 'Valid skip'


def create_sidebar():
    st.sidebar.title('CLPS Data Explorer')
    st.sidebar.markdown('''
    This is a simple app to explore the CLPS data.
    ''')


def select_var(
        raw_df: pd.DataFrame,
        keyed_survey_vars: dict,
        exclude: list = None) -> str:
    selectable = raw_df.columns[~raw_df.columns.isin(exclude)]
    return st.selectbox(
        label='Variable',
        options=selectable,
        format_func=lambda k: f"{k} - {keyed_survey_vars[k][SVK.CONCEPT]}"
    )


def select_region():
    return st.selectbox('Region', ['National', 1, 2, 3, 4, 5])


def select_groupby_var() -> str:
    GROUPBY_DICT = {'Age': AGE_KEY, 'Gender': GENDER_KEY}
    return GROUPBY_DICT[st.selectbox('Groupby:', GROUPBY_DICT.keys())]


@st.cache_data
def load_data():
    return pd.read_csv(CLPS_DATA_FP)


@st.cache_data
def load_survey_vars():
    return svu.load_keyed_survey_vars(SURVEY_VARS_FP)


def main():
    create_sidebar()
    df = load_data()
    svs = load_survey_vars()

    non_selectable = [ID_KEY, AGE_KEY, GENDER_KEY, REGION_KEY, WEIGHT_KEY]
    # Load data
    # Choose a variable for display
    selected_var = select_var(df, svs, non_selectable)

    region = select_region()
    groupby_var = select_groupby_var()

    # Selector for weighted/unweighted frequency
    plot_weighted = st.checkbox('Plot weighted frequency', value=True)
    remove_valid_skips = st.checkbox('Remove valid skips', value=True)

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

    # TODO tidying of the names
    # TODO dealing with when region is in or not
    # TODO show Analise first.
    # TODO consider testing
    # TODO Add note about saving as SVG/PNG
    # TODO Deal with PROBCNTP


if __name__ == '__main__':
    main()
