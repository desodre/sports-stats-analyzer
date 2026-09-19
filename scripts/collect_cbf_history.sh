#!/usr/bin/env sh
# Coleta 2023 -> 2024 -> 2025; cada comando retoma páginas já salvas.
set -eu

cd "$(dirname "$0")/.."
CLI=.venv/bin/sports-stats-analyzer
PYTHON=.venv/bin/python
AUDIT_DIR=data/cbf/audits
export SPORTS_CBF_CA_BUNDLE="${SPORTS_CBF_CA_BUNDLE:-data/cbf/certs/sectigo-ov-bundle.crt}"

if [ ! -x "$CLI" ] || [ ! -x "$PYTHON" ]; then
    echo 'Ambiente ausente; execute uv sync --locked.' >&2
    exit 1
fi
if [ ! -f "$SPORTS_CBF_CA_BUNDLE" ]; then
    echo 'Pacote de certificados CBF não encontrado.' >&2
    exit 1
fi
mkdir -p "$AUDIT_DIR"

for season in 2023 2024 2025; do
    "$CLI" cbf-teams --season "$season" --max-requests 10000 --progress
    "$CLI" cbf-team-audit --season "$season" > "$AUDIT_DIR/$season.json"
    "$PYTHON" -c '
import json, sys
from pathlib import Path

season = int(sys.argv[1])
report = json.loads(Path(sys.argv[2]).read_text())
coverage = report["coverage"]
complete = len(coverage) == 5 and all(
    item["index_observed"]
    and all(
        tab["observed"] + tab.get("unavailable", 0) == tab["expected"]
        for tab in item["tabs"].values()
    )
    for item in coverage
)
integrity = not any(
    issue["code"] in {"missing_file", "hash_mismatch", "invalid_payload"}
    for issue in report["issues"]
)
pages = report["stored_pages"]
signals = report["issue_counts"]
unavailable = signals.get("unavailable_404", 0)
print(f"CBF {season}: varredura concluída={complete}, integridade={integrity}, "
      f"páginas={pages}, abas HTTP 404={unavailable}, sinais={signals}")
if not complete or not integrity:
    sys.exit(1)
' "$season" "$AUDIT_DIR/$season.json"
done
