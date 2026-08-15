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

echo "Provisioned. Now rsync the project into /opt/scraper (as scraper user or chown after),"
echo "write /opt/scraper/.env (see .env.example), then:"
echo "  su - scraper -c 'crontab /opt/scraper/deploy/crontab'"
