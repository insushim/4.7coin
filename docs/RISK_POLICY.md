# 리스크 정책

## 철학
- **Risk-First**: 수익보다 손실 방지를 우선
- 95%의 리테일 알고 트레이더는 손실. 우리의 목표는 나머지 5%에 들어가는 것
- 전량 실거래 전까지 30일 Paper 의무

## 하드 룰 (코드에 하드코딩됨)

1. **출금 권한 API 키 거부** — 거래소 설정에서 체크 해제 필수
2. **단일 종목 25% 상한** (`MAX_POSITION_PCT=0.25`)
3. **일일 -3% 손실 시 신규 진입 차단**
4. **주간 -8% 손실 시 시스템 일시 정지** (kill-switch 트리거)
5. **누적 -15% DD 시 전량 청산** (kill-switch 트리거)
6. **5분 -5% 급락 시 kill-switch**
7. **레버리지 기본 금지** (현물만, 명시 활성화 시에도 최대 2배)
8. **최소 주문 5000 KRW** (업비트)

## 포지션 사이즈 산출

```
fraction = Kelly/4 × VolTarget × Confidence
          ↓
     clamp(≤ per_trade_risk_pct)
          ↓
     notional = equity × fraction
          ↓
     clamp(existing + notional ≤ max_position_pct × equity)
```

## Kill-Switch 트리거 사유

| Reason | Source | 복구 |
|--------|--------|------|
| MANUAL | 대시보드/Telegram | `/admin/reset` |
| DAILY_LOSS | Drawdown Guard | 자정 KST 자동 |
| WEEKLY_LOSS | Drawdown Guard | 수동 검토 후 |
| MAX_DRAWDOWN | Drawdown Guard | 수동 + 재검증 |
| BLACK_SWAN | Flash-crash Detector | 수동 |
| WS_DEAD | WebSocket Timer | 연결 복구 후 |
| EXCHANGE_DOWN | API 5분 500 | 수동 |

## 감사

모든 주문/블록/kill 이벤트는 `audit_logs` 테이블에 저장.
월간 리뷰 때 감사 로그로 위반 패턴 분석.
