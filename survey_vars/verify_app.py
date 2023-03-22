import streamlit as st
import json
import argparse
from enum import Enum


class Heading(Enum):
    """Enum for heading strs for display."""
    variable_name = 'Variable Name'
    length = 'Length'
    position = 'Position'
    question_name = 'Question Name'
    concept = 'Concept'
    question_text = 'Question Text'
    universe = 'Universe'
    note = 'Note'
    source = 'Source'
    answer_categories = 'Answer Categories'
    code = 'Code'
    frequency = 'Frequency'
    weighted_frequency = 'Weighted Frequency'
    percent = '%'
    total = 'Total'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("survey_vars", type=str, default="{}")
    args = parser.parse_args()
    with open(args.survey_vars) as f:
        data = json.load(f)

    # Convenience variable for Heading enum
    H = Heading
    # data is a list of dicts, each dict representing a survey variable
    for q in data:
        # Top line metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                H.variable_name.value, q[H.variable_name.name])
        with col2:
            st.metric(H.length.value, q[H.length.name])
        with col3:
            st.metric(H.position.value, q[H.position.name])
        # Vertically stacked metadata
        for h in [
                H.question_name, H.concept, H.question_text,
                H.universe, H.note, H.source]:
            col1, col2 = st.columns([1, 5], gap='medium')
            col1.markdown(f"**{h.value}**")
            col2.write(r'\-\-\-' if q[h.name] == '' else q[h.name])
        # Horizontal divider
        st.markdown("---")
