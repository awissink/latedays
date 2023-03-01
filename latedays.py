import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# TODO: Change deadline string and filenames of CSVs
DEADLINE_ET_STRING = '2023-02-20-23:59:59' # Assignment deadline in ET (Format: year-month-date-hour:minute:second)

CW_CSV_FILENAME = 'courseworks.csv'
GS_CSV_FILENAME = 'gradescope.csv'
CODIO_CSV_FILENAME = 'codio.csv'
OUTPUT_CSV_FILENAME = 'hw1&2_final_late_days.csv' # Bookkeeping CSV file
COURSEWORKS_IMPORT_FILENAME = 'courseworks_import.csv' # Courseworks import CSV file

WRIT_OVERRIDES_DICT = {} # Add key=uni & value=waived late hours
PROG_OVERRIDES_DICT = {} # Add key=uni & value=waived late hours

GRACE_PERIOD_HOURS = 1  # Number of late hours we give away for free

# TODO: Confirm that column names in CSVs have not changed
CW_UNI = 'SIS User ID' # Column name: column of student unis
CW_NAMES = 'Student' # Column name: column of student names
CW_LATE_DAYS = 'Late Days Remaining (1021574)'

GS_UNI = 'SID'  # Column name: unis
GS_SUBMIT_STATUS = 'Status' # Column name: ungraded/graded or missing
GS_LATENESS = 'Lateness (H:M:S)'

CODIO_FIRSTNAME = 'first name'  # Column name: usually contains mostly unis
CODIO_EMAIL = 'email'
CODIO_SUBMIT_TIME = 'completed date' # Column name: submission date & time (in UTC)
CODIO_SUBMIT_STATUS = 'completed' # Column name: TRUE or FALSE

DIVIDER_STRING = '======================================================================================================================='
CODIO_SUBMIT_TIMEZONE = pytz.timezone('UTC') # Timezone of codio submission timestamp
DEADLINE_TIMEZONE = pytz.timezone('US/Eastern') # Timezone of DEADLINE_ET_STRING
DEADLINE_ET_wGPH = DEADLINE_TIMEZONE.localize( datetime.strptime(DEADLINE_ET_STRING, "%Y-%m-%d-%H:%M:%S") + timedelta(hours=GRACE_PERIOD_HOURS) ) # Extract datetime from string -> add grace period hours -> convert to ET

# Load CSVs to dataframes
def inputs(cw_csv_nameString, gs_csv_nameString, codio_csv_nameString):
    main_df_columns = [CW_UNI, CW_NAMES, CW_LATE_DAYS] # Columns needed from courseworks csv
    main_df = pd.read_csv(cw_csv_nameString, usecols=main_df_columns)[main_df_columns] # Parse csv columns to df (usecols=only grab the rows we want, set column order for naming)//set column order: https://stackoverflow.com/questions/40024406/keeping-columns-in-the-specified-order-when-using-usecols-in-pandas-read-csv
    main_df.columns = ['uni', 'names', 'total_late_days'] # Set column name

    main_df = main_df.dropna(subset=['uni']) # Drop empty rows (fake student rows)

    # Set uni as index & record late hour overrides
    main_df = main_df.set_index('uni') # Set uni as index
    main_df['writ_overrides'] = main_df.index.to_series().map(WRIT_OVERRIDES_DICT) # Parse written hw overrides
    main_df['prog_overrides'] = main_df.index.to_series().map(PROG_OVERRIDES_DICT) # Parse programming hw overrides

    gs_df_columns = [GS_UNI, GS_LATENESS, GS_SUBMIT_STATUS] # Columns needed from gradescope csv
    gs_df = pd.read_csv(gs_csv_nameString, usecols=gs_df_columns)[gs_df_columns] # Parse csv columns to df 
    gs_df.columns = ['uni','writ_lateness','writ_submit_status'] # Name columns

    codio_df_columns = [CODIO_FIRSTNAME, CODIO_EMAIL, CODIO_SUBMIT_TIME, CODIO_SUBMIT_STATUS] # Columns needed from codio csv
    codio_df = pd.read_csv(codio_csv_nameString, usecols=codio_df_columns)[codio_df_columns] # Parse csv columns to df
    codio_df.columns = ['?uni?', 'email', 'prog_submit_time', 'prog_submit_status'] # Name columns

    return gs_df, codio_df, main_df

# WRITTEN LATE DAYS
def writ_latedays(main_df, gs_df):
    # Calculate late days
    gs_df['writ_late_days'] = pd.to_timedelta(gs_df['writ_lateness']) / pd.Timedelta('1 hour') # Convert lateness duration to int & round to hours
    gs_df['writ_late_days'] = gs_df['writ_late_days'].apply(np.floor)  # Round down
    gs_df['writ_late_days'].loc[ (0 < gs_df['writ_late_days']) & (gs_df['writ_late_days'] < GRACE_PERIOD_HOURS) ] = 0  # Apply grace period hours (case: latehours bn 0 and grace hours -> to avoid -ve arithmetic results below)
    gs_df['writ_late_days'].loc[ GRACE_PERIOD_HOURS <= gs_df['writ_late_days'] ] = (gs_df['writ_late_days'] - GRACE_PERIOD_HOURS) # Apply grace period hours (case: latehours > grace hours)
    gs_df['writ_late_days'] = gs_df['writ_late_days']//24 # Convert to late days
    
    # Pass Gradescope info to main_df
    gs_df = gs_df[gs_df['uni'].isin(main_df.index)] # Drop unenrolled students from gs_df (to avoid unenrolled students added to main_df as new rows)    //https://stackoverflow.com/questions/27965295/dropping-rows-from-dataframe-based-on-a-not-in-condition
    main_df = main_df.join( gs_df.set_index('uni') ) # Join gs_df columns (rows mapped to corresponding unis) https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.join.html
    main_df['writ_late_days'] = main_df[['writ_overrides','writ_late_days']].min(axis=1)  # Apply overrides     //https://stackoverflow.com/questions/33975128/pandas-get-the-row-wise-minimum-value-of-two-or-more-columns

    return main_df

# PROGRAMMING LATE DAYS
def prog_latedays(main_df, codio_df):
    # Calculate late days
    codio_df['prog_submit_time'] = pd.to_datetime(codio_df['prog_submit_time'], errors='coerce').apply(lambda x: x.tz_localize(CODIO_SUBMIT_TIMEZONE).tz_convert('US/Eastern'))  # Convert submit time to datetime -> convert from UTC to ET timezone
    codio_df['prog_lateness'] = pd.to_timedelta(codio_df['prog_submit_time'] - DEADLINE_ET_wGPH) # Find lateness
    codio_df['prog_lateness'].loc[ codio_df['prog_lateness'] <= timedelta(seconds=0) ] = str(timedelta(days=0, hours=0, minutes=0, seconds=0)) # Set timely submissions late hours to 0   //https://stackoverflow.com/questions/2591845/comparing-a-time-delta-in-python    //https://docs.python.org/3/library/datetime.html
    codio_df['prog_late_days'] = codio_df['prog_lateness'] / pd.Timedelta('1 hour') # Convert to int & round to hours
    codio_df['prog_late_days'] = codio_df['prog_late_days'].apply(np.ceil) # Round down
    codio_df['prog_late_days'] = codio_df['prog_late_days']//24 # Convert to late days

    # Extract uni (to map to main_df)
    codio_df['uni'] = codio_df.apply(lambda row: row['?uni?'].lower() if row['?uni?'] in main_df.index else row['email'].split('@')[0] if row['email'].split('@')[0] in main_df.index else np.NaN, axis=1)  #extract uni from either first_name or email & check if uni is in main_df AKA if the student is enrolled)
    print(DIVIDER_STRING, "\n[CHECK] prog_latedays(): unable to extract uni OR not enrolled?: \n", codio_df[codio_df['uni'].isna()]) #display rows with no uni (either unable to extract OR not enrolled)

    # Pass codio info to main_df
    main_df = main_df.join(codio_df.set_index('uni').drop(columns=['?uni?', 'email']))  #set uni as codio_df index -> drop uni & email column -> join with main_df
    main_df['prog_late_days'] = main_df[['prog_overrides','prog_late_days']].min(axis=1)  #apply overrides

    return main_df

# Output final updated total late days to a CSV for bookkeeping
def update_total_late_days(main_df):
    main_df['writ_late_days'].fillna(0, inplace=True) # NaN -> 0 for calculation
    main_df['prog_late_days'].fillna(0, inplace=True) # NaN -> 0 for calculation
    main_df['total_late_days'] -= (main_df['writ_late_days'] + main_df['prog_late_days']) # Find final total late days

    main_df.sort_values(by=['names']).to_csv(OUTPUT_CSV_FILENAME) # Sort by names

# Output students who used more than 3 late days
def get_exceed_3_days(main_df):
    print(DIVIDER_STRING, '\n[OUTPUT] writ late days > 3\n', main_df[main_df['writ_late_days'] > 3])
    print(DIVIDER_STRING, '\n[OUTPUT] prog late days > 3\n', main_df[main_df['prog_late_days'] > 3])

# Generate CSV to import to Courseworks
def generate_courseworks_csv(main_df):
    cw_df = pd.read_csv(CW_CSV_FILENAME)
    cw_df['Late Days Remaining (1021574)'] = cw_df['Student'].map(dict(zip(main_df['names'], main_df['total_late_days'])))
    cw_df.to_csv(COURSEWORKS_IMPORT_FILENAME, index=False)

def main():
    gs_df, codio_df, main_df = inputs(CW_CSV_FILENAME, GS_CSV_FILENAME, CODIO_CSV_FILENAME)
    main_df = writ_latedays(main_df, gs_df)
    main_df = prog_latedays(main_df, codio_df)

    main_df = main_df[['names', 'total_late_days', 'writ_lateness', 'writ_overrides', 'writ_submit_status', 'writ_late_days', 'prog_submit_time', 'prog_lateness', 'prog_overrides', 'prog_submit_status', 'prog_late_days']]    #reorder main_df columns
    update_total_late_days(main_df)
    generate_courseworks_csv(main_df)
    get_exceed_3_days(main_df)

if __name__ == "__main__":
    main()