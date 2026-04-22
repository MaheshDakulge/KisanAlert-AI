import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

print("1. Getting initial page...")
r = s.get(url, verify=False)
soup = BeautifulSoup(r.text, "html.parser")

viewstate = soup.find(id="__VIEWSTATE")["value"]
viewstategenerator = soup.find(id="__VIEWSTATEGENERATOR")["value"]
eventvalidation = soup.find(id="__EVENTVALIDATION")["value"]

print("2. Setting filter parameters...")

# Usually:
# Maharashtra = MH
# Nanded = 

# Let's inspect the Commodity drop down values from agmarknet directly if we can't hardcode them, 
# But we can try to fetch them dynamically if we pass State='MH'.
data = {
    '__EVENTTARGET': 'ddlState',
    '__EVENTARGUMENT': '',
    '__VIEWSTATE': viewstate,
    '__VIEWSTATEGENERATOR': viewstategenerator,
    '__EVENTVALIDATION': eventvalidation,
    'ddlState': 'MH' 
}

r2 = s.post(url, data=data, verify=False)
soup2 = BeautifulSoup(r2.text, "html.parser")
print(soup2.find(id="ddlCommodity").prettify()[:200]) # just checking if it updated
