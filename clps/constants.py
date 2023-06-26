# Var names that are often specifically called
# because they are special cases of some sort.
PROBCNTP_KEY = 'PROBCNTP'
PROBCNTP_AGGREGATE_CODE = '01 - 16'
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
SERPROBP_KEY = 'SERPROBP'
WEIGHT_KEY = 'WTPP'
VERDATE_KEY = 'VERDATE'
# Survey variables for grouping. Dict values are display names.
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
# Special values
VALID_SKIP = 'Valid skip'
YES = 'Yes'
NO = 'No'
NOT_STATED = 'Not stated'
