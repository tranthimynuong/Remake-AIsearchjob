#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Multi-Platform Job Finder for Ho Chi Minh City

Platforms Scraped:
1. LinkedIn
2. Glassdoor
3. Indeed (Vietnam)
4. TopCV (Vietnam's #1 Job Portal for Intern & Fresher)

Expanded Role Categories:
1. QA / QC / Software Tester (Manual, Automation, API, Security)
2. Web & Frontend Developer (React, WordPress, HTML/CSS/JS)
3. Software Engineer & Backend (Java Spring Boot, Python, Full-stack)
4. UI / UX Design & Web Design (Figma, Wireframe, Behance)
5. IT Business Analyst (IT BA) & Product Analyst
6. Data Analyst & Data Engineer (SQL, Python, BI)
7. IT Support / Helpdesk & Technical Operations
"""

import os
import sys
import io
import re
import time
import random
import datetime
import urllib.request
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
import pandas as pd

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

CANDIDATE_SKILLS = {
    "qa_qc": [
        "test", "testing", "tester", "qa", "qc", "manual test", "test case", 
        "checklist", "postman", "api", "jira", "trello", "bug", "regression", "automation", "kiểm thử"
    ],
    "web_frontend": [
        "html", "css", "javascript", "typescript", "react", "vue", "frontend", 
        "front-end", "web", "wordpress", "tailwind", "bootstrap", "dom", "cms"
    ],
    "ui_ux_design": [
        "figma", "ui", "ux", "wireframe", "prototype", "design", "mockup", "behance", "user experience", "interface"
    ],
    "backend_data": [
        "python", "java", "spring", "sql", "postgresql", "mysql", "data", "etl", "rest", "backend", "fullstack"
    ],
    "ba_support": [
        "business analyst", "ba", "requirement", "srs", "support", "helpdesk", "operation", "phân tích nghiệp vụ", "scrum"
    ]
}

# Categorized Search Queries across major platforms
SEARCH_CATEGORIES = {
    "QA / QC / Testing": [
        "Tester Intern",
        "QA Intern",
        "QC Intern",
        "Automation Test Intern",
        "Thực tập sinh Tester"
    ],
    "Web & Frontend Developer": [
        "Web Developer Intern",
        "Frontend Intern",
        "React Intern",
        "WordPress Intern"
    ],
    "Software Engineer / Backend": [
        "Software Engineer Intern",
        "Fullstack Intern",
        "Python Intern",
        "Java Intern"
    ],
    "UI / UX Design & Web Design": [
        "UI UX Intern",
        "UI/UX Designer Intern",
        "Web Designer Intern",
        "Product Design Intern"
    ],
    "IT Business Analyst (BA)": [
        "IT Business Analyst Intern",
        "Business Analyst Intern",
        "IT BA Intern"
    ],
    "Data Analyst & Engineering": [
        "Data Analyst Intern",
        "Data Engineer Intern",
        "BI Intern"
    ],
    "IT Support & Technical Operation": [
        "IT Support Intern",
        "Helpdesk Intern",
        "IT Helpdesk Officer"
    ]
}

# TopCV specific queries (optimized for Vietnam market)
TOPCV_QUERIES = [
    ("thực tập sinh tester", "QA / QC / Testing"),
    ("thực tập sinh web", "Web & Frontend Developer"),
    ("thực tập sinh lập trình", "Software Engineer & Backend"),
    ("thực tập sinh ui ux", "UI / UX Design & Web Design"),
    ("thực tập sinh business analyst", "IT Business Analyst (BA)"),
    ("thực tập sinh data", "Data Analyst & Engineering"),
    ("thực tập sinh it support", "IT Support & Technical Operation")
]

def determine_category(title):
    t = title.lower()
    if any(k in t for k in ["test", "qa", "qc", "sdet", "kiem thu", "kiểm thử"]):
        return "QA / QC / Testing"
    if any(k in t for k in ["ui", "ux", "design", "figma"]):
        return "UI / UX Design & Web Design"
    if any(k in t for k in ["web", "front", "react", "wordpress"]):
        return "Web & Frontend Developer"
    if any(k in t for k in ["data", "analyst", "sql", "etl", "bi "]):
        return "Data Analyst & Engineering"
    if any(k in t for k in ["business analyst", "ba ", "srs", "nghiệp vụ"]):
        return "IT Business Analyst (BA)"
    if any(k in t for k in ["support", "helpdesk", "hệ thống", "system admin"]):
        return "IT Support & Technical Operation"
    return "Software Engineer & Backend"

def calculate_match_score(title, desc):
    """Calculate match score based on candidate competencies and title relevance"""
    text = f"{title} {desc}".lower()
    score = 55  # Base score for tech entry
    matched_skills = []

    # Check for intern / fresher keywords in title
    if any(k in title.lower() for k in ["intern", "thuc tap", "thực tập", "fresher", "trainee", "entry", "sinh vien"]):
        score += 15

    # Check for negative senior keywords
    if any(k in title.lower() for k in ["senior", "lead", "manager", "principal", "head", "director", "5+ year", "3+ year", "trưởng phòng"]):
        return 0, []

    for cat, skills in CANDIDATE_SKILLS.items():
        for skill in skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text):
                if skill not in matched_skills:
                    matched_skills.append(skill)
                    score += 3.5

    # Cap score at 98%
    score = min(int(score), 98)
    return score, matched_skills

def scrape_topcv(queries, max_items_per_query=8):
    """Direct scraper for TopCV Vietnam"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8'
    }

    for query_text, default_category in queries:
        try:
            encoded_query = urllib.parse.quote(query_text)
            url = f"https://www.topcv.vn/tim-viec-lam-moi-nhat?keyword={encoded_query}&city=2"
            req = urllib.request.Request(url, headers=headers)
            html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            cards = soup.select('.job-item-search-result, .job-item-2')
            count = 0
            for card in cards:
                if count >= max_items_per_query:
                    break
                title_el = card.select_one('.title a, h3 a')
                comp_el = card.select_one('.company a, .company-name')
                sal_el = card.select_one('.salary, .title-salary')

                if not title_el:
                    continue

                title = title_el.text.strip()
                link = title_el.get('href', '').strip()
                comp = comp_el.text.strip() if comp_el else "TopCV Employer"
                sal = sal_el.text.strip() if sal_el else "Thoả thuận"

                # Filter senior
                if any(k in title.lower() for k in ["senior", "lead", "manager", "trưởng phòng", "giám đốc"]):
                    continue

                # Filter non-IT titles
                non_tech = ["kinh doanh", "telesale", "bán hàng", "tour", "bảo hiểm", "bất động sản", "kế toán", "nhân sự", "sale", "marketing online"]
                if any(nt in title.lower() for nt in non_tech) and not any(it in title.lower() for it in ["it", "developer", "tester", "data", "ui", "ux"]):
                    continue

                score, matched = calculate_match_score(title, f"{title} {sal}")
                if score >= 50:
                    cat = determine_category(title)
                    results.append({
                        "category": cat,
                        "title": title,
                        "company": comp,
                        "location": "TP. Hồ Chí Minh",
                        "site": "TopCV",
                        "score": score,
                        "matched_skills": ", ".join(matched[:8]) if matched else "IT General",
                        "job_url": link,
                        "date_posted": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "description": f"Mức lương: {sal}. Vị trí đăng tuyển trên TopCV tại TP.HCM."
                    })
                    count += 1
            print(f"   [TopCV] '{query_text}' => Tim duoc {count} tin moi.")
            time.sleep(random.uniform(0.8, 1.5))
        except Exception as e:
            print(f"   [!] Loi TopCV query '{query_text}': {e}")
    return results

def run_job_search(results_per_query=5):
    print("=" * 80)
    print(">>> HE THONG QUET VIEC LAM MO RONG TOAN DIEN TAI TP. HO CHI MINH")
    print(">>> Nen tang: LinkedIn, Glassdoor, Indeed, TopCV")
    print(">>> Vi tri: QA/QC, Web Dev, Software Eng, UI/UX Design, IT BA, Data, IT Support")
    print(f">>> Thoi gian bat dau: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)

    all_jobs_list = []
    seen_ids = set()

    # Phase 1: TopCV
    print("\n[PHASE 1] Dang quet tu TopCV (Cong thong tin viec lam lon nhat Viet Nam)...")
    topcv_jobs = scrape_topcv(TOPCV_QUERIES, max_items_per_query=6)
    for j in topcv_jobs:
        key = f"{j['title'].lower()} - {j['company'].lower()}"
        if key not in seen_ids:
            seen_ids.add(key)
            all_jobs_list.append(j)

    # Phase 2: LinkedIn, Glassdoor, Indeed via Jobspy
    print("\n[PHASE 2] Dang quet tu LinkedIn, Glassdoor & Indeed...")
    site_list = ["linkedin", "glassdoor", "indeed"]

    for group_name, queries in SEARCH_CATEGORIES.items():
        print(f"\n---> Nhom: {group_name.upper()} ({len(queries)} tu khoa)")
        for query in queries:
            print(f"[+] Tim kiem: '{query}'...")
            try:
                time.sleep(random.uniform(1.2, 2.0))
                jobs_df = scrape_jobs(
                    site_name=site_list,
                    search_term=query,
                    location="Ho Chi Minh City, Vietnam",
                    results_wanted=results_per_query,
                    country_indeed='vietnam'
                )
                
                if jobs_df is not None and not jobs_df.empty:
                    valid_count = 0
                    for _, row in jobs_df.iterrows():
                        title = str(row.get('title', '')).strip()
                        company = str(row.get('company', '')).strip()
                        url = str(row.get('job_url', '')).strip()
                        desc = str(row.get('description', '')).strip()
                        location = str(row.get('location', 'Ho Chi Minh City')).strip()
                        site = str(row.get('site', 'LinkedIn')).strip()
                        date_posted = str(row.get('date_posted', '')).strip()

                        # Deduplicate
                        key = f"{title.lower()} - {company.lower()}"
                        if key in seen_ids or not url or not title:
                            continue
                        seen_ids.add(key)

                        score, matched = calculate_match_score(title, desc)
                        if score >= 50:
                            category = determine_category(title)
                            all_jobs_list.append({
                                "category": category,
                                "title": title,
                                "company": company,
                                "location": location,
                                "site": site,
                                "score": score,
                                "matched_skills": ", ".join(matched[:8]),
                                "job_url": url,
                                "date_posted": date_posted,
                                "description": desc[:300] + "..." if len(desc) > 300 else desc
                            })
                            valid_count += 1
                    print(f"   => Lay duoc {valid_count} vi tri hop le.")
                else:
                    print("   => Khong co tin dang moi.")
            except Exception as e:
                print(f"   [!] Thong bao query '{query}': {e}")

    if not all_jobs_list:
        print("\nKhong tim thay viec lam phu hop trong dot quet nay.")
        return

    # Convert to DataFrame and sort by score
    df = pd.DataFrame(all_jobs_list)
    df.sort_values(by="score", ascending=False, inplace=True)

    # Save to CSV
    csv_path = os.path.join(os.path.dirname(__file__), "..", "job_search_results.csv")
    csv_path = os.path.abspath(csv_path)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Da cap nhat toan bo vao file Excel/CSV: {csv_path}")

    # Generate Structured Markdown Report
    md_path = os.path.join(os.path.dirname(__file__), "..", "job_search_results.md")
    md_path = os.path.abspath(md_path)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 🎯 Danh Sách Việc Làm Mở Rộng Toàn Diện Tại TP. Hồ Chí Minh\n\n")
        f.write(f"*Cập nhật tự động lúc:* **{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}**  \n")
        f.write(f"*Tổng số việc làm chất lượng tìm thấy:* **{len(df)} việc làm**  \n")
        f.write(f"*Các nền tảng đã quét:* **LinkedIn, Glassdoor, Indeed, TopCV**  \n")
        f.write(f"*Các nhóm công việc được quét:*\n")
        f.write("- 🐞 **QA / QC / Testing** (Kiểm thử phần mềm, Automation, Manual, API)\n")
        f.write("- 💻 **Web & Frontend Developer** (React, WordPress, HTML/CSS/JS)\n")
        f.write("- ⚙️ **Software Engineer & Backend** (Java Spring Boot, Python, Fullstack)\n")
        f.write("- 🎨 **UI / UX Design & Web Design** (Figma, Prototype, Wireframe, Behance)\n")
        f.write("- 📊 **IT Business Analyst (BA)** (Phân tích nghiệp vụ, tài liệu SRS, User Story)\n")
        f.write("- 📈 **Data Analyst & BI** (SQL, Python, Báo cáo & Xử lý dữ liệu)\n")
        f.write("- 🛠️ **IT Support & Technical Operation** (Hỗ trợ kỹ thuật, Helpdesk, Hệ thống)\n\n")
        f.write("---\n\n")

        # Group by category
        categories = df['category'].unique()
        for cat in sorted(categories):
            cat_df = df[df['category'] == cat]
            f.write(f"## 📌 Nhóm: {cat} ({len(cat_df)} vị trí)\n\n")
            f.write("| Độ Phù Hợp | Vị Trí Tuyển Dụng | Công Ty | Nền Tảng | Kỹ Năng Match | Link Ứng Tuyển |\n")
            f.write("| :---: | :--- | :--- | :--- | :--- | :---: |\n")

            for _, row in cat_df.iterrows():
                score_badge = f"🔥 **{row['score']}%**" if row['score'] >= 75 else f"✨ {row['score']}%"
                link = f"[Ứng tuyển ngay]({row['job_url']})"
                matched = row['matched_skills'] if row['matched_skills'] else 'IT Profile'
                f.write(f"| {score_badge} | **{row['title']}** | {row['company']} | `{row['site']}` | `{matched}` | {link} |\n")

            f.write("\n\n")


    print(f"[OK] Da tao bao cao Markdown chi tiet tai: {md_path}")
    print(f"\n[HOAN TAT] Tong cong da tim thay {len(df)} vi tri phu hop!")

if __name__ == "__main__":
    run_job_search(results_per_query=5)
