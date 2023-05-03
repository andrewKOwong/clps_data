import pandas as pd
from pathlib import Path
from textwrap import wrap
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
CLPS_COMPRESSED_FP = DATA_FOLDER / 'clps.zip'
SURVEY_VARS_FP = DATA_FOLDER / 'survey_vars.json'

ID_KEY = 'PUMFID'
AGE_KEY = 'AGEGRP'
REGION_KEY = 'REGION'
GENDER_KEY = 'GDRP10'
WEIGHT_KEY = 'WTPP'
VAR_OF_INTEREST = 'PRIP10H'

VALID_SKIP = 'Valid skip'

GROUPBY_VARS = {AGE_KEY: 'Age', GENDER_KEY: 'Gender'}

LABEL_SPLIT = '----'

SAVE_HINT = 'To save the chart, click on dots in the upper-right corner.'


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


def create_ordered_dtype(s: pd.Series) -> pd.CategoricalDtype:
    """From int column, create an ordered categorical dtype."""
    return pd.CategoricalDtype(
        categories=s.sort_values().unique(),
        ordered=True)


@st.cache_data
def load_data():
    return pd.read_csv(CLPS_COMPRESSED_FP)


@st.cache_data
def load_survey_vars():
    return svu.load_keyed_survey_vars(SURVEY_VARS_FP)


def main(debug=False, log_file_path: str | None = None):
    if debug and log_file_path is None:
        raise ValueError('Must provide log file path if debug is True.')

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

    # Change ints to ordered categorical to preserve order,
    # then convert to text labels.
    # Mapping automatically converts categorical info.
    # REFACTOR: using .cat.rename_categories() is more expressive.
    df = df.assign(**{
        selected_var: lambda d: (
            d[selected_var].astype(create_ordered_dtype(d[selected_var]))
            .map(lambda e: svu.SurveyVar(svs[selected_var]).get_answer(e))
        ),
        groupby_var: lambda d: (
            d[groupby_var].astype(create_ordered_dtype(d[groupby_var]))
            .map(svu.SurveyVar(svs[groupby_var]).get_answer)
        )
    })

    if remove_valid_skips:
        df = df.query(f"{selected_var} != '{VALID_SKIP}'")

    # Hack to wrap long labels, for splitting in altair.
    df = df.assign(**{
        selected_var: lambda d: d[selected_var].cat.rename_categories(
            lambda e: LABEL_SPLIT.join(wrap(e, 20)))
    })

    if not plot_weighted:
        y = alt.Y(f"count({selected_var})", title='Count')
    else:
        y = alt.Y(f'sum({WEIGHT_KEY})', title='Weighted Count')

    x = alt.X(f"{selected_var}",
              type='ordinal',
              title=f"{selected_var} - {svs[selected_var][SVK.CONCEPT]}",
              sort=list(df[selected_var].cat.categories),
              axis=alt.Axis(labelLimit=1000,
                            labelAngle=-45,
                            labelExpr=f"split(datum.label, '{LABEL_SPLIT}')"))

    groupby_order = list(df[groupby_var].cat.categories)

    chart = alt.Chart(df).mark_bar()
    chart = chart.encode(
        x=x,
        y=y,
        color=alt.Color(
            f"{groupby_var}:O",
            title=GROUPBY_VARS[groupby_var],
            sort=groupby_order)
    )

    st.altair_chart(chart, use_container_width=True)

    st.markdown(SAVE_HINT)

    # TODO Color order is wrong?!?!
    # TODO Add no groupby option
    # TODO dealing with when region is in or not
    # TODO tool tips and such
    # TODO Handle PROBCNTP and VERDATE
    # TODO Intro stuff
    # TODO add metric to display low count warning.
    # TODO show Analise first.
    # TODO consider testing, may have to
    # TODO Deal with PROBCNTP
    # TODO add loading indicator for data processing
    # TODO Chart scaling


if __name__ == '__main__':
    # Run as a regular python script for debug options
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--log_file', default='clps_data_explorer.log')
    args = parser.parse_args()
    debug = args.debug
    log_file_path = args.log_file
    main(debug=debug, log_file_path=log_file_path)
