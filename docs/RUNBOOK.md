# Runbook — 운영 매뉴얼

## Day 0 체크리스트
- [ ] `cp .env.example .env` + 모든 필수 키 입력
- [ ] `openssl rand -base64 32` → `MASTER_KEY`
- [ ] `openssl rand -hex 32` → `JWT_SECRET_KEY`
- [ ] `docker-compose up -d postgres redis` 성공
- [ ] `cd backend && pip install -e ".[dev]"`
- [ ] `pytest` 전 항목 통과
- [ ] `uvicorn quantsage.main:app` 기동
- [ ] `http://localhost:8000/health` 200 응답
- [ ] `cd frontend && npm install && npm run dev`
- [ ] `http://localhost:3000` 로그인 → 대시보드 확인

## Day 1~30 — Paper Trading

**운영 원칙**: `TRADING_MODE=paper`, `ENABLE_LIVE_TRADING=false` 유지.

매일:
- 대시보드로 레짐/포지션/Kill-Switch 상태 확인
- `data/logs/` 최근 에러 점검
- Telegram 일일 요약 확인

매주:
- 백테스트 실행 (최근 200봉)
- Win Rate, Sharpe 추세 확인

## Day 30+ — Live 전환 판단

**모든 항목 통과해야 실거래 허용**:
- [ ] Paper 30일 누적 수익률 > 0%
- [ ] Paper Sharpe > 1.0
- [ ] Paper Max DD < 10%
- [ ] 주문 체결율 > 95%
- [ ] Kill-Switch 수동 테스트 1회 이상 성공

**Live 전환 절차**:
1. `.env`에서 `TRADING_MODE=live`, `ENABLE_LIVE_TRADING=true`
2. **총 자산의 1%만** 업비트 입금
3. 서비스 재시작
4. Telegram `/status` 재확인
5. 1주일 정상이면 2%, 그다음 주 3%... 점진 증액

## 긴급 대응

### 시장 급락 중
1. 대시보드 Kill-Switch 클릭 (또는 Telegram `/kill`)
2. 업비트 웹에서 미체결 주문 수동 확인
3. 로그 분석 (`data/logs/`)
4. 진정 후 `.env` 검토 → `/admin/reset`

### 시스템 오류
1. `docker-compose logs backend --tail 200`
2. DB 연결/Redis 연결 확인
3. `docker-compose restart backend`
4. Paper로 재검증 후 Live 복귀

### Kill-Switch 활성화 후
- DB 점검: `docker-compose exec postgres psql -U quantsage -d quantsage`
- 원인 로그에서 확인 (`BLACK_SWAN`, `MAX_DRAWDOWN`, `WS_DEAD` 등)
- 원인 해소 후 `/admin/reset` 로 해제

## 월간 루틴
- [ ] 세무용 엑셀: `python scripts/tax_export.py --year 2026`
- [ ] 의존성 감사: `pip-audit` / `npm audit`
- [ ] DB 백업 검증 (복구 테스트)
- [ ] Paper vs Live 성과 비교 리포트

## 하드 리미트 (절대 수정 금지 권장)

| 항목 | 기본값 | 최대값 |
|------|--------|--------|
| `MAX_POSITION_PCT` | 0.25 | 0.50 |
| `MAX_DAILY_LOSS_PCT` | 0.03 | 0.10 |
| `MAX_WEEKLY_LOSS_PCT` | 0.08 | 0.20 |
| `MAX_DRAWDOWN_PCT` | 0.15 | 0.30 |
| `PER_TRADE_RISK_PCT` | 0.01 | 0.05 |
| `KELLY_FRACTION` | 0.25 | 0.50 |
