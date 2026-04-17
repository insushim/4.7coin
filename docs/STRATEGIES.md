# 전략 명세

## 1. TrendFollowing
- **레짐**: BULL_TRENDING, BEAR_TRENDING
- **진입**: EMA(50) > EMA(200) AND ADX(14) > 25 AND close가 EMA(21) 근방
- **청산**: ATR 트레일링 스톱 또는 EMA(21) 이탈 (실행 계층에서 관리)
- **신뢰도**: `min(ADX/50, 1.0) × (1 - RSI 과매수 페널티)`

## 2. MeanReversion
- **레짐**: RANGE
- **진입**: BB(20,2) 하단 터치 + RSI(14) < 30 + Z-score(20) < -1.8
- **청산**: BB 중심선 도달 or Z-score > 0
- **신뢰도**: Hurst < 0.5 이면 부스트

## 3. Breakout
- **레짐**: 모든 레짐 (HIGH_VOL_CHOP에선 신뢰도 ×0.5)
- **진입**: Donchian(20) 상/하단 돌파 + 거래량 ≥ 20일 평균 × 2
- **필터**: 돌파 깊이 > 0.5 × ATR(14)
- **청산**: ATR 트레일링 or 반대 채널 도달

## 4. GridHint
- **레짐**: RANGE
- **진입 힌트**: 20일 High/Low 대비 현재가가 하단 15% / 상단 15% 영역
- **주의**: 실제 그리드 주문은 실행 계층 책임

## 5. SmartDCA
- **레짐**: BULL_TRENDING, RANGE
- **진입**: -3% 이상 하락 시 Tier-1, -6% Tier-2, -9% Tier-3 (사이즈 증액)
- **브레이크**: -12% 초과 하락 시 DCA 중단 (3Commas 비판 반영)

## 앙상블 투표 규칙

```
votes = {strategy → Signal}
if 과반수(≥3/5) BUY && 가중신뢰도 ≥ 0.65:
    → BUY
elif 과반수 SELL && 가중신뢰도 ≥ 0.65:
    → SELL
else:
    → HOLD

반대 방향 신호 존재 시 임계치 0.75로 상향.
```

## 추가 전략 제안 (후속 커밋)

- **ML Predictor (LSTM)**: 30분 후 상승 확률 예측
- **Pairs Trading**: BTC-ETH 상대 강도 기반
- **Funding Rate Arbitrage**: 현물-선물 자금 조달률 차익 (해외 한정)
- **Order Book Imbalance**: 호가 불균형 기반 단타
