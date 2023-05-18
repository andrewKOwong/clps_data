import pandas as pd
from pathlib import Path
from textwrap import wrap
import streamlit as st
import altair as alt
import clps.survey_vars_utils as svu
from clps.survey_vars_utils import SurveyVars
import clps.transform as tfm
from importlib import reload
reload(svu)
reload(tfm)


DATA_FOLDER = Path('data')
CLPS_DATA_FP = DATA_FOLDER / 'clps.csv'
CLPS_COMPRESSED_FP = DATA_FOLDER / 'clps.zip'
SURVEY_VARS_FP = DATA_FOLDER / 'survey_vars.json'

ID_KEY = 'PUMFID'
NUMPPLHOUSE_KEY = 'PHHP01P'
NUMPPLHOUSE18_KEY = 'PHHP02P'
AGE_KEY = 'AGEGRP'
REGION_KEY = 'REGION'
GENDER_KEY = 'GDRP10'
RURALURBAN_KEY = 'RURURBP'
SEXORIENT_KEY = 'SORFLAGP'
INDIG_KEY = 'IIDFLGP'
VISMINORITY_KEY = 'VISMFLP'
EDU_KEY = 'EDUGRPP'
EMPLOYED_KEY = 'MAP01'
WEIGHT_KEY = 'WTPP'

VALID_SKIP = 'Valid skip'

GROUPBY_VARS = {
    NUMPPLHOUSE_KEY: 'Number of People in Household',
    NUMPPLHOUSE18_KEY: 'Number of People in Household 18+',
    AGE_KEY: 'Age',
    GENDER_KEY: 'Gender',
    RURALURBAN_KEY: 'Rural/Urban',
    SEXORIENT_KEY: 'Sexual Orientation',
    INDIG_KEY: 'Indigenous Identity',
    VISMINORITY_KEY: 'Visible Minority',
    EDU_KEY: 'Highest Education',
    EMPLOYED_KEY: 'Worked at Job/Business in Last 12 Months'
}

LABEL_SPLIT = '----'

SAVE_HINT = 'To save the chart, click on dots in the upper-right corner.'
INTRO = (
    "The [Canadian Legal Problems Survey (CLPS)]"
    "(https://www.justice.gc.ca/eng/rp-pr/jr/survey-enquete.html)"
    " is a national survey of Canadians' experiences with the justice system,"
    " most recently conducted by Statisics Canada in 2021."
    " The original data is provided by StatsCan via a"
    " [Public Use Microdata File]"
    "(https://www150.statcan.gc.ca/n1/pub/35-25-0002/352500022022001-eng.htm)."
    " \n\n"
    " This app displays plots for each survey variable of the data:"
    " \n- Select a survey variable in the first dropdown (type to search)."
    " \n- Optionally, filter by region."
    " \n- Data may also be grouped by age or gender."
    " \n- Data is displayed as weighted counts to represent the entire "
    " population of Canada. To see actual counts of survey respondents,"
    " uncheck the box."
    " \n- Some survey questions are not presented to respondents based on "
    " their answers to previous questions. These are termed \"valid skips\"."
    " To include these, uncheck the box."

)


def create_sidebar():
    st.sidebar.title('CLPS Data Explorer')
    st.sidebar.write(INTRO)


def select_var(
        raw_df: pd.DataFrame,
        survey_vars: SurveyVars,
        exclude: list = None) -> str:
    selectable = raw_df.columns[~raw_df.columns.isin(exclude)]
    return st.selectbox(
        label='Variable',
        options=selectable,
        format_func=lambda k: f"{k} - {survey_vars[k].concept}"
    )


def select_region(survey_vars: SurveyVars) -> str:
    NATIONAL = 'National'
    regions = survey_vars.get_region()
    opts = [None] + regions.codes
    return st.selectbox(
        label='Region',
        options=opts,
        format_func=lambda e:
            NATIONAL if e is None else
            regions.lookup_answer(e)
    )


def select_groupby_var(selected_var_to_exclude: str) -> str:
    """Select a variable to groupby, if any.

    Args:
        selected_var_to_exclude: If the variable selected for display is one of
            the avaiable groupby variables, it is removed as an option.

    Returns:
        Str code for variable to groupby, or `None`.
    """
    options = [None] + list(GROUPBY_VARS.keys())
    if selected_var_to_exclude in options:
        options.remove(selected_var_to_exclude)
    return st.selectbox(
        label='Groupby:',
        options=options,
        format_func=lambda k: 'None' if k is None else GROUPBY_VARS[k])


def create_ordered_dtype(s: pd.Series) -> pd.CategoricalDtype:
    """From int column, create an ordered categorical dtype."""
    return pd.CategoricalDtype(
        categories=s.sort_values().unique(),
        ordered=True)


def order_and_convert_code(
        s: pd.Series,
        survey_vars: SurveyVars) -> pd.Series:
    """Converts a series of codes to text labels, as ordered categorical."""
    return (s
            .astype(create_ordered_dtype(s))
            .cat.rename_categories(
                survey_vars[s.name].lookup_answer))


def temp_process_data(
        df: pd.DataFrame,
        selected_var: str,
        groupby_var: str | None,
        weighted: bool,
        ) -> pd.DataFrame:
    df = df.copy()

    groupby_list = [selected_var]
    if groupby_var is not None:
        groupby_list.append(groupby_var)
    grpby = df.groupby(groupby_list)[[WEIGHT_KEY]]  # groupby object

    if weighted:
        out = grpby.sum()
    else:
        out = grpby.count()

    # # Bug with streamlit? Where categorical indexes display with a warning
    # # That "The value is not part of the allowed options" along with a
    # # yellow exclamtion mark. This is a workaround.
    # out.index = out.index.astype('object')

    return (out
            .round()
            .astype(int)
            .reset_index()
            )


def style_datatable(
        df: pd.DataFrame) -> pd.io.formats.style.Styler:
    return (df
            .style
            # Note: hide(axis='index') doesn't work with streamlit.
            # Streamlit as of >= 1.10 can't hide row indices at all in a
            # st.dataframe call.
            # https://docs.streamlit.io/knowledge-base/using-streamlit/hide-row-indices-displaying-dataframe
            .hide(axis='index')
            )


@st.cache_data
def load_data():
    return pd.read_csv(CLPS_COMPRESSED_FP)


# REFACTOR: currently uncached. Cacheing is possible with
# returned object is pickle serializable, but can't because of mutation.
# Can get around by making SurveyVars able to initialize with dict
# representation of JSON.
def load_survey_vars(fp: str | Path):
    return SurveyVars(fp)


def main(debug=False, log_file_path: str | None = None):
    if debug and log_file_path is None:
        raise ValueError('Must provide log file path if debug is True.')

    create_sidebar()
    df = load_data()

    svs = load_survey_vars(SURVEY_VARS_FP)

    non_selectable = [ID_KEY, WEIGHT_KEY]
    # Load data
    # Choose a variable for display
    selected_var = select_var(df, svs, non_selectable)
    # Choose region to filter
    region = select_region(svs)
    # Choose variable for bar chart groupings
    groupby_var = select_groupby_var(selected_var)

    # Selector for weighted/unweighted frequency
    plot_weighted = st.checkbox('Plot weighted frequency', value=True)

    # Space for valid skip removal container.
    skip_container = st.container()

    # BEGIN: DATA TRANSFORMATIONS
    # Region filtering
    if region is not None:
        df = tfm.filter_by_region(df, region)
    # Groupby filtering
    if groupby_var is None:
        df = df[[selected_var, WEIGHT_KEY]]
    else:
        df = df[[selected_var, groupby_var, WEIGHT_KEY]]

    # Change ints to ordered categorical to preserve order,
    # then convert to text labels.
    # Mapping automatically converts categorical info.
    df = df.assign(**{
        selected_var: lambda d: (
            order_and_convert_code(d[selected_var], svs))})
    if groupby_var is not None:
        df = df.assign(**{
            groupby_var: lambda d: (
                order_and_convert_code(d[groupby_var], svs))})

    # Check if data contains "Valid skip" codes.
    # If so, add checkbox to give the option to remove them.
    if VALID_SKIP in df[selected_var].cat.categories:
        with skip_container:
            remove_valid_skips = st.checkbox('Remove valid skips', value=True)
        if remove_valid_skips:
            df = df.query(f"{selected_var} != '{VALID_SKIP}'")
    # END: DATA TRANSFORMATIONS

    # TODO Testing data tables
    # Need to do counts, or not counts.
    # Groupbys or not groupbys.
    df2 = df.copy()

    df2 = temp_process_data(df2, selected_var, groupby_var, plot_weighted)
    print(df2)

    df2 = style_datatable(df2)
    st.dataframe(df2)

    # BEGIN: CHART PREPARATION
    # Hack to wrap long labels, for splitting in altair.
    # `wrap` breaks long str into a list of str, then stitch them back together
    # with LABEL_SPLIT delimiter. Altair then uses this delimiter to split
    # the str again using Vega expressions.
    df = df.assign(**{
        selected_var: lambda d: d[selected_var].cat.rename_categories(
            lambda e: LABEL_SPLIT.join(wrap(e, 20)))
    })

    # Assemble chart arguments
    chart_args = {}
    # Y is dependent on whether weights are used
    if not plot_weighted:
        y = alt.Y(f"count({selected_var}):Q", title='Count')
    else:
        y = alt.Y(f'sum({WEIGHT_KEY}):Q', title='Weighted Count')
    chart_args['y'] = y
    # X is bar chart labels. Sorting of the labels is by the original order
    # in the codebook.
    x = alt.X(f"{selected_var}",
              type='ordinal',
              title=f"{selected_var} - {svs[selected_var].concept}",
              sort=list(df[selected_var].cat.categories),
              axis=alt.Axis(labelLimit=1000,
                            labelAngle=-45,
                            # False seems not be the default, despite the docs?
                            labelOverlap=False,
                            labelExpr=f"split(datum.label, '{LABEL_SPLIT}')"))
    chart_args['x'] = x
    # Use color for groupbys
    if groupby_var is not None:
        groupby_order = list(df[groupby_var].cat.categories)
        # Color is also ordered according to the codebook.
        # For info about how to order both the legend and the order on the
        # bar chart stacks, see:
        # https://github.com/altair-viz/altair/issues/245#issuecomment-748443434
        # The above is actually the official recommended solution according to
        # the docs (search "follow the approach in this issue comment"):
        # https://altair-viz.github.io/user_guide/encodings/channels.html#order
        color = alt.Color(
            f"{groupby_var}:O",
            title=GROUPBY_VARS[groupby_var],
            sort=alt.Sort(groupby_order))
        order = alt.Order(
            f'color_{groupby_var}_sort_index:Q', sort='descending')
        chart_args['color'] = color
        chart_args['order'] = order

    # Make the chart object
    chart = alt.Chart(df).mark_bar().encode(**chart_args)
    # END: CHART PREPARATION

    # Plot the chart
    st.altair_chart(chart, use_container_width=True)
    # Hint for the user on how to save the chart
    st.markdown(SAVE_HINT)

    # Logging for debugging
    if debug:
        import logging
        logging.basicConfig(filename=log_file_path, level=logging.DEBUG)
        alt.data_transformers.disable_max_rows()
        logging.debug(chart.to_json())

    # Return objects for testing
    return {'processed_data': df, 'chart': chart, 'chart_args': chart_args,
            'survey_vars': svs,
            'selected_var': selected_var, 'groupby_var': groupby_var,
            }


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
