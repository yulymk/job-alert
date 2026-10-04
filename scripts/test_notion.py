"""Notion 연결 테스트: 테스트 공고 한 건을 넣어 본다.

GitHub Actions의 'Notion 연결 테스트'에서 실행한다.
성공하면 채용공고 DB에 [테스트] 행이 하나 생긴다. 확인 후 지워도 된다.
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.notion_db import add_job, job_exists  # noqa: E402


def main():
    for key in ("NOTION_TOKEN", "NOTION_DB_ID"):
        if not os.environ.get(key):
            sys.exit(f"{key} 값이 없습니다. GitHub Secrets 이름을 확인하세요.")

    today = datetime.date.today()
    job_id = f"test-{today.isoformat()}"
    if job_exists(job_id):
        print(f"오늘 테스트 공고({job_id})가 이미 있습니다. 조회까지 정상입니다.")
        return

    url = add_job({
        "title": "[테스트] job-alert 연결 확인",
        "company": "job-alert",
        "deadline": (today + datetime.timedelta(days=7)).isoformat(),
        "start": today.isoformat(),
        "roles": ["정보보안"],
        "career": "신입",
        "region": "서울",
        "source": "사람인",
        "url": "https://github.com/yulymk/job-alert",
        "job_id": job_id,
    })
    print(f"성공: 테스트 공고를 넣었습니다. {url}")


if __name__ == "__main__":
    main()
