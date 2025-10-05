#!/usr/bin/env bash
set -euo pipefail

# Fetch representative Penn Courses API detail payloads for documentation/debugging.
# Requires outbound network access. Outputs JSON files under tests/fixtures/api_samples.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/tests/fixtures/api_samples"

mkdir -p "${OUTPUT_DIR}"

SAMPLES=(
  "202510|BE 1000|10613|spring-2025-be1000-10613"
  "202430|BE 1000|60563|fall-2024-be1000-60563"
  "202330|BE 1000|60563|fall-2023-be1000-60563"
  "202430|CHEM 1101|80134|fall-2024-chem1101-80134"
  "202330|OIDD 2910|60251|fall-2023-oidd2910-60251"
)

USER_AGENT="Mozilla/5.0 (compatible; PennPathScraper/1.0; +https://github.com/jlumbroso/penn-path-scraper)"
API_URL="https://courses.upenn.edu/api/?page=fose&route=details"

for entry in "${SAMPLES[@]}"; do
  IFS='|' read -r term code crn label <<< "${entry}"
  body=$(python - "$term" "$code" "$crn" <<'PY'
import json, sys
term, code, crn = sys.argv[1:4]
print(json.dumps({
    "group": f"code:{code}",
    "key": f"crn:{crn}",
    "srcdb": term,
    "matched": f"crn:{crn}",
    "userWithRolesStr": "!!!!!!",
}, separators=(",", ":")))
PY
)
  output_file="${OUTPUT_DIR}/${label}.json"
  echo "Fetching term ${term}, course ${code}, CRN ${crn} -> ${output_file}"
  curl -sS "${API_URL}" \
    -H "Accept: application/json, text/javascript, */*; q=0.01" \
    -H "Content-Type: application/json" \
    -H "X-Requested-With: XMLHttpRequest" \
    -H "User-Agent: ${USER_AGENT}" \
    --data "${body}" \
    --fail \
    > "${output_file}"
  echo "Saved $(stat -f%z "${output_file}") bytes"
done

echo "Samples written to ${OUTPUT_DIR}"
