"""
LinkedIn Job Scanner — Generic Engine
Searches LinkedIn for any job title/location and scores results.
"""

import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,he;q=0.8",
}

COMPANY_BONUS = {
    "microsoft": 5, "google": 5, "amazon": 5, "meta": 4, "apple": 5,
    "oracle": 5, "sap": 5, "salesforce": 5, "servicenow": 5, "workday": 5,
    "ibm": 4, "intel": 5, "cisco": 4, "nvidia": 5,
    "check point": 5, "nice": 4, "amdocs": 5, "monday.com": 5,
    "wix": 4, "payoneer": 4, "fiverr": 3, "papaya": 4,
    "deloitte": 4, "kpmg": 3, "pwc": 3, "accenture": 4, "ey": 3,
    "one1": 5, "priority": 4,
}

STOP_WORDS = {
    "and", "the", "for", "with", "from", "that", "this", "have", "been",
    "will", "are", "was", "were", "has", "had", "not", "but", "you", "your",
    "our", "its", "all", "can", "more", "into", "than", "their", "they",
    "which", "who", "also", "any", "may", "each", "such", "both", "very",
    "over", "after", "while", "about", "what", "when", "some", "new", "work",
    "job", "role", "position", "team", "company", "including", "required",
    "ability", "skills", "experience", "years", "strong", "excellent",
    "של", "על", "עם", "אל", "את", "הם", "הן", "הוא", "היא", "אנו", "כל",
    "לא", "אם", "כי", "גם", "עד", "רק", "עוד", "יש", "היה", "זה", "זאת",
}


def extract_resume_keywords(resume_text: str) -> dict:
    """Extract weighted keywords from pasted resume text."""
    if not resume_text or len(resume_text.strip()) < 30:
        return {}
    words = re.findall(r"[a-zA-Zא-ת]{3,}", resume_text.lower())
    freq: dict = {}
    for w in words:
        if w not in STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1
    kw = {}
    for w, count in freq.items():
        if count >= 3:
            kw[w] = min(6 + count, 14)
        elif count == 2:
            kw[w] = 6
        elif len(w) >= 6:
            kw[w] = 4
    return kw


def build_search_variants(job_title: str) -> list[str]:
    base = job_title.strip()
    variants = [base]
    lower = base.lower()
    if "manager" in lower and "senior" not in lower:
        variants.append(f"Senior {base}")
    if "director" not in lower and "manager" in lower:
        variants.append(base.replace("Manager", "Director").replace("manager", "Director"))
    if len(variants) < 3:
        variants.append(f"{base} Israel")
    return variants[:3]


def build_score_keywords(job_title: str) -> dict:
    """Generate scoring keywords from the job title."""
    words = re.findall(r"[a-zA-Zא-ת]+", job_title.lower())
    kw = {}
    for w in words:
        if len(w) > 3:
            kw[w] = 10
    # Universal high-value terms
    kw.update({
        "erp": 9, "oracle": 9, "sap": 7, "salesforce": 6,
        "enterprise": 6, "digital transformation": 7,
        "implementation": 7, "project management": 5,
        "stakeholder": 4, "vendor": 4, "integration": 5,
        "global": 4, "budget": 4, "roadmap": 4,
    })
    return kw


def _parse_applicants(text: str) -> int:
    text = text.lower()
    m = re.search(r"([\d,]+)\+?\s*applicant", text)
    if m:
        return int(m.group(1).replace(",", ""))
    if "over 200" in text: return 201
    if "first 25"  in text: return 12
    if "first 10"  in text: return 5
    return -1


def _trim(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0] + "…"


def fetch_job_ids(keywords: str, location: str) -> list[str]:
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    try:
        r = requests.get(url, params={"keywords": keywords, "location": location,
                                       "f_TP": "1,2,3,4", "start": 0},
                         headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        ids = []
        for card in soup.find_all("li"):
            tag = card.find("div", {"data-entity-urn": True})
            if tag:
                ids.append(tag["data-entity-urn"].split(":")[-1])
            else:
                a = card.find("a", href=True)
                if a:
                    m = re.search(r"/jobs/view/(\d+)", a["href"])
                    if m: ids.append(m.group(1))
        return ids[:25]
    except Exception:
        return []


def fetch_job_detail(job_id: str) -> dict:
    try:
        r = requests.get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}",
                         headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")

        title     = soup.find("h2", {"class": lambda c: c and "top-card-layout__title" in c})
        comp_link = soup.find("a",  {"class": lambda c: c and "topcard__org-name" in c})
        location  = soup.find("span", {"class": lambda c: c and "topcard__flavor--bullet" in c})
        desc_div  = soup.find("div", {"class": lambda c: c and "show-more-less-html__markup" in c})
        date_span = soup.find("span", {"class": lambda c: c and "posted-time" in c})

        comp_href   = comp_link["href"] if comp_link and comp_link.has_attr("href") else ""
        company_url = re.sub(r"\?.*", "", comp_href).rstrip("/")
        full_desc   = desc_div.get_text(" ", strip=True) if desc_div else ""

        criteria: dict = {}
        for item in soup.find_all("li", {"class": lambda c: c and "description__job-criteria-item" in c}):
            h = item.find("h3"); v = item.find("span")
            if h and v:
                criteria[h.get_text(strip=True).lower()] = v.get_text(strip=True)

        applicants_raw = ""
        for cls in ["num-applicants__caption", "jobs-unified-top-card__applicant-count"]:
            el = soup.find(attrs={"class": lambda c: c and cls in c})
            if el: applicants_raw = el.get_text(strip=True); break
        if not applicants_raw:
            for el in soup.find_all(string=re.compile(r"applicant", re.I)):
                t = str(el).strip()
                if len(t) < 80: applicants_raw = t; break

        date_text   = date_span.get_text(strip=True) if date_span else ""
        days_posted = -1
        dm = re.search(r"(\d+)\s+(hour|day|week|month)", date_text.lower())
        if dm:
            n, unit = int(dm.group(1)), dm.group(2)
            days_posted = n if unit=="day" else (n*7 if unit=="week" else (n*30 if unit=="month" else 0))

        return {
            "job_id":          job_id,
            "title":           title.get_text(strip=True) if title else "",
            "company":         comp_link.get_text(strip=True) if comp_link else "",
            "company_url":     company_url,
            "location":        location.get_text(strip=True) if location else "",
            "description":     full_desc,
            "desc_summary":    _trim(re.sub(r"\s+", " ", full_desc), 380),
            "date_posted":     date_text,
            "job_url":         f"https://www.linkedin.com/jobs/view/{job_id}",
            "applicants_raw":  applicants_raw,
            "applicants_n":    _parse_applicants(applicants_raw),
            "easy_apply":      bool(soup.find(string=re.compile(r"easy apply", re.I))),
            "days_posted":     days_posted,
            "seniority":       criteria.get("seniority level", ""),
            "employment_type": criteria.get("employment type", ""),
            "industries":      criteria.get("industries", ""),
        }
    except Exception:
        return {}


def fetch_company_about(company_url: str) -> str:
    if not company_url: return ""
    try:
        r = requests.get(company_url + "/about/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "lxml")
        for tag in ["p", "div", "span"]:
            for el in soup.find_all(tag):
                t = el.get_text(" ", strip=True)
                if 80 < len(t) < 800:
                    return _trim(t, 300)
    except Exception:
        pass
    return ""


def score_job(job: dict, score_kw: dict, resume_kw: dict | None = None) -> int:
    title = job.get("title", "").lower()
    desc  = job.get("description", "").lower()
    comp  = job.get("company", "").lower()
    loc   = job.get("location", "").lower()

    s = 0
    for kw, pts in score_kw.items():
        if kw in title: s += pts * 2
        elif kw in desc: s += pts

    if resume_kw:
        for kw, pts in resume_kw.items():
            if kw in title: s += pts * 2
            elif kw in desc: s += pts

    for comp_name, pts in COMPANY_BONUS.items():
        if comp_name in comp: s += pts

    il = ["israel", "tel aviv", "herzliya", "raanana", "haifa",
          "netanya", "petah tikva", "rishon", "rehovot"]
    s += 15 if any(x in loc for x in il) else (10 if "remote" in loc else 0)

    return min(s, 100)


def run_scan(job_title: str, location: str, log_fn=None, resume_text: str = "") -> list[dict]:
    def log(msg):
        if log_fn: log_fn(msg)

    variants  = build_search_variants(job_title)
    score_kw  = build_score_keywords(job_title)
    resume_kw = extract_resume_keywords(resume_text)
    if resume_kw:
        log(f"📄 רזומה נטענה — {len(resume_kw)} מילות מפתח זוהו")

    seen, all_ids = set(), []
    for variant in variants:
        log(f"🔍 מחפש: '{variant}' @ {location}")
        ids = fetch_job_ids(variant, location)
        for jid in ids:
            if jid not in seen:
                seen.add(jid); all_ids.append(jid)
        time.sleep(1.2)

    log(f"\n📦 נמצאו {len(all_ids)} משרות ייחודיות — שולף פרטים...")
    seen_comp: dict = {}
    jobs = []

    for i, jid in enumerate(all_ids):
        if i % 5 == 0 and i > 0: time.sleep(2)
        d = fetch_job_detail(jid)
        if not d or not d.get("title"):
            time.sleep(0.4); continue

        cu = d.get("company_url", "")
        if cu not in seen_comp:
            seen_comp[cu] = fetch_company_about(cu)
            time.sleep(0.7)
        d["company_about"] = seen_comp.get(cu, "")
        d["score"] = score_job(d, score_kw, resume_kw or None)
        jobs.append(d)
        log(f"  [{i+1}/{len(all_ids)}] {d['title']} @ {d['company']}")

    jobs.sort(key=lambda x: x["score"], reverse=True)
    log(f"\n✅ סיום — {len(jobs)} משרות, "
        f"{len([j for j in jobs if j['score'] >= 70])} עם התאמה גבוהה")
    return jobs
