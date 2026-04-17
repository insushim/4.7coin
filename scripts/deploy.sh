#!/usr/bin/env bash
# 원격 서버에서 실행하는 배포 스크립트.
#
#   1) 서버 준비: Ubuntu 22.04 / 2 vCPU / 4GB+ RAM / 퍼블릭 IP 한 개
#   2) 도메인 A 레코드가 서버 IP로 지정되어야 함 (Let's Encrypt용)
#   3) ssh root@서버   후 아래 실행:
#
#      curl -fsSL https://raw.githubusercontent.com/insushim/4.7coin/main/scripts/deploy.sh | bash
#
# 또는 로컬에서 scp 로 복사 후 실행.
set -euo pipefail

DOMAIN="${DOMAIN:-}"
ACME_EMAIL="${ACME_EMAIL:-}"
REPO="${REPO:-https://github.com/insushim/4.7coin.git}"
APP_DIR="${APP_DIR:-/opt/quantsage}"

if [[ -z "$DOMAIN" || -z "$ACME_EMAIL" ]]; then
    echo "필수: DOMAIN=... ACME_EMAIL=... bash deploy.sh"
    echo "예: DOMAIN=quantsage.example.com ACME_EMAIL=you@example.com bash deploy.sh"
    exit 1
fi

echo "━━━ 1. 시스템 업데이트 + Docker ━━━"
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
fi
apt-get update -qq
apt-get install -y -qq ufw fail2ban git

echo "━━━ 2. 방화벽 ━━━"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "━━━ 3. 저장소 가져오기 ━━━"
mkdir -p "$APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

echo "━━━ 4. .env 준비 ━━━"
if [[ ! -f .env ]]; then
    cp .env.example .env
    MASTER_KEY=$(openssl rand -base64 32)
    JWT_KEY=$(openssl rand -hex 32)
    ADMIN_PW="qs-$(openssl rand -hex 6)"
    PG_PW=$(openssl rand -hex 16)
    sed -i "s|^MASTER_KEY=.*|MASTER_KEY=$MASTER_KEY|" .env
    sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_KEY|" .env
    sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$ADMIN_PW|" .env
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$PG_PW|" .env
    sed -i "s|^APP_ENV=.*|APP_ENV=production|" .env
    {
        echo "DOMAIN=$DOMAIN"
        echo "ACME_EMAIL=$ACME_EMAIL"
    } >> .env
    echo ""
    echo "⚠️ 생성된 관리자 계정: admin / $ADMIN_PW"
    echo "   이 비밀번호를 안전한 곳에 저장하세요 (화면에 한 번만 표시됩니다)"
    echo ""
else
    echo "기존 .env 유지"
fi

echo "━━━ 5. 빌드 + 기동 ━━━"
docker compose -f docker-compose.prod.yml --env-file .env up -d --build

echo "━━━ 6. DB 마이그레이션 ━━━"
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

echo "━━━ 7. 상태 ━━━"
docker compose -f docker-compose.prod.yml ps

cat <<EOF

✅ 배포 완료
    도메인:   https://$DOMAIN
    API:      https://$DOMAIN/docs
    로그인:    admin / (.env의 ADMIN_PASSWORD)

다음 단계:
  1) DNS A 레코드 $DOMAIN → 이 서버의 IP 확인
  2) Let's Encrypt 인증서 발급 대기 (최대 2분)
  3) 브라우저에서 https://$DOMAIN 접속
  4) .env에 Upbit/Telegram 키 추가 후
     docker compose -f docker-compose.prod.yml restart backend

로그: docker compose -f docker-compose.prod.yml logs -f backend
정지: docker compose -f docker-compose.prod.yml down
EOF
