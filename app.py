import pandas as pd
from pathlib import Path
from textwrap import wrap
import streamlit as st
import altair as alt
import yaml
from clps.constants.special_vars_names import ID_KEY, WEIGHT_KEY, REGION_KEY
from clps.constants.special_vars_names import GROUPBY_VARS
from clps.constants.special_vars_names import VALID_SKIP
import clps.survey_vars_utils as svu
from clps.survey_vars_utils import SurveyVars
import clps.transform as tfm
from importlib import reload
reload(svu)
reload(tfm)

CONFIG_FP = Path('config.yaml')

LABEL_SPLIT = '----'

Y_FREQ_AXIS_LABEL = 'Count'
Y_WT_FREQ_AXIS_LABEL = 'Weighted Count'

TEXT_FP = Path('text')
TEXT_INTRO_FP = TEXT_FP / 'intro.md'
# These are survey variables that shouldn't be displayed
NON_SELECTABLE = [ID_KEY, WEIGHT_KEY]


def create_sidebar(intro_fp: str | Path) -> None:
    if isinstance(intro_fp, str):
        intro_fp = Path(intro_fp)
    st.sidebar.markdown(TEXT_INTRO_FP.read_text(),
                        unsafe_allow_html=True)


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


def select_region(survey_vars: SurveyVars) -> int:
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


def filter_by_region(df: pd.DataFrame, region: int | None) -> pd.DataFrame:
    """Filter a dataframe by a region code.

    Args:
        df: Dataframe to filter. Region column must be ints.
        region: Region code to filter by. If `None`, no filtering is done.

    Returns:
        Filtered dataframe.
    """
    if region is not None:
        df = df[df[REGION_KEY] == region].copy()
    return df


def filter_by_selected_and_groupby(
        df: pd.DataFrame,
        selected_var: str,
        groupby_var: str | None) -> pd.DataFrame:
    """Filter for the selected variable of interest, the groupby variable, and
    the respondent weights.

    Args:
        df: Dataframe with survey variables.
        selected_var: Name of the survey variable to filter for.
        groupby_var: Name of the groupby variable to filter for.
    """
    if groupby_var is None:
        df = df[[selected_var, WEIGHT_KEY]]
    else:
        df = df[[selected_var, groupby_var, WEIGHT_KEY]]
    return df


def create_ordered_dtype(s: pd.Series) -> pd.CategoricalDtype:
    """From an integer-containing column, create an ordered categorical dtype.

    Args:
        s: Series corresponding to a survey variable, with integer codes.

    Returns:
        Ordered categorical dtype, with categories in ascending integer order.
        """
    return pd.CategoricalDtype(
        categories=s.sort_values().unique(),
        ordered=True)


def order_and_convert_code(
        s: pd.Series,
        survey_vars: SurveyVars) -> pd.Series:
    """Converts a series of codes to text labels, as ordered categorical.

    Used as a helper func for `convert_to_categorical`.

    Args:
        s: Series corresponding to a survey variable, with integer codes.
        survey_vars: SurveyVars object, with survey variable metadata.

    Returns:
        Series with text labels as an ordered categorical. Order is determined
        by the order of the integers, which corresponds to the order found
        in the survey variable metadata.
    """
    # Change ints to ordered categorical to preserve order,
    # then convert to text labels.
    # Mapping automatically converts categorical info.
    return (s
            .astype(create_ordered_dtype(s))
            .cat.rename_categories(
                survey_vars[s.name].lookup_answer))


def convert_to_categorical(
        df: pd.DataFrame,
        svs: SurveyVars,
        selected_var: str,
        groupby_var: str | None):
    """Converted survey variable columns to ordered categorical dtype.

    Args:
        df: Dataframe with survey variable columns. These columns are still in
            integer code form.
        svs: SurveyVars object, with survey variable metadata.
        selected_var: Name of the survey variable column to convert.
        groupby_var: Name of the groupby column to convert, if any.

    Returns:
        Dataframe with survey variable columns converted to ordered categorical
        dtype, as text labels. Order is determined by the integer order, which
        corresponds to the order found in the survey variable metadata.
    """
    df = df.assign(**{
        selected_var: lambda d: (
            order_and_convert_code(d[selected_var], svs))})
    if groupby_var is not None:
        df = df.assign(**{
            groupby_var: lambda d: (
                order_and_convert_code(d[groupby_var], svs))})
    return df


def deploy_valid_skip_checkbox(
        df: pd.DataFrame,
        selected_var: str,
        skip_container: st.delta_generator.DeltaGenerator) -> bool | None:
    """Deploy checkbox to remove valid skips from the data.

    Args:
        df: Dataframe with survey variable columns, converted to str ordered
        categorical dtype.
        selected_var: Name of the survey variable column of interest.
        skip_container: Pre-existing container to hold the checkbox, i.e.
            from `st.container()`.

    Returns:
       If the dataframe contains valid skips, returns the checkbox value.
       Otherwise, returns `None`.
    """
    if VALID_SKIP in df[selected_var].cat.categories:
        with skip_container:
            return st.checkbox('Remove valid skips', value=True)
    else:
        return None


def filter_valid_skips(
        df: pd.DataFrame,
        selected_var: str,
        remove_valid_skips: bool) -> pd.DataFrame:
    """Filter out valid skips from the data.

    If remove_valid_skips is `False` or `None`, this filter does nothing.

    Args:
        df: Dataframe with survey variable columns, converted to str ordered
        categorical dtype.
        selected_var: Name of the survey variable column of interest.
        remove_valid_skips: Whether to remove valid skips from the data.

    Returns:
    """
    if remove_valid_skips:
        df = df.query(f"{selected_var} != '{VALID_SKIP}'")
        df = df.assign(**{
            selected_var:
                lambda d: d[selected_var].cat.remove_unused_categories()
        })
    return df


def process_data(
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
    create_sidebar(config['text']['intro_file'])
    # Choose a variable for display
    selected_var = select_var(df, svs, NON_SELECTABLE)
    # Choose region to filter
    region = select_region(svs)
    # Choose variable for bar chart groupings
    groupby_var = select_groupby_var(selected_var)
    # Selector for weighted/unweighted frequency
    plot_weighted = st.checkbox('Plot weighted frequency', value=True)
    # Space for valid skip removal container.
    skip_container = st.container()
    # Spacing
    st.divider()
    make_gap(3)
    # END: DATA SELECTION WIDGETS AND UI

    # BEGIN: DATA TRANSFORMATIONS
    # Filter region rows
    df = filter_by_region(df, region)
    # Filter survey var columns
    df = filter_by_selected_and_groupby(df, selected_var, groupby_var)

    df = convert_to_categorical(df, svs, selected_var, groupby_var)

    # Check if data contains "Valid skip" codes.
    # If so, add checkbox to give the option to remove them.
    remove_valid_skips = deploy_valid_skip_checkbox(
        df, selected_var, skip_container
    )

    # Remove valid skips if checkbox is checked. Note, if there are no
    # valid skips, remove_valid_skips will be None.
    df = filter_valid_skips(df, selected_var, remove_valid_skips)
    # END: DATA TRANSFORMATIONS

    # TODO Testing data tables
    # Need to do counts, or not counts.
    # Groupbys or not groupbys.
    df = df.copy()

    df = process_data(df, selected_var, groupby_var, plot_weighted)
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
