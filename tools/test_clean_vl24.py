import sys
from curl_cffi import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

r = requests.get('https://vieclam24h.vn/tim-kiem-viec-lam-nhanh?q=QC', impersonate='chrome120', timeout=12)
soup = BeautifulSoup(r.text, 'html.parser')

links = soup.find_all('a', href=True)
count = 0
for a in links:
    if not ('/quan-ly-' in a['href'] or '/khoa-hoc-' in a['href'] or '/san-xuat-' in a['href'] or 'id' in a['href']):
        continue
    h_tag = a.find(['h2', 'h3'])
    if h_tag:
        count += 1
        title = h_tag.text.strip()
        # Find all text elements inside a
        texts = [t.strip() for t in a.stripped_strings if t.strip()]
        # Company is usually the text right after title or containing CÔNG TY / CP / TNHH
        company = "N/A"
        salary = "Thương lượng"
        location = "TP.HCM"
        for t in texts:
            if any(k in t.lower() for k in ["công ty", "tnhh", "cổ phần", "cp "]):
                company = t
            elif "triệu" in t.lower() or "thỏa thuận" in t.lower():
                salary = t
            elif any(k in t.lower() for k in ["tp.hcm", "bình dương", "đồng nai", "thủ đức", "quận 9"]):
                location = t
        print(f"[{count}] Title: {title}")
        print(f"    Company: {company}")
        print(f"    Salary: {salary}")
        print(f"    Loc: {location}")
        print(f"    Link: https://vieclam24h.vn{a['href'] if not a['href'].startswith('http') else ''}")
        if count >= 6:
            break

