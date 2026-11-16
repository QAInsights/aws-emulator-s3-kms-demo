#!/usr/bin/env bash
# Ubuntu/Debian amd64. Review before running: installs packages system-wide.
# RPM distros: use aws-emulator-x86_64.rpm from the same LTS/latest directory.
set -euo pipefail
sudo apt-get update
sudo apt-get install -y curl unzip python3-venv
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl -fL https://downloads.aws.com/aws-emulator/packages/aws-emulator/LTS/latest/aws-emulator_amd64.deb -o "$work/emulator.deb"
sudo dpkg -i "$work/emulator.deb"
# CLI v2 supports AWS_ENDPOINT_URL; distro CLI v1 may silently call real AWS.
curl -fL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o "$work/aws.zip"
unzip -q "$work/aws.zip" -d "$work"
sudo "$work/aws/install" --update
export PATH="/usr/local/bin:$PATH"
aws-emulator -v
aws --version
# Reuse an already healthy emulator; otherwise start once and wait for its CA.
health() {
  curl -fsS --cacert "$HOME/.aws/emulator/9297/ca.pem" https://127.0.0.1:9297/__admin/health
}
if ! health 2>/dev/null; then
  nohup aws-emulator >"$HOME/aws-emulator.log" 2>&1 &
  ready=false
  for _ in {1..60}; do
    if health 2>/dev/null; then ready=true; break; fi
    sleep 1
  done
  if [[ "$ready" != true ]]; then echo "Emulator did not become healthy"; exit 1; fi
fi
