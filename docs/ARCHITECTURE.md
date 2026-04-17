# QuantSage Architecture

## 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                   │
│   / · /login · /dashboard · /strategies · /backtest         │
└─────────────────┬───────────────────────────────────────────┘
                  │ REST (JWT)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│   /health /auth /positions /strategies /backtest /admin     │
└─────────────────┬───────────────────────────────────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
   ┌──────────┐     ┌──────────────┐
   │Orchestr. │     │   Exchanges  │
   │ MainLoop │◄────│  Upbit/etc   │
   └──────────┘     └──────────────┘
         │
   ┌─────┴──────┬─────────────┬───────────────┐
   ▼            ▼             ▼               ▼
┌─────────┐ ┌─────────┐ ┌────────────┐ ┌──────────────┐
│Strategy │ │Features │ │   Risk     │ │ Execution    │
│Ensemble │ │ Regime  │ │ 8 Layers   │ │Paper / Live  │
└─────────┘ └─────────┘ └────────────┘ └──────────────┘
                              │
                        ┌─────┴──────┐
                        ▼            ▼
                  ┌──────────┐  ┌──────────┐
                  │PostgreSQL│  │  Redis   │
                  │Timescale │  │  Cache   │
                  └──────────┘  └──────────┘
```

## 8-Layer 리스크 파이프라인

모든 주문 제안(OrderProposal)은 다음 순서로 평가:

1. **Kill-Switch** — 활성 시 즉시 차단
2. **Regime Filter** — 현재 레짐에 맞는 전략만 통과
3. **Signal Quality** — 신뢰도 < `MIN_CONFIDENCE` 차단
4. **Correlation Guard** — 기존 포지션과 상관 > 0.75 차단
5. **Position Sizer** — Kelly/4 × 변동성타깃 × 신뢰도, 하드 상한 클램프
6. **Black Swan** — 5분 내 -5% 급락 시 차단 + kill-switch
7. **Drawdown Guard** — 일일 -3% / 주간 -8% / 누적 -15%
8. **Liquidity Check** — 주문 크기 > 호가 10% 시 분할

## 전략 앙상블

5개 독립 전략이 투표:
- **TrendFollowing** (BULL/BEAR만)
- **MeanReversion** (RANGE만)
- **Breakout** (전 레짐, HighVol은 신뢰도 반감)
- **GridHint** (RANGE만)
- **SmartDCA** (BULL/RANGE, 브레이크 내장)

과반수 + 가중 신뢰도 >= `MIN_CONFIDENCE` → 집행.
반대 방향 신호 존재 시 임계치 0.75로 상향.

## 레짐 분류

```python
if realized_vol > mean_vol * 1.5:
    return HIGH_VOL_CHOP
elif close > SMA200 * 1.03 and ADX > 22:
    return BULL_TRENDING
elif close < SMA200 * 0.97 and ADX > 22:
    return BEAR_TRENDING
else:
    return RANGE
```

## 데이터 흐름

1. `market_data/websocket.py` (계획) → Redis Pub/Sub + TimescaleDB 적재
2. `orchestrator/main_loop.py` → 주기적으로 OHLCV 읽고 신호 생성
3. Signal → 8-Layer 평가 → Paper 또는 Live 집행
4. 모든 이벤트 `loguru`로 구조화 로깅 (`data/logs/`)

## Paper ↔ Live

동일 인터페이스(`create_order`)로 구현. `settings.is_live` 체크 후 분기.
30일 Paper 기준 통과 후에만 `.env`에서 `ENABLE_LIVE_TRADING=true`로 전환 권장.
