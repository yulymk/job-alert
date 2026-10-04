# job-alert

사람인·고용24 API로 채용공고를 모아 Notion에 정리하고 마감 알림을 보내는 개인 구직용 프로그램.

## 구조
- `src/notion_db.py` : Notion 채용공고 DB에 공고 저장, 중복 확인
- `scripts/test_notion.py` : Notion 연결 테스트
- `.github/workflows/` : GitHub Actions 예약 실행 설정

## 필요한 GitHub Secrets
| 이름 | 내용 |
|---|---|
| `NOTION_TOKEN` | Notion 연결(job-alert)의 API token |
| `NOTION_DB_ID` | 채용공고 DB ID |
| `SARAMIN_KEY` | 사람인 API access-key (발급 후 추가) |

채용정보 출처: 사람인
