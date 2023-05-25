import pandas as pd
from pathlib import Path
from textwrap import wrap
import streamlit as st
import altair as alt
import yaml
from clps.constants.special_vars_names import ID_KEY, WEIGHT_KEY
from clps.constants.special_vars_names import GROUPBY_VARS
import clps.survey_vars_utils as svu
import clps.transform as transform
from clps.survey_vars_utils import SurveyVars
from clps.transform import transform_data
# Hot reloading of modules doesn't seem to work, although apparently it should
# be solved.
# Reload the modules during local development to avoid restarting the server.
# Note: for `from` import, have to import the main module, then the do
# from import, the reload the main module.
from importlib import reload
reload(svu)
reload(transform)


CONFIG_FP = Path('config.yaml')

LABEL_SPLIT = '----'

Y_FREQ_AXIS_LABEL = 'Count'
Y_WT_FREQ_AXIS_LABEL = 'Weighted Count'

TEXT_FP = Path('text')
TEXT_INTRO_FP = TEXT_FP / 'intro.md'
# These are survey variables that shouldn't be displayed
NON_SELECTABLE = [ID_KEY, WEIGHT_KEY]
# This text is displayed when no region is selected for the region selectbox
NATIONAL = 'National'


def deploy_sidebar(intro_fp: str | Path) -> None:
    """Create the sidebar.

    Args:
        intro_fp: File path to the markdown file containing the introduction
            text.
    """
    if isinstance(intro_fp, str):
        intro_fp = Path(intro_fp)
    st.sidebar.markdown(TEXT_INTRO_FP.read_text(),
                        unsafe_allow_html=True)


def deploy_survey_var_selectbox(
        survey_vars: SurveyVars,
        exclude: list = None) -> str:
    """Deploy a selectbox to choose a survey variable.

    Survey variables are formatted to include the variable name and the
    concept text, e.g. 'PHHP01P - Number of people in household'.

    Args:
        raw_df: CLPS raw dataframe.
        survey_vars: SurveyVars object, containing variable metadata.
        exclude: List of variables to exclude from the selectbox.

    Returns:
        Name (str) of the selected variable, e.g. 'PUMFID'.
    """
    selectable = survey_vars.get_all_var_names()
    selectable = [x for x in selectable if x not in exclude]

    return st.selectbox(
        label='Variable',
        options=selectable,
        format_func=lambda k: f"{k} - {survey_vars[k].concept}"
    )


def deploy_region_selectbox(survey_vars: SurveyVars) -> int | None:
    """Deploy a selectbox to filter the data by region."""
    regions = survey_vars.get_region()
    opts = [None] + regions.codes
    return st.selectbox(
        label='Region',
        options=opts,
        format_func=lambda e:
            NATIONAL if e is None else
            regions.lookup_answer(e)
    )


def deploy_groupby_var_selectbox(selected_var_to_exclude: str) -> str | None:
    """Select a variable to groupby, if any.

    Args:
        selected_var_to_exclude: If the variable selected for display is one of
            the available groupby variables, it is removed as an option.

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


def deploy_valid_skips_checkbox(
        survey_vars: SurveyVars,
        selected_var: str) -> bool:
    """Deploy a checkbox to remove valid skips from the data.

    Checks SurveyVars object to see if the answer categories has a valid skip
    category. I.e. does not directly interrogate the main data.

    Args:
        survey_vars: SurveyVars object, containing variable metadata.
        selected_var: The variable selected for display.

    Returns:
        Bool, whether to remove valid skips from the data. False if the
        selected survey variable has no valid skips or no answer section."""
    if survey_vars[selected_var].has_valid_skips():
        # Deploy the checkbox
        remove_valid_skips = st.checkbox('Remove valid skips', value=True)
    else:
        remove_valid_skips = False
    return remove_valid_skips


def style_datatable(
        df: pd.DataFrame,
        weighted: bool) -> pd.io.formats.style.Styler:
    return (df
            .rename(
                {WEIGHT_KEY:
                    Y_WT_FREQ_AXIS_LABEL if weighted else Y_FREQ_AXIS_LABEL},
                axis='columns')
            .style
            # Note: hide(axis='index') doesn't work with streamlit.
            # Streamlit as of >= 1.10 can't hide row indices at all in a
            # st.dataframe call.
            # https://docs.streamlit.io/knowledge-base/using-streamlit/hide-row-indices-displaying-dataframe
            .hide(axis='index')
            )


def create_chart(
        df: pd.DataFrame,
        survey_vars: SurveyVars,
        selected_var: str,
        groupby_var: str | None,
        plot_weighted: bool) -> alt.Chart:

    LABEL_WEIGHTED = 'Weighted Count'
    LABEL_UNWEIGHTED = 'Count'
    LABEL_SELECT_VAR = 'Category'
    LABEL_GROUPBY_VAR = 'Sub-group'

    # Assemble chart arguments into dict for expansion
    chart_args = {}
    # Choose Y axis title, depending if un/weighted counts are used
    if plot_weighted:
        y = alt.Y(f"{WEIGHT_KEY}:Q", title=Y_WT_FREQ_AXIS_LABEL)
    else:
        y = alt.Y(f"{WEIGHT_KEY}:Q", title=Y_FREQ_AXIS_LABEL)
    chart_args['y'] = y

    # X axis
    # Sorting of labels is by the original order in the codebook.
    x = alt.X(f"{selected_var}",
              type='ordinal',
              title=f"{selected_var} - {survey_vars[selected_var].concept}",
              sort=list(df[selected_var].cat.categories),
              axis=alt.Axis(labelLimit=1000,
                            labelAngle=-45,
                            # False seems not be the default, despite the docs?
                            labelOverlap=False,
                            labelExpr=f"split(datum.label, '{LABEL_SPLIT}')"))
    chart_args['x'] = x

    # Groupby is encoded in color.
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
            f"{groupby_var}:N",
            title=GROUPBY_VARS[groupby_var],
            sort=alt.Sort(groupby_order))
        order = alt.Order(
            f'color_{groupby_var}_sort_index:Q', sort='descending')
        chart_args['color'] = color
        chart_args['order'] = order

    # Format the tooltips
    tooltip = [
        alt.Tooltip(
            f"{WEIGHT_KEY}:Q",
            title=LABEL_WEIGHTED if plot_weighted else LABEL_UNWEIGHTED),
        alt.Tooltip(f"{selected_var}:O", title=LABEL_SELECT_VAR),
        ]
    if groupby_var is not None:
        tooltip.append(
            alt.Tooltip(f"{groupby_var}:O", title=LABEL_GROUPBY_VAR)
            if groupby_var else None,
        )
    chart_args['tooltip'] = tooltip

    return (alt.Chart(df)
            .mark_bar()
            .encode(**chart_args)
            .configure_axis(labelFontSize=14,
                            titleFontSize=16,
                            # labelFontWeight='bold',
                            # titleFontWeight='bold',
                            ))


def make_gap(n=3):
    """Make a gap of n `st.text('')` elements."""
    for _ in range(n):
        st.text('')


def load_config() -> dict:
    """Load the config file."""
    with CONFIG_FP.open() as f:
        return yaml.safe_load(f)


@st.cache_data
def load_data(fp: str | Path) -> pd.DataFrame:
    return pd.read_csv(fp)


# REFACTOR: currently uncached. Cacheing is possible with
# returned object is pickle serializable, but can't because of mutation.
# Can get around by making SurveyVars able to initialize with dict
# representation of JSON.
def load_survey_vars(fp: str | Path):
    return SurveyVars(fp)


def main(debug=False, log_file_path: str | None = None):
    if debug and log_file_path is None:
        raise ValueError('Must provide log file path if debug is True.')

    # Load configuation YAML file
    config = load_config()
    # Load main data and survey vars codebook info
    if config['data']['use_clps_compressed']:
        df = load_data(config['data']['clps_compressed'])
    else:
        df = load_data(config['data']['clps_file'])
    svs = load_survey_vars(config['data']['survey_vars_file'])

    # BEGIN: DATA SELECTION WIDGETS AND UI
    # Side bar with explanations
    deploy_sidebar(config['text']['intro_file'])
    # Choose a variable for display
    selected_var = deploy_survey_var_selectbox(svs, NON_SELECTABLE)
    # Choose region to filter
    region = deploy_region_selectbox(svs)
    # Choose variable for bar chart groupings
    groupby_var = deploy_groupby_var_selectbox(selected_var)
    # Selector for weighted/unweighted frequency
    plot_weighted = st.checkbox('Plot weighted frequency', value=True)
    remove_valid_skips = deploy_valid_skips_checkbox(svs, selected_var)
    # Spacing
    st.divider()
    make_gap(3)
    # END: DATA SELECTION WIDGETS AND UI

    # Transform data
    df = transform_data(
        df=df,
        survey_vars=svs,
        region=region,
        selected_var=selected_var,
        groupby_var=groupby_var,
        remove_valid_skips=remove_valid_skips,
        weighted=plot_weighted)

    chart_df = df.copy()

    # Hack to wrap long labels, for splitting in altair.
    # `wrap` breaks long str into a list of str, then stitch them back together
    # with LABEL_SPLIT delimiter. Altair then uses this delimiter to split
    # the str again using Vega expressions.
    chart_df = chart_df.assign(**{
        selected_var: lambda d: d[selected_var].cat.rename_categories(
            lambda e: LABEL_SPLIT.join(wrap(e, 20)))
    })

    chart_df = create_chart(
        chart_df, svs, selected_var, groupby_var, plot_weighted)

    st.altair_chart(chart_df.interactive(),
                    use_container_width=True,
                    )

    st.divider()
    make_gap(2)

    # Display datatable
    df = style_datatable(df, plot_weighted)
    st.dataframe(df, use_container_width=True)
    # Logging for debugging
    if debug:
        import logging
        logging.basicConfig(filename=log_file_path, level=logging.DEBUG)
        alt.data_transformers.disable_max_rows()
        logging.debug(chart_df.to_json())

    # Return objects for testing
    return {'processed_data': df, 'chart': chart_df,
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
