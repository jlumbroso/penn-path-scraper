# Scripts

## Historical Scraper

**Purpose**: Scrape all historical Penn course terms overnight.

### Quick Start (Run Overnight)

```bash
# From repo root
./scripts/scrape-all-historical.sh
```

The script will:
- ✅ **Scrape 10 historical terms** (Spring 2025 back to Fall 2020)
- ✅ **Auto-resume** if stopped (won't re-scrape existing data)
- ✅ **Log everything** to `logs/historical-scrape-*.log`
- ✅ **Show progress** with colored output and time estimates
- ✅ **Handle errors** gracefully and continue

### Stop and Resume

Press `Ctrl+C` to stop anytime. When you restart, it will skip already-scraped data.

### Custom Configuration

```bash
# Use custom database path
DB_PATH=./my-database.db ./scripts/scrape-all-historical.sh

# Adjust rate limiting (slower = more polite)
RATE_LIMIT=1.0 ./scripts/scrape-all-historical.sh
```

### After Scraping

1. **Check stats**:
   ```bash
   pipenv run scraper --db courses.db stats
   ```

2. **Export to JSON**:
   ```bash
   pipenv run scraper --db courses.db export --output-dir .
   ```

3. **Commit and deploy**:
   ```bash
   git add .
   git commit -m "data: add historical course data"
   git push  # Triggers deployment
   ```

### Estimated Time

- **Full scrape**: ~3-4 hours (10 terms × 12 schools × ~15 sec/school)
- **Resume from partial**: Depends on what's already scraped

### Monitoring Progress

The script outputs:
- 🏫 Each school being scraped
- ✓ Success/skip/failure status
- ⏱️ Estimated time remaining
- 📊 Summary after each term

All output is also saved to log files in `./logs/`

### Terms Included

| Term Code | Name          | Year |
|-----------|---------------|------|
| 202510    | Spring 2025   | 2025 |
| 202430    | Fall 2024     | 2024 |
| 202410    | Spring 2024   | 2024 |
| 202330    | Fall 2023     | 2023 |
| 202310    | Spring 2023   | 2023 |
| 202230    | Fall 2022     | 2022 |
| 202210    | Spring 2022   | 2022 |
| 202130    | Fall 2021     | 2021 |
| 202110    | Spring 2021   | 2021 |
| 202030    | Fall 2020     | 2020 |

### Troubleshooting

**Script fails to start**:
```bash
# Make sure it's executable
chmod +x scripts/scrape-all-historical.sh

# Verify pipenv is installed
pipenv --version
```

**Want to add more terms?**

Edit `HISTORICAL_TERMS` array in the script:
```bash
HISTORICAL_TERMS=(
    "202510|Spring 2025"
    "YOUR_CODE|YOUR_NAME"  # Add here
)
```

### Safety Features

- ✅ Won't overwrite existing data (uses `--skip-existing`)
- ✅ Detailed logging for debugging
- ✅ Colored output for easy monitoring
- ✅ Rate limiting to be respectful to Penn's servers
- ✅ Error handling doesn't stop entire script
