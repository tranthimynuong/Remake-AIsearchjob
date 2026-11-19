import requests
import json
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8'
}

# 1. CareerViet
print("--- TESTING CAREERVIET ---")
try:
    url_cv = "https://careerviet.vn/viec-lam/qc-k-vi.html"
    r = requests.get(url_cv, headers=headers, timeout=10)
    print("CV status:", r.status_code)
    soup = BeautifulSoup(r.text, 'html.parser')
    # search for class names containing job
    job_elements = soup.find_all(class_=lambda x: x and ('job-item' in x or 'job_item' in x or 'bx_item' in x or 'job-card' in x))
    print("CV job elements found:", len(job_elements))
    if not job_elements:
        # inspect any headings
        h2s = soup.find_all(['h2', 'h3'])
        print(f"CV h2/h3 count: {len(h2s)}")
        for h in h2s[:5]:
            print("  H:", h.text.strip())
    else:
        for item in job_elements[:3]:
            title_a = item.find('a', class_=lambda x: x and 'title' in x) or item.find('a')
            print("  Job:", title_a.text.strip() if title_a else "N/A", "->", title_a.get('href') if title_a else "")
except Exception as e:
    print("CV Error:", e)

# 2. Vieclam24h
print("\n--- TESTING VIECLAM24H ---")
try:
    url_vl = "https://vieclam24h.vn/tim-kiem-viec-lam-nhanh?q=QC"
    r = requests.get(url_vl, headers=headers, timeout=10)
    print("VL24 status:", r.status_code)
    soup = BeautifulSoup(r.text, 'html.parser')
    # Check next data
    next_script = soup.find('script', id='__NEXT_DATA__')
    if next_script and next_script.string:
        print("VL24 has __NEXT_DATA__! Parsing JSON...")
        data = json.loads(next_script.string)
        jobs = data.get('props', {}).get('pageProps', {}).get('jobs', []) or data.get('props', {}).get('pageProps', {}).get('initialState', {}).get('jobs', {}).get('data', [])
        print("VL24 jobs in NEXT_DATA:", len(jobs))
        if jobs:
            print("Sample job title:", jobs[0].get('title') or jobs[0].get('job_title'))
    else:
        print("VL24 no __NEXT_DATA__ directly, checking links...")
except Exception as e:
    print("VL24 Error:", e)

# 3. VietnamWorks
print("\n--- TESTING VIETNAMWORKS ---")
try:
    url_vnw = "https://ms.vietnamworks.com/job-search/v1.0/search"
    # VietnamWorks uses Algolia / search API or web query
    payload = {
        "userId": 0,
        "query": "QC",
        "filter": [],
        "ranges": [],
        "order": [],
        "hitsPerPage": 5,
        "page": 0
    }
    r = requests.post(url_vnw, json=payload, headers={**headers, 'Content-Type': 'application/json'}, timeout=10)
    print("VNW status:", r.status_code)
    if r.status_code == 200:
        res = r.json()
        print("VNW keys:", list(res.keys()))
        data = res.get('data', [])
        print("VNW jobs count:", len(data))
        if data:
            print("VNW job 1:", data[0].get('jobTitle'), "|", data[0].get('companyName'))
except Exception as e:
    print("VNW Error:", e)

