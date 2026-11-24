#!/usr/bin/env bash
set -euo pipefail

instance=${1:-}
port=${2:-5433}
if [[ ! $instance =~ ^[a-z][a-z0-9-]*:[a-z0-9-]+:[a-z][a-z0-9-]*$ ||
      ! $port =~ ^[0-9]{4,5}$ ]] || (( 10#$port < 1024 || 10#$port > 65535 )); then
    printf '%s\n' 'Usage: bash ops/install-local-services.sh PROJECT:REGION:INSTANCE [PROXY_PORT]' >&2
    exit 2
fi

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
proxy=$(command -v cloud-sql-proxy)
units="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
if [[ ! -x "$repo/.venv/bin/python" ]]; then
    printf '%s\n' 'Install the project virtual environment first.' >&2
    exit 1
fi

mkdir -p "$units"
cat > "$units/monroe-cloud-sql.service" <<EOF
[Unit]
Description=Monroe Fund Cloud SQL Auth Proxy
After=network-online.target

[Service]
ExecStart="$proxy" --address 127.0.0.1 --port $port $instance
Restart=on-failure
RestartSec=5
EOF

cat > "$units/monroe-api.service" <<EOF
[Unit]
Description=The Monroe Fund API
Requires=monroe-cloud-sql.service
After=monroe-cloud-sql.service

[Service]
WorkingDirectory=$repo
ExecStartPre="$repo/.venv/bin/python" "$repo/ops/check_local_databases.py"
ExecStart="$repo/.venv/bin/python" -m uvicorn api:app --app-dir python-brain --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now monroe-api.service
