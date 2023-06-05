# clps WORK-IN-PROGRESS

## Project Summary

## Instructions
### Description of Files

### Libraries Required
- requirements.txt


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
