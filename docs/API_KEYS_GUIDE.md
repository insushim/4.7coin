# API Keys 발급 가이드

## 1. Upbit Open API (필수)

**경로**: https://upbit.com → 마이페이지 → Open API 관리

**권한 설정 (매우 중요)**:
- ✅ 자산조회
- ✅ 주문조회
- ✅ 주문하기
- ❌ **출금하기 (반드시 체크 해제)**
- ❌ 입금하기

**IP 화이트리스트**: 반드시 설정 (서버 공인 IP).

**.env 적용**:
```env
UPBIT_ACCESS_KEY=...
UPBIT_SECRET_KEY=...
UPBIT_ALLOWED_IPS=123.45.67.89
```

## 2. Anthropic Claude API (권장)

**경로**: https://console.anthropic.com → API Keys
**모델**: `claude-sonnet-4-5` (비용 효율) 또는 `claude-opus-4-7`
**예상 비용**: 뉴스 요약 시간당 1회 × 30일 ≈ $5–15/월

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

## 3. Telegram Bot Token (권장)

1. Telegram에서 `@BotFather` 검색 → `/newbot`
2. 봇 이름 → 유저명 입력 → 토큰 수신
3. 만든 봇과 대화 시작 (`/start`)
4. `@userinfobot` 에서 본인 `chat_id` 확인

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

## 4. 옵션 키

| 서비스 | 용도 | 무료? |
|--------|------|-------|
| CoinGecko Demo | 시가총액/랭킹 | ✅ |
| CryptoPanic | 뉴스 헤드라인 | ✅ (월 10k) |
| Gemini API | 보조 LLM | ✅ (분당 15회) |
| Glassnode | 온체인 지표 | ❌ ($29/월) |
| Discord Webhook | 로그 아카이브 | ✅ |

## 5. MASTER_KEY 생성

```bash
openssl rand -base64 32
```

출력을 `.env`의 `MASTER_KEY=` 에 붙여넣기. API 키 암호화에 사용.

## 6. JWT_SECRET_KEY

```bash
openssl rand -hex 32
```

## 비용 요약 (월)

| 항목 | 금액 |
|------|------|
| Upbit 수수료 | 거래액의 0.05% (양방향) |
| Claude API | $5–15 |
| 필수 무료 키 | $0 |
| Oracle Cloud Free VPS | $0 |
| **최소 합계** | **$5–15/월 + 수수료** |
