# Canadian Legal Problems Survey: Data Dashboard

## Project Summary
The [Canadian Legal Problems
Survey](https://www.justice.gc.ca/eng/rp-pr/jr/survey-enquete.html) (CLPS) is a national survey of Canadians' experiences with the justice system, most recently conducted by Statisics Canada in 2021.
Data from the survey is provided by Statistics Canada via a [Public Use Microdata
File](https://www150.statcan.gc.ca/n1/pub/35-25-0002/352500022022001-eng.htm) (PUMF).

This project contains code for a dashboard app
for exploring data from the main CLPS dataset.

### Links
- [Dashboard](
  https://clps-data.streamlit.app/
) on Streamlit Community Cloud.
- [Code repo](https://github.com/andrewKOwong/clps_data) (i.e. this repo)
- [Blogpost](
  http://mixedconclusions.com/blog/clps/
) describing this project.
- See [here](
  https://github.com/andrewKOwong/clps_survey_vars
)
for a related project
where I extract data from the CLPS codebook PDF.
- To learn more about this dataset and how it can benefit your organization,
please contact [Parallax Information Consulting](
  https://parallaxinformation.com/
).

## Instructions
### Description of Files
- `.streamlit/` contains `config.toml`, used to configure the app for Streamlit
    Community Cloud.
- `clps/` contains the main libraries.
- `clps_docs` contains the original CLPS documentation as provided by StatsCan.
- `data/` contains the compressed CLPS data, and the extracted survey variable
metadata from the codebook.
- `tests/` contains `pytest` tests.
- `text/` contains text/markdown files used in the app.
- `.gitignore` is used to ignore files from git.
- `app.py` is the main app file.
- `config.yaml` is provides configuration info for the app. It is used to hold
- `README.md` is this file.
  file paths for data files, text files, and any other inputs.
- `requirements.txt` is used by Streamlit Community Cloud (SCC) to load dependencies
  for the app.
  It is not a full list of dependencies required to run the app, as SCC already
  loads a number of modules (e.g `pandas`, `altair`).
- `validate_data.py` is a script to validate the data.




### Libraries Required
This is a list of libraries required to run the dashboard app. It is not
rigourously tested for backwards-compatibility, and the app likely works with
older versions of these libraries.
- `python >= 3.10.4`
- `pandas`
- `pytest`
- `streamlit`
- `altair`
- `yaml`


A `requirements.txt` file is provided, but it is for installing app
dependencies onto Streamlit Community Cloud, and does not list a full set of dependencies.


### Data Validation Script
A validation script `validate_data.py` is available to check the following
basic assumptions about the data:
1) PUMFID -> every row is unique.
2) Unique values of every survey variable with answers matches the answer
    codes in the codebook. This excludes PUMFID and WTPP.
3) Frequencies and weighted frequencies match the codebook.
4) No null values.

To run the data validation script,
run the following command in the top directory:

```bash
python validate_data.py 2> validate_test_err.txt
```
Piping the `stderr` stream to a file is optional, but convenient for inspecting
errors collected by Pandera.
Input/output file paths can be specified, see `--help` for details.

### Running the Dashboard App
- To run locally, run the following command in the top directory:
```bash
streamlit run app.py
```

- The app is also [located on Streamlit Community
  Cloud](https://clps-data.streamlit.app/). This cloud version runs from the
  `main` branch of this repo.


### Running Tests
- In order to run tests, you must have `pytest` installed.
- Tests are located in the `tests` folder.
- Run `pytest` in the root folder to run all tests.
