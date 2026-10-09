import pandas as pd
import sqlite3
import glob
import os

def format_time(time_series):
    # Format time series from numeric float (e.g. 1530.0) to timedelta
    # Fill NA with 0, convert to int, then to 4-char string (e.g., "1530")
    time_str = time_series.fillna(0).astype(int).astype(str).str.zfill(4)
    # Handle the '2400' midnight representation
    time_str = time_str.replace('2400', '0000')
    # Create timedelta
    return pd.to_timedelta(time_str.str[:2] + ':' + time_str.str[2:] + ':00', errors='coerce')

def main():
    print("Searching for dataset...")
    # Auto-detect CSV in the root folder
    csv_files = glob.glob('*.csv')
    if not csv_files:
        print("No CSV files found in the current directory.")
        return
    
    csv_file = csv_files[0]
    print(f"Loading data from {csv_file}...")
    
    # Read first row to detect columns
    sample = pd.read_csv(csv_file, nrows=0)
    columns = sample.columns.tolist()
    
    # Map standard BTS/Kaggle columns to our expected names if needed
    col_mapping = {
        'TailNum': 'Tail_Number',
        'Reporting_Airline': 'Carrier',
        'UniqueCarrier': 'Carrier',
        'Flight_Number_Reporting_Airline': 'Flight_Number',
        'DepDelayMinutes': 'Departure_Delay',
        'ArrDelayMinutes': 'Arrival_Delay',
        'DepDelay': 'Departure_Delay',
        'ArrDelay': 'Arrival_Delay'
    }
    
    usecols = []
    # Identify the actual columns to use
    expected = ['FlightDate', 'Tail_Number', 'TailNum', 'Reporting_Airline', 'UniqueCarrier', 'Carrier',
                'Flight_Number_Reporting_Airline', 'Flight_Number', 'Origin', 'Dest',
                'CRSDepTime', 'DepTime', 'CRSArrTime', 'ArrTime', 'Cancelled', 'Diverted']
    
    if 'DepDelayMinutes' in columns:
        expected.append('DepDelayMinutes')
    elif 'DepDelay' in columns:
        expected.append('DepDelay')
        
    if 'ArrDelayMinutes' in columns:
        expected.append('ArrDelayMinutes')
    elif 'ArrDelay' in columns:
        expected.append('ArrDelay')
    
    for c in columns:
        if c in expected:
            usecols.append(c)
            
    print(f"Reading columns: {usecols}")
    df = pd.read_csv(csv_file, usecols=usecols)
    
    # Rename columns to standard names
    df.rename(columns=col_mapping, inplace=True)
    
    print(f"Initial shape: {df.shape}")
    
    # Filter out cancelled and diverted flights
    if 'Cancelled' in df.columns:
        df = df[df['Cancelled'] == 0]
    if 'Diverted' in df.columns:
        df = df[df['Diverted'] == 0]
        
    # Drop rows with missing critical information
    critical_cols = ['Tail_Number', 'CRSDepTime', 'CRSArrTime', 'DepTime', 'ArrTime', 'FlightDate']
    # Check which critical columns actually exist in df
    available_critical = [c for c in critical_cols if c in df.columns]
    df.dropna(subset=available_critical, inplace=True)
    
    # Format FlightDate to datetime
    df['FlightDate'] = pd.to_datetime(df['FlightDate'])
    
    # Create valid timestamps for Scheduled and Actual times
    print("Formatting timestamps...")
    df['Scheduled_Departure'] = df['FlightDate'] + format_time(df['CRSDepTime'])
    df['Actual_Departure'] = df['FlightDate'] + format_time(df['DepTime'])
    
    # Scheduled Arrival
    df['Scheduled_Arrival'] = df['FlightDate'] + format_time(df['CRSArrTime'])
    # Adjust for overnight scheduled flights (arrival next day)
    mask_arr = df['CRSDepTime'] > df['CRSArrTime']
    df.loc[mask_arr, 'Scheduled_Arrival'] += pd.Timedelta(days=1)
    
    # Actual Arrival
    df['Actual_Arrival'] = df['FlightDate'] + format_time(df['ArrTime'])
    # Heuristic adjustment for actual arrival next day
    # E.g. dep 2300, arr 0100
    mask_act_arr = (df['CRSDepTime'] > df['CRSArrTime']) | (df['DepTime'] > df['ArrTime'])
    df.loc[mask_act_arr, 'Actual_Arrival'] += pd.Timedelta(days=1)
    
    # Compute Raw Turnaround Metrics where applicable (will also be done precisely via SQL)
    # Here we just compute basic scheduled duration
    df['Scheduled_Duration_Mins'] = (df['Scheduled_Arrival'] - df['Scheduled_Departure']).dt.total_seconds() / 60.0
    df['Actual_Duration_Mins'] = (df['Actual_Arrival'] - df['Actual_Departure']).dt.total_seconds() / 60.0

    # Ensure delays are numeric
    if 'Departure_Delay' not in df.columns:
        df['Departure_Delay'] = (df['Actual_Departure'] - df['Scheduled_Departure']).dt.total_seconds() / 60.0
    if 'Arrival_Delay' not in df.columns:
        df['Arrival_Delay'] = (df['Actual_Arrival'] - df['Scheduled_Arrival']).dt.total_seconds() / 60.0
        
    final_cols = [
        'FlightDate', 'Carrier', 'Tail_Number', 'Flight_Number', 'Origin', 'Dest',
        'Scheduled_Departure', 'Actual_Departure', 'Departure_Delay',
        'Scheduled_Arrival', 'Actual_Arrival', 'Arrival_Delay',
        'Scheduled_Duration_Mins', 'Actual_Duration_Mins'
    ]
    final_cols = [c for c in final_cols if c in df.columns]
    
    df = df[final_cols].copy()
    
    # Convert datetime to string for SQLite storage
    for col in ['Scheduled_Departure', 'Actual_Departure', 'Scheduled_Arrival', 'Actual_Arrival', 'FlightDate']:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    print(f"Data cleaned. Final shape: {df.shape}")
    
    # Load into SQLite database
    db_path = 'operations.db'
    print(f"Loading data into SQLite database: {db_path}...")
    conn = sqlite3.connect(db_path)
    
    # Enable WAL mode and performance pragmas
    conn.execute('PRAGMA journal_mode = WAL;')
    conn.execute('PRAGMA synchronous = NORMAL;')
    conn.execute('PRAGMA cache_size = -64000;')  # 64MB cache
    
    # Write to database (using chunksize if large, though to_sql handles reasonably well)
    df.to_sql('flight_operations', conn, if_exists='replace', index=False, chunksize=50000)
    
    # Create indexes to speed up SQL pipeline
    print("Creating database indexes...")
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tail_date ON flight_operations(Tail_Number, Scheduled_Departure)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_origin ON flight_operations(Origin)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_carrier ON flight_operations(Carrier)')
    
    conn.close()
    print("Data ingestion and database creation completed successfully.")

if __name__ == '__main__':
    import time
    t0 = time.time()
    main()
    print(f"Total pipeline elapsed time: {time.time() - t0:.2f} seconds")
