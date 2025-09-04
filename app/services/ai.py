from __future__ import annotations

import re, html, unicodedata
from typing import Iterable, List, Optional, Dict, Tuple
import requests
from bs4 import BeautifulSoup

def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")

def _norm_text(t: str) -> str:
    t = _nfkc(html.unescape(t or ""))
    t = t.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")  # – — − -> -
    t = t.replace("\u00A0", " ")
    t = re.sub(r"[•·●▪▶►]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def _fetch_full_text(url: Optional[str]) -> str:
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for bad in soup(["script", "style", "noscript", "svg"]):
            bad.decompose()
        cands = soup.find_all(["main", "article", "section", "div"], limit=80)
        chunks: List[str] = []
        for c in cands:
            txt = c.get_text(" ", strip=True)
            if txt and len(txt) > 200:
                chunks.append(txt)
        full = " ".join(sorted(chunks, key=len, reverse=True)[:3])
        return _norm_text(full)[:20000]
    except Exception:
        return ""

_YEAR_PATS: List[re.Pattern] = [
    # 5-10 years / 5 – 10 years / 5 to 10 years
    re.compile(r"\b(\d{1,2})\s*(?:-|–|to|or)\s*(\d{1,2})\s*(?:\+)?\s*(?:years?|yrs?)\b", re.I),
    # 3+ years / 3 years+
    re.compile(r"\b(\d{1,2})\s*(?:\+|plus)\s*(?:years?|yrs?)\b", re.I),
    re.compile(r"\b(\d{1,2})\s*(?:years?|yrs?)\s*\+\b", re.I),
    # at least / minimum / over / more than X years
    re.compile(r"\bat\s+least\s+(\d{1,2})\s*(?:years?|yrs?)\b", re.I),
    re.compile(r"\bmin(?:imum)?\s+(?:of\s+)?(\d{1,2})\s*(?:years?|yrs?)\b", re.I),
    re.compile(r"\b(?:over|more\s+than)\s+(\d{1,2})\s*(?:years?|yrs?)\b", re.I),
    # X years of ... experience / X years' experience / X years experience
    re.compile(r"\b(\d{1,2})\s*(?:years?|yrs?)\s+of\s+[^.\n]*?\bexperience\b", re.I),
    re.compile(r"\b(\d{1,2})\s*(?:years?|yrs?)\s*['’]?\s*experience\b", re.I),
    # Experience: 6+ Years
    re.compile(r"\bexperience\s*[:\-]\s*(\d{1,2})\s*(?:\+)?\s*(?:years?|yrs?)\b", re.I),
]

def _norm_years(m: re.Match) -> Optional[str]:
    g = m.groups()
    if len(g) >= 2 and all(x and x.isdigit() for x in g[:2]):
        return f"{int(g[0])}–{int(g[1])} years"
    text = m.group(0).lower()
    for x in g:
        if isinstance(x, str) and x.isdigit():
            n = int(x)
            if "plus" in text or "+" in text: return f"{n}+ years"
            if "at least" in text:           return f"at least {n} years"
            if "min" in text or "minimum" in text: return f"minimum {n} years"
            if "over" in text or "more than" in text: return f"over {n} years"
            return f"{n} years"
    return None

def _extract_years(text: str) -> str:
    if not text: return "not mentioned"
    seen, found = set(), []
    t = _norm_text(text)
    for pat in _YEAR_PATS:
        for m in pat.finditer(t):
            s = _norm_years(m)
            if s and s not in seen:
                seen.add(s); found.append((m.start(), s))
    if not found: return "not mentioned"
    found.sort(key=lambda x: x[0])
    for _, s in found:
        if "–" in s or "+" in s:
            return s
    return found[0][1]

_SAL_PATS: List[re.Pattern] = [
    re.compile(r"(?P<cur>\$|USD|CAD|C\$)?\s?(?P<a>\d{2,3}(?:,\d{3})?|(?:\d+)?k)\s*(?:-|–|to)\s*(?P<cur2>\$|USD|CAD|C\$)?\s?(?P<b>\d{2,3}(?:,\d{3})?|(?:\d+)?k)\s*(?P<unit>per\s*year|/year|year|annum|annual)?", re.I),
    re.compile(r"(?P<cur>\$|USD|CAD|C\$)?\s?(?P<a>\d{1,3})(?:\s*(?:-|–|to)\s*(?P<b>\d{1,3}))?\s*(?P<u>per\s*hour|/hour|hour|hr|/hr)\b", re.I),
    re.compile(r"(?P<cur>\$|USD|CAD|C\$)?\s?(?P<a>\d{2,3}(?:,\d{3})?|(?:\d+)?k)\s*(?P<unit>per\s*year|/year|year|annum|annual)\b", re.I),
]

def _fmt_money(tok: str) -> str:
    s = (tok or "").lower().replace(",", "").strip()
    if not s: return ""
    if s.endswith("k"):
        try:
            return f"{int(float(s[:-1]) * 1000):,}"
        except Exception:
            return tok
    return f"{int(s):,}" if s.isdigit() else tok

def _extract_salary(text: str) -> str:
    if not text: return "not mentioned"
    t = _norm_text(text)
    for pat in _SAL_PATS:
        m = pat.search(t)
        if not m: continue
        gd = m.groupdict()
        cur = gd.get("cur") or gd.get("cur2") or ""
        cur = {"USD": "$", "CAD": "CAD", "C$": "CAD"}.get(cur, cur or "")
        a = _fmt_money(gd.get("a"))
        b = _fmt_money(gd.get("b")) if gd.get("b") else None
        unit = (gd.get("unit") or gd.get("u") or "").lower()
        unit = "per hour" if ("hour" in unit or "hr" in unit) else ("per year" if any(x in unit for x in ["year","annum","annual"]) else "")
        core = f"{cur} {a} – {b}" if b else f"{cur} {a}"
        return f"{core.strip()} {unit}".strip()
    return "not mentioned"

_REMOTE_PH = [
    r"\bremote(-first)?\b", r"work\s+from\s+home", r"\bWFH\b", r"\banywhere\b",
    r"fully\s+remote", r"remote\s+within\s+canada", r"remote\s+across"
]
_HYBRID_PH = [
    r"\bhybrid\b", r"\b(\d|one|two|three)\s+(?:days?|d)/?\s*(?:in|at)\s+(?:the\s+)?office\b",
    r"partially\s+remote", r"split\s+time\s+between\s+home\s+and\s+office"
]
_ONSITE_PH = [
    r"\bon[\s-]?site\b", r"in[-\s]?person", r"\bin\s+office\b", r"must\s+be\s+on\s+site"
]

def _detect_type(text: str) -> str:
    if not text: return "not mentioned"
    t = _norm_text(text).lower()
    for p in _REMOTE_PH:
        if re.search(p, t): return "remote"
    for p in _HYBRID_PH:
        if re.search(p, t): return "hybrid"
    if any(re.search(p, t) for p in _ONSITE_PH):
        return "onsite"
    return "not mentioned"

_TECH_TERMS = [
    # languages
    "python","java","javascript","typescript","c#",".net",".net core","c++","go","golang","rust","ruby","php","kotlin","swift",
    # web/frontend
    "react","react native","vue","angular","next.js","nuxt","svelte","tailwind","webpack","babel","html","css","sass","less",
    # backend/frameworks
    "spring","spring boot","django","flask","fastapi","express","node.js","nodejs","graphql","rest","grpc","microservices",
    # data/storage
    "sql","mysql","postgresql","postgres","mariadb","oracle","mongodb","dynamodb","redis","elasticsearch","kafka","rabbitmq",
    "spark","hadoop","hive","airflow","snowflake","bigquery","redshift","databricks","power bi","tableau","pandas","numpy",
    # cloud/devops
    "aws","azure","gcp","docker","kubernetes","terraform","ansible","jenkins","github actions","gitlab ci","ci/cd","linux",
    # testing
    "pytest","junit","selenium","cypress","playwright","jest","mocha",
    # security
    "oauth","oidc","sso",
    # misc
    "jira","agile","scrum"
]

def _term_regex(term: str) -> re.Pattern:
    pat = re.escape(term)
    pat = pat.replace(r"\ ", r"[ \-_/]+")
    return re.compile(rf"(?<![A-Za-z0-9]){pat}(?![A-Za-z0-9])", re.I)

_TERM_PATS: List[Tuple[str, re.Pattern]] = [(t, _term_regex(t)) for t in _TECH_TERMS]

_EXPER_PH = re.compile(
    r"(?:experience\s+with|proficien(?:t|cy)\s+in|knowledge\s+of|familiar\s+with|hands[- ]on\s+with|expertise\s+in)\s+([A-Za-z0-9\.\+#/\- ]{2,80})",
    re.I
)

def _extract_skills(text: str, limit: int = 8) -> List[str]:
    if not text: return []
    t = _norm_text(text)
    hits: List[Tuple[int,str]] = []

    for term, pat in _TERM_PATS:
        for m in pat.finditer(t):
            hits.append((m.start(), term))

    for m in _EXPER_PH.finditer(t):
        frag = m.group(1)
        parts = re.split(r",|/| and |\bor\b|;", frag, flags=re.I)
        for p in parts:
            s = p.strip().lower()
            s = re.sub(r"\s{2,}", " ", s)
            if 2 <= len(s) <= 40 and re.search(r"[A-Za-z0-9]", s):
                hits.append((m.start(), s))

    seen, ordered = set(), []
    for _, s in sorted(hits, key=lambda x: x[0]):
        if s not in seen:
            seen.add(s); ordered.append(s)
        if len(ordered) >= limit: break
    return ordered[:limit]

def analyze(job_text: str, your_skills: Iterable[str], *, url: Optional[str] = None) -> dict:

    base = ""
    page_text = _fetch_full_text(url) if url else ""
    if page_text:
        base = page_text
    else:
        base = _norm_text(job_text)

    try:
        skills = _extract_skills(base, limit=8)
        years  = _extract_years(base)
        jobtype = _detect_type(base)
        salary = _extract_salary(base)
        return {
            "skills": skills,
            "years_experience_required": years,
            "type": jobtype,
            "salary": salary,
        }
    except Exception:
        return {
            "skills": [],
            "years_experience_required": "not mentioned",
            "type": "not mentioned",
            "salary": "not mentioned",
        }
