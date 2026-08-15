#!/usr/bin/env bash
# One-time host setup. No browser needed -- page fetching goes through
# FlareSolverr (see common/fetch.py), so this only needs uv, git (for the
# GitHub Actions runner's checkout step), and the 'scraper' user.
set -euo pipefail

apt-get update -qq
apt-get install -y --no-install-recommends git

curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

id scraper &>/dev/null || useradd -m -s /bin/bash scraper
cp /root/.local/bin/uv /root/.local/bin/uvx /usr/local/bin/
chown -R scraper:scraper /opt/scraper 2>/dev/null || true

# Narrowly-scoped passwordless sudo so the deploy workflow (running as
# 'scraper' on the self-hosted runner) can restart the viewer after every
# deploy -- Python doesn't hot-reload and rsync alone doesn't touch the
# systemd unit. Only this exact command, nothing else.
cat > /etc/sudoers.d/scraper-viewer-restart <<'SUDOERS'
scraper ALL=(root) NOPASSWD: /usr/bin/systemctl restart scraper-viewer
SUDOERS
chmod 440 /etc/sudoers.d/scraper-viewer-restart
visudo -c

echo "Provisioned. Now rsync the project into /opt/scraper (as scraper user or chown after),"
echo "write /opt/scraper/.env (see .env.example), then:"
echo "  su - scraper -c 'crontab /opt/scraper/deploy/crontab'"
