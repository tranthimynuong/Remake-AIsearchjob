import sys
from curl_cffi import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

r = requests.get('https://vieclam24h.vn/tim-kiem-viec-lam-nhanh?q=QC', impersonate='chrome120', timeout=10)
soup = BeautifulSoup(r.text, 'html.parser')

print("Page title:", soup.title.text if soup.title else "No title")

# Check all links
links = soup.find_all('a', href=True)
job_links = []
for a in links:
    href = a['href']
    if any(k in href for k in ['/viec-lam/', '-id', '.html']) and len(a.text.strip()) > 5:
        job_links.append((a.text.strip(), href))

print("Total job-like links:", len(job_links))
for title, href in job_links[:10]:
    print(f"Title: {title} -> {href}")

