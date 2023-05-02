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

GROUPBY_VARS = {AGE_KEY: 'Age', GENDER_KEY: 'Gender'}


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


def select_region(keyed_survey_vars: dict):
    NATIONAL = 'National'
    regions = svu.SurveyVar(keyed_survey_vars[REGION_KEY])
    opts = [None] + regions.codes
    return st.selectbox(
        label='Region',
        options=opts,
        format_func=lambda e:
            NATIONAL if e is None else
            regions.get_answer(e)
    )


def select_groupby_var() -> str:
    return st.selectbox(
        label='Groupby:',
        options=GROUPBY_VARS.keys(),
        format_func=lambda k: GROUPBY_VARS[k])


def remove_valid_skips(df: pd.DataFrame) -> pd.DataFrame:
    return df[df[VAR_OF_INTEREST] != VALID_SKIP]


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
    # Choose region to filter
    region = select_region(svs)
    # Choose variable for bar chart groupings
    groupby_var = select_groupby_var()

    # Selector for weighted/unweighted frequency
    plot_weighted = st.checkbox('Plot weighted frequency', value=True)
    remove_valid_skips = st.checkbox('Remove valid skips', value=True)

    # Region filtering
    if region is not None:
        df = tfm.filter_by_region(df, region)
    # Groupby filtering
    df = df[[selected_var, groupby_var, WEIGHT_KEY]]

    # Change ints to text
    df = df.assign(**{
        selected_var: lambda d: d[selected_var].map(
            svu.SurveyVar(svs[selected_var]).get_answer
        ),
        groupby_var: lambda d: d[groupby_var].map(
            svu.SurveyVar(svs[groupby_var]).get_answer)
    })

    if remove_valid_skips:
        df = df.query(f"{selected_var} != 6")

    if not plot_weighted:
        y = f"count({selected_var})"
    else:
        y = 'sum(WTPP)'

    chart = alt.Chart(df).mark_bar().encode(
        x=f"{selected_var}:N",
        y=y,
        color=alt.Color(
            f"{groupby_var}:O", title=GROUPBY_VARS[groupby_var])
    )

    st.altair_chart(chart, use_container_width=True)

    # TODO X and Y axis titles
    # TODO dealing with when region is in or not
    # TODO compress data
    # TODO tool tips and such
    # TODO add metric to display low count warning.
    # TODO Handle PROBCNTP and VERDATE
    # TODO Intro stuff
    # TODO show Analise first.
    # TODO consider testing
    # TODO Add note about saving as SVG/PNG
    # TODO Deal with PROBCNTP


if __name__ == '__main__':
    main()
