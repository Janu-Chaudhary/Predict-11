#!/usr/bin/env bash
# After resetting the Supabase database password in the dashboard, run this in YOUR terminal:
#   infra/set-db-password.sh
# It asks for the new password (hidden), tests it, rewrites backend/.env.deploy (git-ignored)
# and copies the P11_DATABASE_URL to the clipboard for Render. Nothing is printed.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE=backend/.env.deploy
REF=$(grep '^SUPABASE_PROJECT_REF=' "$ENV_FILE" | cut -d= -f2-)
HOST=aws-0-ap-south-1.pooler.supabase.com

read -rsp "New Supabase database password: " PW; echo
if ! PGPASSWORD="$PW" PGCONNECT_TIMEOUT=15 psql \
  "host=$HOST port=5432 user=postgres.$REF dbname=postgres sslmode=require" -tAc "select 1" >/dev/null 2>&1; then
  echo "Could not connect with that password (wait ~1 min after resetting, then retry)." >&2
  exit 1
fi
ENC=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$PW")
URL="postgresql+psycopg://postgres.$REF:$ENC@$HOST:5432/postgres?sslmode=require"
umask 077
printf 'SUPABASE_DB_PASSWORD=%s\nP11_DATABASE_URL=%s\nSUPABASE_PROJECT_REF=%s\n' "$PW" "$URL" "$REF" > "$ENV_FILE"
if command -v wl-copy >/dev/null; then printf '%s' "$URL" | wl-copy
elif command -v xclip >/dev/null; then printf '%s' "$URL" | xclip -selection clipboard
else echo "No clipboard tool; run: grep P11_DATABASE_URL $ENV_FILE | cut -d= -f2-  (in your terminal)"; exit 0; fi
echo "OK: connection works, $ENV_FILE updated, P11_DATABASE_URL copied to clipboard."
