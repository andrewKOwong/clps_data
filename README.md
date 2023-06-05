# clps WORK-IN-PROGRESS

## Project Summary

## Instructions
### Description of Files

### Libraries Required TODO
This is a list of libraries required to run the dashboard app. It is not
rigourously tested for backwards-compatibility, and the app likely works with
older versions of these libraries.
- requirements.txt
- python >= 3.10.4
- pandas?
- pytest


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
- to run locally
- main app on cloud, provide link


### Running Tests
- In order to run tests, you must have `pytest` installed.
- Tests are located in the `tests` folder.
- Run `pytest` in the root folder to run all tests.
