# Deployment

## 로컬 (개발용)

이미 동작 확인됨. 맥북에서 바로 돌아감.

> ⚠️ **`npm run build` 이후에 `npm run dev`를 돌리면 500 에러** — Next.js가 프로덕션 빌드 캐시를 dev 모드에서 재사용하려다 실패합니다.
> 이런 경우: `npm run dev:clean` (`.next` 먼저 삭제 후 dev 실행).

```bash
# 사전: brew install postgresql@16 redis && brew services start postgresql@16 redis
createuser -s quantsage && psql postgres -c "ALTER USER quantsage WITH PASSWORD 'change_me_strong';"
createdb -O quantsage quantsage

# 백엔드
cd backend
source .venv/bin/activate
export DATABASE_URL="postgresql+asyncpg://quantsage:change_me_strong@localhost:5432/quantsage"
alembic upgrade head
uvicorn quantsage.main:app --reload

# 프론트
cd frontend && npm run dev
```

---

## 프로덕션 (VPS 1대로 올인원 배포)

### 추천 스펙
- **Oracle Cloud Free Tier** (ARM Ampere 4 core / 24GB 무료) — 이 프로젝트에 충분
- 또는 AWS Lightsail $10~20/월, Hetzner CPX11 €5/월
- Ubuntu 22.04 / 2 vCPU / 4GB RAM / 30GB SSD 이상

### 사전 준비
1. 도메인 1개 (예: `quantsage.example.com`) — Cloudflare/가비아/Namecheap 어디든
2. 서버 IP를 A 레코드로 지정
3. SSH 접속 가능

### 한 줄 배포

서버에 SSH 접속 후:

```bash
DOMAIN=quantsage.example.com \
ACME_EMAIL=you@example.com \
bash <(curl -fsSL https://raw.githubusercontent.com/insushim/4.7coin/main/scripts/deploy.sh)
```

이 스크립트가 자동으로:
- Docker 설치
- 방화벽(ufw) 22/80/443 허용
- 저장소 clone → `/opt/quantsage`
- `.env` 자동 생성 (MASTER_KEY, JWT, admin 패스워드 모두 랜덤)
- `docker-compose.prod.yml` 빌드 + 기동
- TimescaleDB + Redis + FastAPI + Next.js + Traefik 컨테이너 5개 실행
- Traefik + Let's Encrypt 자동 HTTPS 발급
- Alembic 마이그레이션 실행

완료 후 브라우저에서 `https://quantsage.example.com` 접속.

### API 키 추가

```bash
ssh root@서버
cd /opt/quantsage
nano .env
# UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, TELEGRAM_* 등 추가
docker compose -f docker-compose.prod.yml restart backend
```

### 운영 명령

```bash
# 로그 실시간
docker compose -f docker-compose.prod.yml logs -f backend

# 재시작
docker compose -f docker-compose.prod.yml restart backend

# 정지
docker compose -f docker-compose.prod.yml down

# 업데이트 (git pull + 재빌드)
cd /opt/quantsage && git pull && docker compose -f docker-compose.prod.yml up -d --build

# DB 백업
docker compose -f docker-compose.prod.yml exec postgres \
    pg_dump -U quantsage quantsage | gzip > backup_$(date +%Y%m%d).sql.gz

# DB 복원
gunzip < backup_YYYYMMDD.sql.gz | \
    docker compose -f docker-compose.prod.yml exec -T postgres psql -U quantsage quantsage
```

### Kill-Switch 긴급 정지

```bash
# 컨테이너 내부에서
curl -X POST -u admin:$ADMIN_PASSWORD http://localhost:8000/admin/kill

# 또는 Telegram에서
/kill  (봇에게)

# 또는 하드 정지
docker compose -f docker-compose.prod.yml stop backend
```

---

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` 이 매 push/PR마다 자동 실행:

- ✅ Postgres 16 + Redis 7 컨테이너 기동
- ✅ 백엔드 pytest 29개 + ruff lint
- ✅ Alembic 마이그레이션 적용 검증
- ✅ 프론트 `tsc --noEmit` + `next build`

자동 배포는 기본값으로 **꺼져 있습니다**. 켜려면:

1. VPS에 배포 후 deploy SSH 키 발급
2. GitHub Secrets 등록: `SSH_HOST`, `SSH_USER`, `SSH_KEY`
3. `.github/workflows/deploy.yml` 추가 (아래 템플릿)

```yaml
# .github/workflows/deploy.yml (선택 — 수동 트리거만)
name: Deploy
on:
  workflow_dispatch:   # main push 자동 배포를 원하면 push: branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Pull & rebuild on VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/quantsage
            git pull
            docker compose -f docker-compose.prod.yml up -d --build
            docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## Vercel / Netlify 안내

Frontend만 정적 배포는 가능하지만 **권장하지 않음**:

- 백엔드는 WebSocket + 장시간 트레이딩 루프라서 serverless 부적합
- 로컬 백엔드와 공개 프론트가 연결 안 됨 (CORS + localhost 문제)
- → **Backend + Frontend는 같은 VPS에 함께 배포** 하는 것이 운영·보안상 유리

---

## 모니터링

- **Uptime Robot** (무료): `https://your-domain/health` 1분 주기
- **Telegram 알림**: 주문·체결·Kill-Switch 자동 푸시 (봇 토큰만 .env에 넣으면 자동)
- **로그 보존**: `backend/data/logs/` 30일 회전 (loguru 자동)
- **DB 백업**: crontab + pg_dump + rclone to Google Drive/S3 권장
