#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Portal Job Scraper for Vietnam:
- VietnamWorks (vietnamworks.com)
- CareerViet (careerviet.vn)
- ViecLam24h (vieclam24h.vn)

Search preset for QA and QC jobs in southern Vietnam
- Role: QA / QC / Kiểm soát chất lượng / Quản lý chất lượng / Tester / KCS
- Location: TP.HCM (đặc biệt TP. Thủ Đức, Quận 9, Bình Thạnh) & Các KCN lân cận (Linh Trung 1-2, Sóng Thần, SHTP, Bình Chiểu, VSIP 1, Đồng An, Amata)
- Gender constraint: NỮ (hoặc Nam/Nữ, tuyệt đối loại bỏ các tin tuyển Nam / Chỉ tuyển Nam).
"""

import argparse
import sys
from pathlib import Path
import re
import time
import json
import urllib.parse
from bs4 import BeautifulSoup

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests
try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = requests

# Exclude any explicit male requirements
MALE_PATTERNS = [
    r'\bnam\b', r'\(nam\)', r'\(nam,', r'nam,', r'nam\)', r'chỉ tuyển nam', r'yêu cầu nam',
    r'ưu tiên nam', r'giới tính nam', r'nam giới', r'khuân vác nặng', r'bốc xếp', r'nam đi ca'
]

BOTH_GENDER_PATTERNS = [
    "nam/nữ", "nam / nữ", "nam hoặc nữ", "nam hay nữ", "nam & nữ", "nam và nữ", "nam, nữ", "nam,nữ", "nam-nữ"
]

SENIOR_EXCLUSIONS = [
    "trưởng phòng", "giám đốc", "trưởng bộ phận", "director", "manager", "head of",
    "5 năm kinh nghiệm", "4 năm kinh nghiệm", "7 năm kinh nghiệm", "10 năm kinh nghiệm"
]

NORTH_CENTRAL_EXCLUSIONS = [
    "hà nội", "hanoi", "hải phòng", "đà nẵng", "bắc ninh", "vĩnh phúc", "hà tĩnh",
    "hưng yên", "hải dương", "thái nguyên", "quảng ninh", "thanh hóa", "nghệ an", "huế", "bình định"
]

def is_female_friendly(title, desc=""):
    combined = f"{title} {desc}".lower()
    
    # Check if both genders accepted
    for both in BOTH_GENDER_PATTERNS:
        if both in combined:
            return True

    # If explicitly male
    for pat in MALE_PATTERNS:
        if re.search(pat, combined):
            return False

    return True

def is_junior_friendly(title, desc=""):
    t = title.lower()
    for excl in SENIOR_EXCLUSIONS:
        if excl in t:
            return False
    return True

def is_target_location(location_str, full_text=""):
    loc = f"{location_str} {full_text}".lower()
    # Check exclusions
    for nc in NORTH_CENTRAL_EXCLUSIONS:
        if nc in loc:
            return False
    # Check target southern areas
    target_locs = [
        "hồ chí minh", "tp.hcm", "hcm", "thủ đức", "thu duc", "quận 9", "quận 2", "bình thạnh",
        "bình dương", "dĩ an", "thuận an", "sóng thần", "linh trung", "bình chiểu", "đồng nai",
        "biên hòa", "amata", "vsip", "đồng an", "cát lái", "kcn", "kcx"
    ]
    return any(k in loc for k in target_locs)

def calculate_relevance(title, company, location, desc=""):
    t_lower = title.lower()
    loc_lower = location.lower()
    desc_lower = desc.lower()
    score = 65

    # QA/QC roles
    if any(k in t_lower for k in ["qc", "qa", "kiểm soát chất lượng", "quản lý chất lượng", "kcs", "tester"]):
        score += 15
    if any(k in t_lower for k in ["fresher", "thực tập", "intern", "học việc", "mới ra trường", "nhân viên", "staff"]):
        score += 10
    if "ưu tiên nữ" in t_lower or "ưu tiên nữ" in desc_lower or "nữ" in t_lower:
        score += 10
    if "bao bì" in t_lower or "bao bì" in desc_lower:
        score += 8

    # Industrial parks near Thu Duc
    if any(k in loc_lower for k in ["thủ đức", "quận 9", "linh trung", "sóng thần", "dĩ an", "bình chiểu", "shtp"]):
        score += 15
    elif any(k in loc_lower for k in ["thuận an", "vsip", "bình dương", "quận 2", "bình thạnh"]):
        score += 10
    elif any(k in loc_lower for k in ["hồ chí minh", "hcm", "tp.hcm", "đồng nai", "biên hòa", "amata"]):
        score += 6

    return min(score, 99)

# 1. CAREERVIET SCRAPER
def scrape_careerviet(keyword="qc", max_pages=3):
    print(f"\n[1/3] Quét CareerViet (careerviet.vn) với từ khóa '{keyword}'...")
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8'
    }

    for page in range(1, max_pages + 1):
        try:
            url = f"https://careerviet.vn/viec-lam/{urllib.parse.quote(keyword)}-k-trang-{page}-vi.html"
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.select('.job-item')
            if not cards:
                break

            for c in cards:
                t_el = c.select_one('.job-title') or c.select_one('.title a') or c.select_one('h2 a') or c.select_one('h3 a')
                comp_el = c.select_one('.company-name')
                loc_el = c.select_one('.location')
                sal_el = c.select_one('.salary')

                if not t_el:
                    continue

                title = t_el.text.strip()
                company = comp_el.text.strip() if comp_el else "Doanh nghiệp trên CareerViet"
                location = loc_el.text.strip() if loc_el else "TP.HCM"
                salary = sal_el.text.strip() if sal_el else "Thỏa thuận"
                link = t_el.get('href', '')
                if link and not link.startswith('http'):
                    link = 'https://careerviet.vn' + link

                if not is_female_friendly(title):
                    continue
                if not is_junior_friendly(title):
                    continue
                if not is_target_location(location):
                    continue

                score = calculate_relevance(title, company, location)
                results.append({
                    "portal": "CareerViet",
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "url": link,
                    "score": score
                })
            time.sleep(1)
        except Exception as e:
            print(f"   [!] Lỗi CareerViet trang {page}: {e}")
    print(f"   => Tìm được {len(results)} tin phù hợp trên CareerViet.")
    return results

# 2. VIETNAMWORKS SCRAPER
def scrape_vietnamworks(keywords=["QC", "Kiểm soát chất lượng", "QA"]):
    print(f"\n[2/3] Quét VietnamWorks (vietnamworks.com)...")
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    }
    url_vnw = 'https://ms.vietnamworks.com/job-search/v1.0/search'
    seen_urls = set()

    for kw in keywords:
        try:
            payload = {
                'userId': 0,
                'query': kw,
                'filter': [],
                'ranges': [],
                'order': [],
                'hitsPerPage': 25,
                'page': 0
            }
            r = requests.post(url_vnw, json=payload, headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json().get('data', [])
                for job in data:
                    title = job.get('jobTitle', '')
                    company = job.get('companyName', '')
                    salary = job.get('prettySalary', 'Thương lượng')
                    address = job.get('address', '') or ""
                    locations = job.get('locations', []) or []
                    loc_str = address if address else ", ".join([str(l) for l in locations])

                    link = job.get('jobUrl', '')
                    if link and not link.startswith('http'):
                        link = 'https://www.vietnamworks.com/' + link
                    
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    full_desc = f"{address} {loc_str}"
                    if not is_target_location(loc_str, address):
                        continue
                    if not is_female_friendly(title, full_desc):
                        continue
                    if not is_junior_friendly(title, full_desc):
                        continue

                    score = calculate_relevance(title, company, loc_str)
                    results.append({
                        "portal": "VietnamWorks",
                        "title": title,
                        "company": company,
                        "location": address if address else "TP. Hồ Chí Minh / Bình Dương",
                        "salary": salary,
                        "url": link,
                        "score": score
                    })
            time.sleep(1)
        except Exception as e:
            print(f"   [!] Lỗi VietnamWorks kw '{kw}': {e}")
    print(f"   => Tìm được {len(results)} tin phù hợp trên VietnamWorks.")
    return results

# 3. VIECLAM24H SCRAPER
def scrape_vieclam24h(keywords=["QC", "kiểm soát chất lượng", "QA"]):
    print(f"\n[3/3] Quét Việc Làm 24h (vieclam24h.vn)...")
    results = []
    seen_urls = set()

    for kw in keywords:
        try:
            url = f"https://vieclam24h.vn/tim-kiem-viec-lam-nhanh?q={urllib.parse.quote(kw)}"
            r = curl_requests.get(url, impersonate='chrome120', timeout=15)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')

            links = soup.find_all('a', href=True)
            for a in links:
                href = a['href']
                if not ('/quan-ly-' in href or '/khoa-hoc-' in href or '/san-xuat-' in href or 'id' in href):
                    continue
                
                h_tag = a.find(['h2', 'h3'])
                if not h_tag:
                    continue
                
                title = h_tag.text.strip()
                if title.startswith('Tin ưu tiên') or title.startswith('HOT'):
                    title = re.sub(r'^(Tin ưu tiên|HOT)+', '', title).strip()

                texts = [t.strip() for t in a.stripped_strings if t.strip()]
                company = "Doanh nghiệp Việc Làm 24h"
                salary = "Thương lượng"
                location = "TP.HCM"

                for t in texts:
                    if any(k in t.lower() for k in ["công ty", "tnhh", "cổ phần", "cp "]):
                        company = t
                    elif "triệu" in t.lower() or "thỏa thuận" in t.lower():
                        salary = t
                    elif any(k in t.lower() for k in ["tp.hcm", "bình dương", "đồng nai", "thủ đức", "quận 9"]):
                        location = t

                link = href
                if not link.startswith('http'):
                    link = 'https://vieclam24h.vn' + link

                if link in seen_urls:
                    continue
                seen_urls.add(link)

                full_context = " ".join(texts)
                if not is_female_friendly(title, full_context):
                    continue
                if not is_junior_friendly(title, full_context):
                    continue
                if not is_target_location(location, full_context):
                    continue

                score = calculate_relevance(title, company, location, full_context)
                results.append({
                    "portal": "Việc Làm 24h",
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "url": link,
                    "score": score
                })
            time.sleep(1)
        except Exception as e:
            print(f"   [!] Lỗi Việc Làm 24h kw '{kw}': {e}")
    print(f"   => Tìm được {len(results)} tin phù hợp trên Việc Làm 24h.")
    return results

def collect_jobs(portals):
    jobs = {}
    for name, scrape in portals:
        print(f"Đang quét {name}...")
        for job in scrape():
            key = (job["title"].strip().casefold(), job["company"].strip().casefold())
            previous = jobs.get(key)
            if previous is None or job["score"] > previous["score"]:
                jobs[key] = job
    return sorted(jobs.values(), key=lambda job: job["score"], reverse=True)


def main(argv=None):
    portals = {
        "careerviet": (
            "CareerViet",
            lambda: scrape_careerviet("qc", max_pages=3)
            + scrape_careerviet("kiem-soat-chat-luong", max_pages=2),
        ),
        "vietnamworks": ("VietnamWorks", scrape_vietnamworks),
        "vieclam24h": ("Việc Làm 24h", scrape_vieclam24h),
    }
    parser = argparse.ArgumentParser(description="Thu thập tin tuyển dụng QA/QC.")
    parser.add_argument(
        "--portal", choices=portals, help="Chỉ quét một nguồn. Mặc định quét tất cả."
    )
    args = parser.parse_args(argv)
    selected = [portals[args.portal]] if args.portal else list(portals.values())
    all_jobs = collect_jobs(selected)
    source_names = ", ".join(name for name, _ in selected)

    print(f"\n=======================================================")
    print(f"TỔNG CỘNG LỌC ĐƯỢC: {len(all_jobs)} VIỆC PHÙ HỢP CHO NỮ")
    print(f"Khu vực: TP.HCM (Thủ Đức, Q9...) & KCN lân cận (Sóng Thần, Linh Trung, VSIP, Amata)")
    print(f"=======================================================")

    # Output to markdown file
    out_dir = Path(__file__).resolve().parents[1] / "documents" / "postings"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_name = "multi_portal_female_qc_jobs"
    if args.portal:
        output_name += f"_{args.portal}"
    md_path = out_dir / f"{output_name}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Danh Sách Việc Làm QA/QC Phù Hợp Cho Nữ (TP.HCM & Các KCN Lân Cận)\n\n")
        f.write(f"*Nguồn đã quét: {source_names} - Ngày {time.strftime('%d/%m/%Y')}*\n\n")
        f.write("> **Bộ lọc áp dụng:**\n")
        f.write("> 1. **Giới tính:** Tuyển Nữ hoặc Nam/Nữ (Đã loại trừ 100% các tin yêu cầu chỉ tuyển Nam / việc nặng nhọc).\n")
        f.write("> 2. **Khu vực:** TP.HCM (đặc biệt TP. Thủ Đức, Q.9), Bình Dương (Dĩ An, Thuận An, Sóng Thần, VSIP), Đồng Nai (Biên Hòa, Amata).\n")
        f.write("> 3. **Cấp bậc:** Thực tập sinh, Fresher, Nhân viên, Chuyên viên (Đã lọc bỏ cấp Trưởng phòng/Giám đốc).\n\n")
        f.write("| STT | Điểm Phù Hợp | Vị Trí Tuyển Dụng | Công Ty | Khu Vực / KCN | Mức Lương | Nguồn | Link Ứng Tuyển |\n")
        f.write("|:---:|:---:|---|---|---|---|:---:|:---:|\n")
        for i, j in enumerate(all_jobs, 1):
            f.write(f"| {i} | **{j['score']}%** | **{j['title']}** | {j['company']} | {j['location']} | {j['salary']} | {j['portal']} | [Xem & Ứng Tuyển]({j['url']}) |\n")

    json_path = out_dir / f"{output_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)

    print(f"Đã cập nhật bảng danh sách tại: {md_path}")

if __name__ == "__main__":
    main()
