# 1. Set up test database (isolate from production)
export PENN_SCRAPER_DB=/tmp/crn-reuse-test.db
rm -f /tmp/crn-reuse-test.db  # Clean slate

# 2. Scrape Fall 2024 - Dental School only
pipenv run scraper scrape 202430 -s D

# 3. Scrape Fall 2025 - SAME school (tests CRN reuse)
pipenv run scraper scrape 202530 -s D

# 4. Verify samples (KEY: detects corruption)
pipenv run verify-samples scrape-samples/scrape-samples-*.json

# 5. Check for CRN reuse (should see same CRNs in both terms)
sqlite3 /tmp/crn-reuse-test.db "
SELECT crn, COUNT(DISTINCT term_id) as term_count, 
       GROUP_CONCAT(term_id || ':' || code) as courses
FROM courses 
GROUP BY crn 
HAVING term_count > 1 
LIMIT 10;"