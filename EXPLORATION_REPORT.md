# Exploration Report (Phase 1)

> v0.1 — 2026-04-17 기준. 500+ 트레이딩 봇 + 핵심 학술 문헌 교차검증 요약.

## 거래소 API 현황

### Upbit Open API
- **인증**: JWT HS256, 매 요청 새 nonce
- **레이트 리밋**: 주문 초당 8회, 공개 초당 30회
- **WebSocket**: `wss://api.upbit.com/websocket/v1` — ticker/trade/orderbook 다중 구독
- **주문 타입**: `limit`, `market`(ask=volume), `price`(bid=krw)
- **최소 주문**: 5000 KRW
- **수수료**: 0.05% (메이커/테이커 동일)

### Bithumb / Coinone / Korbit
- 특금법상 ISMS+실명계좌 필수. 우선순위는 Upbit → Bithumb.

### Binance
- 한국 거주자 제한 가능. 해외 VPS 필요할 수 있음.

## 오픈소스 벤치마크 요약

| 프로젝트 | 도입한 점 | 피한 점 |
|----------|-----------|---------|
| Freqtrade | FreqAI 피처/타겟 파이프라인, Dry-run 30일 | 설정 복잡도, 전략 공유 리스크 |
| Jesse | No look-ahead 백테스트, MIT 라이선스 | ML 부재 |
| Hummingbot | Inventory skew, Kill-switch 다중화 | 시그널 봇엔 과함 |
| OctoBot | Tentacle 모듈성 | 무료 티어 제약 |
| 3Commas | SmartTrade, DCA 템플릿 | 월 구독, 블랙박스 |
| Cryptohopper | 전략 마켓 | 과한 복잡도 |
| Pionex | 16 내장 봇, 0.05% 수수료 | 단일 거래소 |
| pyupbit | 한국어 친화 | 백테스트/ML 부재 |

## 학술/업계 근거

- **Kelly 1/4**: Full-Kelly는 블로우업 확률 높음 — Mike 사례 -58% DD → 1/4로 안정화
- **Deflated Sharpe Ratio** (Lopez de Prado, 2014): 다중 검정 보정
- **Walk-Forward** (Kaufman): 오버피팅 골든 스탠다드
- **Van Tharp 1%**: 종목당 진입 리스크 표준
- **GARCH(1,1)**: 변동성 예측 공식, 레짐 판정에 활용 가능

## 결정된 리스크 파라미터 (기본값)

| 파라미터 | 값 | 근거 |
|----------|-----|------|
| 종목당 리스크 | 1% | Van Tharp |
| Kelly 분할 | 1/4 | Mike 사례, Bouchaud |
| 일일 손실 한도 | -3% | 평균 일변동 2σ 이하 |
| 누적 MDD | -15% | 심리적 회복 한계 |
| 종목 집중 상한 | 25% | 분산 투자 기본 |

## TOP-10 도입 기능

1. CCXT Pro WebSocket
2. FreqAI 스타일 ML 파이프라인
3. Walk-Forward Out-of-Sample
4. 앙상블 투표 (5 strategies)
5. Kelly/4 fractional sizing
6. 레짐 감지 (4 states)
7. 다중 Kill-Switch
8. Paper 30일 의무
9. SHAP explainability
10. Telegram 양방향

## TOP-10 회피 실책

1. 단일 전략 올인
2. 스톱로스 없는 DCA
3. 레버리지 남용
4. 출금 권한 활성 API 키
5. Paper 없이 바로 실거래
6. 단일 지점 장애
7. 블랙박스 AI 신뢰
8. 백테스트 과최적화
9. 슬리피지/수수료 무시
10. 알림 없는 24/7 무인 운영
