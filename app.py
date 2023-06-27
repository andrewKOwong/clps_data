import pandas as pd
from pandas.io.formats.style import Styler
from pathlib import Path
from textwrap import wrap
import streamlit as st
import altair as alt
import yaml
from clps.constants import ID_KEY, WEIGHT_KEY
from clps.constants import GROUPBY_VARS
from clps.constants import VALID_SKIP_CODES
import clps.survey_vars.utils as svu
import clps.transform as transform
from clps.survey_vars.utils import SurveyVars
from clps.transform import transform_data
# Hot reloading of modules doesn't seem to work, although apparently it should
# be solved.
# Reload the modules during local development to avoid restarting the server.
# Note: for `from` import, have to import the main module, then the do
# from import, the reload the main module.
from importlib import reload
reload(svu)
reload(transform)

# App Title
st.set_page_config(page_title="CLPS Data Dashboard")


CONFIG_FP = Path('config.yaml')


Y_FREQ_AXIS_LABEL = 'Count'
Y_WT_FREQ_AXIS_LABEL = 'Weighted Count'

TEXT_FP = Path('text')
TEXT_INTRO_FP = TEXT_FP / 'intro.md'
# These are survey variables that shouldn't be displayed
NON_SELECTABLE = [ID_KEY, WEIGHT_KEY]
# This text is displayed when no region is selected for the region selectbox
NATIONAL = 'National'
# Chart label constants
# LABEL_SPLIT is used for breaking long labels, not sure why \n or \\n
# doesn't work
LABEL_SPLIT = '----'
LABEL_WEIGHTED = 'Weighted Count'  # y label for weighted charts
LABEL_UNWEIGHTED = 'Count'  # y label for unweighted charts
LABEL_SELECT_VAR = 'Category'  # tooltip label for selected survey variable
LABEL_GROUPBY_VAR = 'Sub-group'  # tooltip label for groupby variable
#
DATATABLE_HEADER_CSS = 'css/datatable_header.css'


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
        label='Variable (type to search)',
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


def deploy_valid_skip_selectbox(
        survey_vars: SurveyVars,
        selected_var: str) -> str | None:
    """Deploy a selectbox to choose valid skip handling.

    Checks SurveyVars object to see if the answer categories has a valid skip
    category. I.e. does not directly interrogate the main data.

    Recoding changes the valid skip category to 'No', removing removes the
    valid skip category from the data, and leaving does nothing.

    Args:
        survey_vars: SurveyVars object, containing variable metadata.
        selected_var: The variable selected for display.

    Returns:
        str code, one of 'recode', 'remove', or 'leave',
        other wise None if the selected survey var has no valid skips.
    """
    if survey_vars[selected_var].has_valid_skips():
        # Deploy the selectbox
        return st.selectbox(
            label='Valid skip handling:',
            options=[VALID_SKIP_CODES.RECODE,
                     VALID_SKIP_CODES.REMOVE,
                     VALID_SKIP_CODES.LEAVE
                     ],
            format_func=lambda k:
                {VALID_SKIP_CODES.RECODE: "Recode to 'No'",
                 VALID_SKIP_CODES.REMOVE: "Remove valid skips",
                 VALID_SKIP_CODES.LEAVE: "Leave as original data"}
                [k]
            )
    else:
        return None


def deploy_disable_interactivity_checkbox() -> bool:
    """Deploy a checkbox to disable interactive chart (pan/zoom).

    Returns:
        True if interactivity should be disabled.
    """
    return st.checkbox('Disable chart pan/zoom.', value=False)


def style_datatable(
        df: pd.DataFrame,
        selected_var: str,
        weighted: bool) -> Styler:

    # inject_datatable_header_style()
    # import numpy as np
    return (df
            .rename(
                {WEIGHT_KEY:
                    Y_WT_FREQ_AXIS_LABEL if weighted else Y_FREQ_AXIS_LABEL},
                axis='columns')
            # Note: in order to not display numerical indexes, the obvious
            # way would be `.style.hide(axis='index')`. However, Streamlit as
            # of >= 1.10 can't hide row indices at all in a st.dataframe call.
            # https://docs.streamlit.io/knowledge-base/using-streamlit/hide-row-indices-displaying-dataframe
            # Instead, we'll set the index as the selected variable to mimic
            # this behaviour. Unexpectedly, Streamlit has a problem with
            # categorical indexes, claiming that the index values are not
            # part of the allowed categorical values and displaying yellow
            # warning emojis. I am unable to suppress this, and it does not
            # appear to me that the values are actually not part of the
            # allowed values. The workaround is to convert the selected_var
            # column to str before setting it as an index.
            .astype({selected_var: str})
            .set_index(selected_var)
            .style
            # Additional styling calls can be chained here.
            # Index styling doesn't appear to work
            # .apply_index(
            #     lambda s: np.where(
            # ~s.isna(), 'background-color: blue;', 'background-color: blue;')
            # )
            # .highlight_max(axis='rows', color='lightgreen')
            )


def inject_datatable_header_style() -> None:
    with open(DATATABLE_HEADER_CSS) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


def create_chart(
        df: pd.DataFrame,
        survey_vars: SurveyVars,
        selected_var: str,
        groupby_var: str | None,
        plot_weighted: bool) -> alt.Chart:
    """Create an Altair chart object (bar chart).

    Args:
        df: Dataframe to plot.
        survey_vars: SurveyVars object, containing variable metadata.
        selected_var: The variable selected for display.
        groupby_var: The variable to groupby, if any.
        plot_weighted: Whether to plot weighted or unweighted counts.

    Returns:
        An Altair chart object.
    """
    # Hack to wrap long labels, for splitting in altair.
    # `wrap` breaks long str into a list of str, then stitch them back together
    # with LABEL_SPLIT delimiter. Altair then uses this delimiter to split
    # the str again using Vega expressions.
    # Without this, x tick labels get too long for some survey variables.
    df = df.assign(**{
        selected_var: lambda d: d[selected_var].cat.rename_categories(
            lambda e: LABEL_SPLIT.join(wrap(e, 20)))
    })

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


@st.cache_data
def load_config() -> dict:
    """Load the config file."""
    with CONFIG_FP.open() as f:
        return yaml.safe_load(f)


@st.cache_data
def load_data(fp: str | Path) -> pd.DataFrame:
    return pd.read_csv(fp)


# REFACTOR: currently uncached.
# Cacheing is possible when returned object is pickle serializable.
# Will need to investigate why SurveyVars is not picklable.
def load_survey_vars(fp: str | Path):
    return SurveyVars(fp)


def main(debug=False, log_file_path: str | None = None):
    if debug and log_file_path is None:
        raise ValueError('Must provide log file path if debug is True.')

    # Load configuation YAML file
    config = load_config()
    # Load main data and survey vars codebook info
    if config['data']['use_clps_compressed']:
        clps_df = load_data(config['data']['clps_compressed'])
    else:
        clps_df = load_data(config['data']['clps_file'])
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
    # Selector for valid skip handling
    valid_skip_handling = deploy_valid_skip_selectbox(
        svs, selected_var
    )
    # Selector for weighted/unweighted frequency
    plot_weighted = st.checkbox('Plot weighted frequency', value=True)
    disable_interactive = deploy_disable_interactivity_checkbox()
    # Spacing
    st.divider()
    make_gap(3)
    # END: DATA SELECTION WIDGETS AND UI

    # Transform data
    clps_df = transform_data(
        df=clps_df,
        survey_vars=svs,
        region=region,
        selected_var=selected_var,
        groupby_var=groupby_var,
        valid_skip_handling=valid_skip_handling,
        weighted=plot_weighted)

    # Prepare Altair chart
    chart_df = create_chart(
        clps_df, svs, selected_var, groupby_var, plot_weighted)
    # Display Chart
    st.altair_chart(
        chart_df if disable_interactive else chart_df.interactive(),
        use_container_width=True)
    # Spacing
    st.divider()
    make_gap(2)

    # Display datatable
    clps_df = style_datatable(clps_df, selected_var, plot_weighted)
    st.dataframe(
        clps_df,
        use_container_width=True,
        # Magic formula for getting the dataframe to not scroll
        # https://discuss.streamlit.io/t/st-dataframe-controlling-the-height-threshold-for-scolling/31769
        height=(clps_df.data.shape[0] + 1) * 35 + 3)

    # st.table(clps_df)

    # Logging for debugging
    if debug:
        import logging
        logging.basicConfig(filename=log_file_path, level=logging.DEBUG)
        alt.data_transformers.disable_max_rows()
        logging.debug(chart_df.to_json())

    # Return objects for testing
    return {'processed_data': clps_df, 'chart': chart_df,
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
