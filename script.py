import requests
import csv
import os
from dotenv import load_dotenv
load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

LIMIT = 1000

url = f'https://api.massive.com/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}'
response = requests.get(url)
print(response.json())
tickers = []

data = response.json()
for ticker in data['results']:
    tickers.append(ticker)

while 'next_url' in data:
    print('requesting next page', data['next_url'])
    response = requests.get(data['next_url'] + f'&apiKey={POLYGON_API_KEY}')
    data = response.json()
    print(data)
    for ticker in data['results']:
        tickers.append(ticker)

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
print(f'Wrote {len(tickers)} tickers to {output_csv }')
