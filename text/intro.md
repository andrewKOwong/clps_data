
<style>
    .list-block> * {
        margin-bottom: 0;
    }
    .list-block {
        margin-bottom: 1rem;
    }
</style>

# CLPS Data Explorer

The [Canadian Legal Problems Survey
(CLPS)](https://www.justice.gc.ca/eng/rp-pr/jr/survey-enquete.html)
is a national survey of Canadians' experiences with the justice
system, most recently conducted by Statisics Canada in 2021.

The original data is provided by StatsCan via a
[Public Use Microdata
File](https://www150.statcan.gc.ca/n1/pub/35-25-0002/352500022022001-eng.htm).
Information about definitions and methodology
can be found in the materials included with the microdata download.


<div class="list-block">
See also:

- A <a href="https://mixedconclusions.com/blog/clps/">technical blogpost</a>
about this app's development
- <a href="https://github.com/andrewKOwong/clps_data">Github code repo</a>
- <a href="https://clps-survey-variables.streamlit.app/">Auxiliary app for browsing the CLPS codebook</a>
</div>

For more information about this data and how it can help your organization,
please contact [Parallax Information Consulting](
    https://parallaxinformation.com/
).

---

<div class="list-block">
This app displays plots for each survey variable of the data:

 - Select a **survey variable** from the dropdown (type to search).
 - Optionally:
    - Filter by **region**.
    - Group by a **demographic variable**.
</div>


Counts are **weighted** to represent the entire
population of Canada. Uncheck the box for actual survey respondent counts.

Some survey questions are not presented to respondents
based on their answers to previous questions.
These are called **"Valid skips"**.
Choose whether to recode these as a 'No' response,
remove them from the plot, or leave them as in the original data
(i.e. a separate category).


<div class="list-block">
Chart Instructions:

- Drag to pan, scroll to zoom.
- Click on the options menu (upper-right corner) to **download** the chart.
</div>