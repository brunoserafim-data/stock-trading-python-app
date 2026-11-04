import requests
import csv
import os
import time
from dotenv import load_dotenv
load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

LIMIT = 1000

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
        print(f'waiting 15 seconds before requesting next page to avoid hitting the rate limit...')
        time.sleep(15)  # Sleep for 15 seconds to avoid hitting the rate limit

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
            break  # Exit the loop if there are no more results

    if not tickers:
        print('No tickers found.')
        return

    example_ticket = {'ticker': 'GMAY', 
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
                    'last_updated_utc': '2026-11-04T07:08:56.810423726Z'}

    fieldnames = list(example_ticket.keys())
    output_csv = 'tickers.csv'
    with open (output_csv, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for t in tickers:
            row = {key: t.get(key, '') for key in fieldnames}
            writer.writerow(row)
    print(f'Wrote {len(tickers)} rows to {output_csv }')

if __name__ == "__main__":
    run_stock_job()
