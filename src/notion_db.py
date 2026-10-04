"""Notion 채용공고 DB에 공고를 넣고, 이미 있는 공고인지 확인하는 모듈.

필요한 환경변수 (GitHub Secrets에 저장)
  NOTION_TOKEN : Notion 연결(job-alert)의 API token
  NOTION_DB_ID : 채용공고 DB의 ID
"""

import os

import requests

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _text(value):
    """Notion의 텍스트 칸 형식으로 바꾼다. 값이 없으면 빈 칸."""
    return {"rich_text": [{"text": {"content": value[:2000]}}]} if value else {"rich_text": []}


def _date(value):
    """'2026-10-20' 같은 날짜 문자열을 Notion 날짜 칸 형식으로 바꾼다."""
    return {"date": {"start": value}} if value else {"date": None}


def _select(value):
    return {"select": {"name": value}} if value else {"select": None}


def job_exists(job_id):
    """공고ID 칸으로 검색해서 이미 들어간 공고면 True."""
    db_id = os.environ["NOTION_DB_ID"]
    body = {"filter": {"property": "공고ID", "rich_text": {"equals": job_id}}, "page_size": 1}
    r = requests.post(f"{API}/databases/{db_id}/query", headers=_headers(), json=body, timeout=30)
    r.raise_for_status()
    return len(r.json()["results"]) > 0


def add_job(job):
    """공고 하나를 DB에 새 행으로 넣는다.

    job 예시
      {
        "title": "정보보안 신입 채용", "company": "OO회사",
        "deadline": "2026-10-20", "start": "2026-10-01",
        "roles": ["정보보안"], "career": "신입", "region": "서울",
        "source": "사람인", "url": "https://...", "job_id": "saramin-123456",
      }
    """
    props = {
        "공고명": {"title": [{"text": {"content": job["title"][:2000]}}]},
        "회사": _text(job.get("company")),
        "마감일": _date(job.get("deadline")),
        "접수시작": _date(job.get("start")),
        "상태": _select("새 공고"),
        "직무": {"multi_select": [{"name": r} for r in job.get("roles", [])]},
        "경력": _select(job.get("career")),
        "지역": _text(job.get("region")),
        "출처": _select(job.get("source")),
        "링크": {"url": job.get("url") or None},
        "공고ID": _text(job["job_id"]),
    }
    body = {"parent": {"database_id": os.environ["NOTION_DB_ID"]}, "properties": props}
    r = requests.post(f"{API}/pages", headers=_headers(), json=body, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Notion 저장 실패 {r.status_code}: {r.text}")
    return r.json()["url"]
