"""사람인 채용공고 API에서 공고를 가져와 우리 DB 형식(add_job이 받는 dict)으로 바꾸는 모듈.

API 문서: https://oapi.saramin.co.kr/guide/job-search
필요한 환경변수: SARAMIN_KEY (사람인에서 발급받은 access-key)
"""

import html
import os
import re
from datetime import datetime, timedelta, timezone

import requests

API_URL = "https://oapi.saramin.co.kr/job-search"
KST = timezone(timedelta(hours=9))

# 검색 조건 (사람인 서버에서 1차로 거른다)
JOB_MID_IT = "2"                # 상위 직무: IT개발·데이터
LOCATIONS = "101000,102000"     # 1차 지역: 서울, 경기
PAGE_SIZE = 110                 # 한 번에 받을 수 있는 최대 개수
MAX_PAGES = 10                  # 혹시 모를 무한 반복 방지

# 직무 분류 (우리 쪽에서 2차로 거른다)
# 공고의 직무명·제목·키워드에 아래 단어가 있으면 그 직무로 분류.
# 어느 것에도 안 걸리면 버린다. 단어는 마음대로 더하고 빼도 된다.
ROLE_KEYWORDS = {
    "정보보안": ["보안", "취약점", "ISMS", "모의해킹", "침해", "관제", "CERT", "SOC", "Security"],
    "데이터": ["데이터", "빅데이터", "DBA", "ETL", "Data", "BI"],
    "AI": ["AI", "인공지능", "머신러닝", "딥러닝", "컴퓨터비전", "LLM", "자연어", "NLP", "MLOps"],
    "SW개발": ["백엔드", "프론트엔드", "풀스택", "웹개발", "앱개발", "서버개발", "소프트웨어", "SW", "Backend", "Frontend"],
}


def _contains(text, word):
    """영어 약어(AI, SW, BI 등)는 다른 단어 속에 묻힌 경우(MAIL의 AI)를 빼고 찾는다."""
    if re.fullmatch(r"[A-Za-z]+", word):
        return re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text, re.IGNORECASE) is not None
    return word in text


def classify_roles(text):
    return [role for role, words in ROLE_KEYWORDS.items() if any(_contains(text, w) for w in words)]


def classify_career(exp_name):
    """사람인 경력 표기를 우리 DB의 '신입' / '경력무관'으로. 경력직만 뽑는 공고는 None(버림)."""
    if "경력무관" in exp_name:
        return "경력무관"
    if "신입" in exp_name:          # '신입', '신입·경력' 모두 포함
        return "신입"
    return None


def _kst_date(timestamp):
    if not timestamp:
        return None
    return datetime.fromtimestamp(int(timestamp), KST).strftime("%Y-%m-%d")


def _region(loc_name):
    """'서울 &gt; 강남구,경기 &gt; 성남시' → '서울 강남구, 경기 성남시'"""
    parts = [p.replace(">", " ").split() for p in html.unescape(loc_name or "").split(",")]
    return ", ".join(" ".join(p) for p in parts if p)


def parse_job(raw):
    """사람인 공고 하나를 add_job 형식으로. 조건에 안 맞으면 None."""
    pos = raw.get("position", {})
    title = html.unescape(pos.get("title", ""))
    job_code_name = (pos.get("job-code") or {}).get("name", "")
    keyword = raw.get("keyword", "")

    roles = classify_roles(" ".join([title, job_code_name, keyword]))
    career = classify_career((pos.get("experience-level") or {}).get("name", ""))
    if not roles or not career:
        return None

    # 마감 방식: 1=접수마감일, 2=채용시 마감, 3=상시, 4=수시 → 날짜가 의미 있는 건 1뿐
    close_code = str((raw.get("close-type") or {}).get("code", ""))
    deadline = _kst_date(raw.get("expiration-timestamp")) if close_code == "1" else None

    return {
        "title": title,
        "company": html.unescape(raw.get("company", {}).get("detail", {}).get("name", "")),
        "deadline": deadline,
        "start": _kst_date(raw.get("opening-timestamp")),
        "roles": roles,
        "career": career,
        "region": _region((pos.get("location") or {}).get("name")),
        "source": "사람인",
        "url": raw.get("url"),
        "job_id": f"saramin-{raw['id']}",
    }


def fetch_raw(lookback_hours):
    """최근 lookback_hours 시간 안에 올라온 IT개발·데이터 / 서울·경기 공고를 전부 받아온다."""
    since = int((datetime.now(KST) - timedelta(hours=lookback_hours)).timestamp())
    params = {
        "access-key": os.environ["SARAMIN_KEY"],
        "job_mid_cd": JOB_MID_IT,
        "loc_mcd": LOCATIONS,
        "published_min": since,
        "sr": "directhire",          # 헤드헌팅 공고 제외
        "sort": "pd",                # 최신 등록순
        "count": PAGE_SIZE,
    }
    results = []
    for page in range(MAX_PAGES):
        r = requests.get(API_URL, params={**params, "start": page},
                         headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "jobs" not in data:       # 키 오류 등은 {"code":..., "message":...}로 온다
            raise RuntimeError(f"사람인 API 오류: {data}")
        jobs = data["jobs"].get("job", [])
        results.extend(jobs)
        if len(results) >= int(data["jobs"].get("total", 0)) or not jobs:
            break
    return results


def fetch_jobs(lookback_hours=36):
    """수집 스크립트가 부르는 함수. 조건에 맞는 공고만 add_job 형식으로 돌려준다."""
    raws = fetch_raw(lookback_hours)
    jobs = [j for j in (parse_job(r) for r in raws) if j]
    print(f"[사람인] 받은 공고 {len(raws)}개 → 조건 통과 {len(jobs)}개")
    return jobs
