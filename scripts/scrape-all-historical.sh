#!/usr/bin/env bash
#
# Historical Term Scraper - Foolproof Overnight Runner
#
# This script scrapes all historical Penn course terms.
# It's designed to be:
# - Resumable: Can stop/restart without losing progress
# - Safe: Won't re-scrape existing data
# - Logged: Keeps detailed progress logs
# - Foolproof: Clear status messages and error handling
#

set -euo pipefail

# Configuration
DB_PATH="${DB_PATH:-./courses.db}"
LOG_FILE="./logs/historical-scrape-$(date +%Y%m%d-%H%M%S).log"
RATE_LIMIT="${RATE_LIMIT:-0.5}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create logs directory
mkdir -p ./logs

# Historical terms to scrape (most recent to oldest)
# Format: TERM_CODE|TERM_NAME
HISTORICAL_TERMS=(
    "202510|Spring 2025"
    "202430|Fall 2024"
    "202410|Spring 2024"
    "202330|Fall 2023"
    "202310|Spring 2023"
    "202230|Fall 2022"
    "202210|Spring 2022"
    "202130|Fall 2021"
    "202110|Spring 2021"
    "202030|Fall 2020"
)

# Schools to scrape for each term
SCHOOLS=("E" "W" "A" "M" "N" "L" "S" "F" "G" "C" "D" "V")

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_section() {
    echo "" | tee -a "$LOG_FILE"
    echo "═══════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
    echo -e "$1" | tee -a "$LOG_FILE"
    echo "═══════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

check_existing() {
    local term_code=$1
    local school_code=$2

    # Check if term+school already has data in database
    COUNT=$(pipenv run scraper --db "$DB_PATH" stats 2>/dev/null | grep "$term_code" | wc -l || echo "0")
    if [ "$COUNT" -gt "0" ]; then
        return 0  # Has data
    else
        return 1  # No data
    fi
}

estimate_time() {
    local remaining_terms=$1
    local schools_per_term=${#SCHOOLS[@]}
    local total_scrapes=$((remaining_terms * schools_per_term))

    # Estimate: ~15 seconds per school scrape (conservative)
    local seconds=$((total_scrapes * 15))
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))

    echo "${hours}h ${minutes}m"
}

# Main script
log_section "${BLUE}Penn Path Historical Scraper${NC}
Starting: $(date)
Database: $DB_PATH
Log: $LOG_FILE
Rate limit: $RATE_LIMIT seconds"

# Check database exists
if [ ! -f "$DB_PATH" ]; then
    log "${YELLOW}⚠️  Database not found at $DB_PATH${NC}"
    log "Creating new database..."
    mkdir -p "$(dirname "$DB_PATH")"
fi

# Summary
TOTAL_TERMS=${#HISTORICAL_TERMS[@]}
TOTAL_SCHOOLS=${#SCHOOLS[@]}
log "${BLUE}📊 Scraping Plan:${NC}"
log "  Terms: $TOTAL_TERMS"
log "  Schools per term: $TOTAL_SCHOOLS"
log "  Total scrapes: $((TOTAL_TERMS * TOTAL_SCHOOLS))"
log "  Estimated time: $(estimate_time $TOTAL_TERMS)"
log ""
log "${YELLOW}💡 Tip: You can stop this script anytime with Ctrl+C${NC}"
log "${YELLOW}   It will resume from where it left off when you restart it.${NC}"
log ""

# Count down
echo -n "Starting in: "
for i in {5..1}; do
    echo -n "$i "
    sleep 1
done
echo "GO!"
echo ""

TERMS_COMPLETED=0
TERMS_SKIPPED=0
TERMS_FAILED=0

# Process each term
for term_entry in "${HISTORICAL_TERMS[@]}"; do
    IFS='|' read -r TERM_CODE TERM_NAME <<< "$term_entry"

    log_section "${BLUE}📅 Processing: $TERM_NAME ($TERM_CODE)${NC}"

    SCHOOLS_COMPLETED=0
    SCHOOLS_SKIPPED=0
    SCHOOLS_FAILED=0

    for SCHOOL in "${SCHOOLS[@]}"; do
        log "${BLUE}   🏫 School: $SCHOOL${NC}"

        # Check if already scraped
        if check_existing "$TERM_CODE" "$SCHOOL"; then
            log "${GREEN}   ✓ Already scraped - skipping${NC}"
            SCHOOLS_SKIPPED=$((SCHOOLS_SKIPPED + 1))
            continue
        fi

        # Run scraper
        log "   ⏳ Scraping..."
        if pipenv run scraper --db "$DB_PATH" scrape \
            --term "$TERM_CODE" \
            --school "$SCHOOL" \
            --rate-limit "$RATE_LIMIT" \
            >> "$LOG_FILE" 2>&1; then
            log "${GREEN}   ✓ Success${NC}"
            SCHOOLS_COMPLETED=$((SCHOOLS_COMPLETED + 1))
        else
            log "${RED}   ✗ Failed${NC}"
            SCHOOLS_FAILED=$((SCHOOLS_FAILED + 1))
        fi

        # Brief pause between schools
        sleep 1
    done

    # Term summary
    log ""
    log "${BLUE}Term $TERM_NAME Summary:${NC}"
    log "  ✓ Completed: $SCHOOLS_COMPLETED"
    log "  ⊘ Skipped: $SCHOOLS_SKIPPED"
    if [ $SCHOOLS_FAILED -gt 0 ]; then
        log "  ${RED}✗ Failed: $SCHOOLS_FAILED${NC}"
        TERMS_FAILED=$((TERMS_FAILED + 1))
    else
        TERMS_COMPLETED=$((TERMS_COMPLETED + 1))
    fi

    # Progress
    REMAINING=$((TOTAL_TERMS - TERMS_COMPLETED - TERMS_FAILED - TERMS_SKIPPED - 1))
    if [ $REMAINING -gt 0 ]; then
        log ""
        log "${YELLOW}⏱  Estimated time remaining: $(estimate_time $REMAINING)${NC}"
    fi
    log ""
done

# Final summary
log_section "${GREEN}✨ Historical Scrape Complete!${NC}

$(date)

Final Summary:
  ✓ Terms completed: $TERMS_COMPLETED / $TOTAL_TERMS
  ⊘ Terms skipped: $TERMS_SKIPPED
  ✗ Terms failed: $TERMS_FAILED

Database: $DB_PATH
Log file: $LOG_FILE

${BLUE}Next steps:${NC}
1. Review log file for any errors
2. Run: pipenv run scraper --db $DB_PATH stats
3. Export JSON: pipenv run scraper --db $DB_PATH export --output-dir .
"

log "${GREEN}🎉 All done! Sleep well!${NC}"
