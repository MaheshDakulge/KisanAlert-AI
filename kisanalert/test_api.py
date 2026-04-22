from dotenv import load_dotenv
import os, requests
load_dotenv()
key = os.getenv('DATAGOV_API_KEY')
url = 'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070'

# Find Turmeric with all possible names, and Soyabean in Maharashtra specifically
for comm in ['Turmeric', 'Haldi', 'Turmeric (Raw)', 'Dry Turmeric']:
    params = {'api-key': key, 'format': 'json', 'limit': '2', 'filters[commodity]': comm}
    r = requests.get(url, params=params, timeout=10)
    d = r.json()
    total = d.get('total', 0)
    print(comm + ': ' + str(total))
    for rec in d.get('records', [])[:1]:
        print('  ' + str(rec.get('state')) + ' | price=' + str(rec.get('modal_price')) + ' | date=' + str(rec.get('arrival_date')))

# Soyabean in Maharashtra
params = {'api-key': key, 'format': 'json', 'limit': '5', 'filters[commodity]': 'Soyabean', 'filters[state]': 'Maharashtra'}
r = requests.get(url, params=params, timeout=10)
d = r.json()
print('Soyabean Maharashtra: ' + str(d.get('total')))
for rec in d.get('records', [])[:3]:
    print('  ' + str(rec.get('district')) + ' | price=' + str(rec.get('modal_price')) + ' | date=' + str(rec.get('arrival_date')))
