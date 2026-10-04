"""모든 출처에서 공고를 모아, Notion DB에 없는 것만 새로 넣는다. GitHub Actions가 하루 두 번 실행.

환경변수
  NOTION_TOKEN, NOTION_DB_ID : Notion 연결 (필수)
  SARAMIN_KEY                : 없으면 사람인은 건너뜀
  LOOKBACK_HOURS             : 몇 시간 전 공고까지 볼지 (기본 36)
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.notion_db import add_job, job_exists  # noqa: E402
from src.sources import saramin  # noqa: E402

# (이름, 모듈, 필요한 키) — 출처를 늘릴 땐 여기에 한 줄 추가
SOURCES = [
    ("사람인", saramin, "SARAMIN_KEY"),
]


def main():
    lookback = int(os.environ.get("LOOKBACK_HOURS") or 36)
    added, skipped = 0, 0
    lines = []

    for name, module, key in SOURCES:
        if not os.environ.get(key):
            print(f"[{name}] {key}가 아직 없어서 건너뜀")
            continue
        for job in module.fetch_jobs(lookback):
            if job_exists(job["job_id"]):
                skipped += 1
                continue
            add_job(job)
            added += 1
            lines.append(f"- {job['company']} | {job['title']} | 마감 {job['deadline'] or '상시/채용시'}")
            time.sleep(0.4)   # Notion은 초당 3번까지만 허용

    summary = f"새로 추가 {added}개, 이미 있던 공고 {skipped}개"
    print(summary)
    print("\n".join(lines))

    # GitHub Actions 실행 화면에 요약 표 남기기
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## 채용공고 수집 결과\n{summary}\n\n" + "\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
