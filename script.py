import os
import csv
import time
import requests
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_AUTHENTICATOR = os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")

LIMIT = 1000

def load_to_snowflake(tickers, fieldnames):
    print("Connecting to Snowflake (browser window may open for SSO login)...")
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        authenticator=SNOWFLAKE_AUTHENTICATOR,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        role=SNOWFLAKE_ROLE
    )
    
    cursor = conn.cursor()
    try:
        # 1. Create table dynamically if it doesn't exist matching your fields
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS stock_tickets (
                ticker VARCHAR,
                name VARCHAR,
                market VARCHAR,
                locale VARCHAR,
                primary_exchange VARCHAR,
                type VARCHAR,
                active BOOLEAN,
                currency_name VARCHAR,
                cik INT,
                composite_figi VARCHAR,
                share_class_figi VARCHAR,
                last_updated_utc TIMESTAMP
            )
        """)
        
        # Clear old data on re-run (truncate)
        cursor.execute("TRUNCATE TABLE stock_tickets")

        print("Inserting records into Snowflake...")
        insert_sql = """
            INSERT INTO stock_tickets (
                ticker, name, market, locale, primary_exchange, type, 
                active, currency_name, cik, composite_figi, share_class_figi, last_updated_utc
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Prepare rows as tuples for bulk execution
        rows_to_insert = []
        for t in tickers:
            # Handle empty CIK values safely if they are missing or None
            cik_val = t.get('cik')
            try:
                cik_val = int(cik_val) if cik_val else None
            except (ValueError, TypeError):
                cik_val = None

            row = (
                t.get('ticker', ''),
                t.get('name', ''),
                t.get('market', ''),
                t.get('locale', ''),
                t.get('primary_exchange', ''),
                t.get('type', ''),
                t.get('active'),
                t.get('currency_name', ''),
                cik_val,
                t.get('composite_figi', ''),
                t.get('share_class_figi', ''),
                t.get('last_updated_utc', None)
            )
            rows_to_insert.append(row)

        # Execute bulk insert using executemany for optimal performance
        cursor.executemany(insert_sql, rows_to_insert)
        conn.commit()
        print(f"Successfully loaded {len(rows_to_insert)} rows into Snowflake table {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.STOCK_TICKERS.")

    finally:
        cursor.close()
        conn.close()

def run_stock_job():
    url = f'https://api.massive.com/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}'
    
    tickers = []
    print('Requesting first page...')
    response = requests.get(url)
    data = response.json()

    if data.get('status') == 'Error':
        print('Error:', data.get('error'))
        return

    if 'results' in data:
        for ticker in data['results']:
            tickers.append(ticker)

    while next_url := data.get('next_url'):
        print('Waiting 15 seconds before requesting next page to avoid hitting the rate limit...')
        time.sleep(15) 

        print('Requesting next page...', next_url)
        response = requests.get(next_url + f'&apiKey={POLYGON_API_KEY}')
        data = response.json()

        if data.get('status') == 'Error':
            print('API Error / Rate limit hit:', data.get('error'))
            break

        if 'results' in data:
            for ticker in data['results']:
                tickers.append(ticker)
        else:
            break 

    if not tickers:
        print('No tickers found.')
        return

    example_ticket = {
        'ticker': 'GMAY', 
        'name': 'FT Vest U.S. Equity Moderate Buffer ETF - May', 
        'market': 'stocks', 
        'locale': 'us', 
        'primary_exchange': 'BATS', 
        'type': 'ETF', 
        'active': True, 
        'currency_name': 'usd', 
        'cik': '0001667919', 
        'composite_figi': 'BBG01GN8WSR4', 
        'share_class_figi': 'BBG01GN8WTL8', 
        'last_updated_utc': '2026-11-04T07:08:56.810423726Z'
    }

    fieldnames = list(example_ticket.keys())
    output_csv = 'tickers.csv'
    
    # Keep local CSV output as a backup file
    with open(output_csv, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for t in tickers:
            row = {key: t.get(key, '') for key in fieldnames}
            writer.writerow(row)
    print(f'Wrote {len(tickers)} rows locally to {output_csv}')

    # Load data directly into Snowflake database
    load_to_snowflake(tickers, fieldnames)

if __name__ == "__main__":
    run_stock_job()