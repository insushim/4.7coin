# 🤖 QuantSage — AI Crypto Trader

> 프로덕션급 AI 코인 자동매매 시스템. 리스크 우선·설명가능·레짐 인식·앙상블·투명한 검증.

[![License](https://img.shields.io/badge/License-MIT-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)]()
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)]()
[![Status](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

---

## ⚠️ 필수 경고 (읽기 전 반드시)

- **수익 보장 없음**. 리테일 알고리즘 트레이더의 95%+가 손실을 봅니다.
- 이 시스템은 "**손실 최소화 + 검증된 자동화 + 철저한 리스크 관리**"로 수익 확률을 높일 뿐, 수익을 보장하지 않습니다.
- **첫 30일 Paper Trading 필수**. 실거래 금지.
- 초기 실거래 자본은 총 자산의 **1~5%** (절대 초과 금지).
- API 키는 **조회 + 주문만**, **출금 권한 절대 금지**.
- **레버리지 기본 금지** (현물만).
- 이 소프트웨어는 **본인 자산의 개인 자동매매 전용**. 타인 자금 운용·구독·광고는 허용하지 않습니다 (공무원 겸직 이슈 포함).

---

## ✨ 특징

| 원칙 | 구현 |
|------|------|
| **Risk-First** | Kelly 1/4, 8-Layer Guard, 다중 Kill-Switch, 변동성 타겟팅 |
| **Explainable** | 블랙박스 금지. 모든 주문에 "왜" 로그. SHAP 피처 중요도 |
| **Regime-Aware** | Bull/Bear/Range/HighVolChop 자동 구분 |
| **Ensemble** | 5개 독립 전략 투표 → 과반수 신호만 집행 |
| **Honest Backtest** | Walk-Forward + 슬리피지 + 수수료 + Deflated Sharpe |

---

## 🏗️ 기술 스택

**Backend**: Python 3.12, FastAPI, CCXT Pro, pyupbit, pandas-ta, vectorbt, XGBoost, PyTorch, SQLAlchemy + asyncpg, Redis, Celery, APScheduler, Pydantic v2, Anthropic Claude API, Loguru
**Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts, lightweight-charts, Zustand, TanStack Query
**Infra**: PostgreSQL 16 + TimescaleDB, Redis 7, Docker Compose, Traefik

---

## 🚀 빠른 시작

```bash
# 1) 클론
git clone https://github.com/insushim/4.7coin.git quantsage && cd quantsage

# 2) 환경 설정
cp .env.example .env
# .env 파일에 API 키 입력 (docs/API_KEYS_GUIDE.md 참고)

# MASTER_KEY 자동 생성
openssl rand -base64 32  # 값을 .env의 MASTER_KEY= 에 입력

# 3) Docker로 DB/Redis 기동
docker-compose up -d postgres redis

# 4) 백엔드 설치 및 실행
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python ../scripts/seed_historical.py --symbols KRW-BTC,KRW-ETH --days 365
uvicorn quantsage.main:app --reload

# 5) 프론트엔드 설치 및 실행
cd ../frontend
npm install
npm run dev
```

대시보드: http://localhost:3000
API 문서: http://localhost:8000/docs

---

## 📁 구조

```
quantsage/
├── backend/quantsage/
│   ├── exchanges/       # Upbit, Bithumb, Binance 어댑터
│   ├── market_data/     # WebSocket + TimescaleDB 파이프라인
│   ├── indicators/      # RSI, MACD, BB, ADX, etc.
│   ├── features/        # ML 피처 엔지니어링
│   ├── models/          # LSTM, XGBoost, Ensemble
│   ├── strategies/      # TrendFollowing, MeanReversion, Breakout, Grid, DCA
│   ├── risk/            # 8-Layer 리스크 관리
│   ├── backtest/        # Walk-Forward 백테스트 엔진
│   ├── execution/       # DryRun + Live 실행
│   ├── orchestrator/    # 메인 루프 + 스케줄러
│   ├── api/             # FastAPI 엔드포인트
│   ├── notifications/   # Telegram, Discord
│   ├── llm/             # Claude 뉴스/레짐 판단
│   └── db/              # SQLAlchemy + Alembic
├── frontend/            # Next.js 14 대시보드
├── scripts/             # 데이터 시드, 일일 리포트, 세무 엑셀
├── docs/                # 아키텍처, 운영 매뉴얼, API 키 가이드
└── docker-compose.yml
```

---

## 📖 문서

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 시스템 아키텍처 & 8-Layer 리스크
- [docs/API_KEYS_GUIDE.md](docs/API_KEYS_GUIDE.md) — 거래소·LLM·알림 API 키 발급 가이드
- [docs/RUNBOOK.md](docs/RUNBOOK.md) — 운영 플레이북 (Day 0~30, 긴급 대응)
- [docs/STRATEGIES.md](docs/STRATEGIES.md) — 5개 전략 명세
- [docs/RISK_POLICY.md](docs/RISK_POLICY.md) — 리스크 정책 상세
- [EXPLORATION_REPORT.md](EXPLORATION_REPORT.md) — Phase 1 조사 보고서

---

## 🛡️ 보안

- API 키 `cryptography.fernet` 암호화 저장
- IP 화이트리스트 필수
- 출금 권한 OFF
- 서버측 SL + 클라이언트 Kill-Switch 이중 보호
- 주문 요청 HMAC 서명
- FastAPI OAuth2 + JWT 대시보드 인증

---

## 📊 운영 체크리스트

### Day 0
- [ ] `.env` 모든 필수 키 입력
- [ ] `docker-compose up -d` 성공
- [ ] 대시보드 로그인 OK
- [ ] Telegram `/status` 응답

### Day 1~30 (Paper)
- [ ] `TRADING_MODE=paper`, `ENABLE_LIVE_TRADING=false`
- [ ] 일일 P&L / DD 확인
- [ ] 주간 성과 리뷰

### Day 30+ (Live 전환 기준)
- [ ] Paper 30일 누적 수익률 > 0%
- [ ] Paper Sharpe > 1.0
- [ ] Paper Max DD < 10%
- [ ] 주문 체결율 > 95%
- [ ] Kill-Switch 모든 경로 검증 완료

Live 시작 시 **총 자산의 1%만** 입금. 점진 증액.

---

## 🧪 테스트

```bash
cd backend
pytest --cov=quantsage --cov-fail-under=80
ruff check . && ruff format .
mypy .
```

---

## 📜 라이선스

MIT License. 사용에 따른 일체의 책임은 사용자에게 있습니다.

---

## 🙏 Credits

Built following EPCT methodology with cross-validation from 500+ trading bots (Freqtrade, Jesse, Hummingbot, CCXT Pro, etc.) and academic literature (Lopez de Prado, Kaufman).
