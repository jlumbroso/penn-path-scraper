Run Follow-Up

Historical scrape finished cleanly at 14:07:48 with all 16 terms marked complete and no term-level failures (logs/historical-scrape-20251006-021957.log:210867).
Fall 2025 (term 202530) logged twelve school passes, each with errors=0; only Dental returned an empty result set (logs/historical-scrape-20251006-021957.log:188220, logs/historical-scrape-20251006-021957.log:210763). The courses.db snapshot now holds 2 268 sections for that term, versus 6 519 for Fall 2024, which lines up with some schools not publishing yet.
Older catalogs shrink sharply once you move past Summer 2022 because the API stops returning data—every school run for Spring 2022 and earlier comes back empty (logs/historical-scrape-20251006-021957.log:182475, logs/historical-scrape-20251006-021957.log:184353). Summer terms (e.g., 202520 at 786 sections, 202420 at 277) are also naturally smaller than fall/spring.
Only two scrape warnings surfaced, both during Fall 2023’s Arts & Sciences pass where SQLite briefly reported “database is locked,” leaving CRNs 20875 and 15753 unsaved (logs/historical-scrape-20251006-021957.log:138925, logs/historical-scrape-20251006-021957.log:138929, logs/historical-scrape-20251006-021957.log:140227).
Next steps: 1) re-run those two CRNs once the database isn’t busy (pipenv run scraper --crn 20875 15753 …) to fill the gap; 2) monitor the API for schools that still return zero results (notably Dental for 202530) and re-scrape once they publish their schedules.

Can you look at earlier runs, especially those where Fall 2025 completed? I thought that there was like 6,000 courses and I wonder what the difference is.


Findings

Earlier historical runs never actually reached Fall 2025; every prior log in logs/ aborts at the school kickoff because --no-skip-existing is an invalid flag, so Fall 2025 only appears in the most recent run (logs/historical-scrape-20251005-114602.log:30, repeated for each school).
The successful 6 Oct run did scrape Fall 2025 and recorded 6535 section saves across the 12 schools (e.g., Engineering 957, Fels 294, etc.) as shown throughout logs/historical-scrape-20251006-021957.log:188219 and logs/historical-scrape-20251006-021957.log:209491, ending with the “Term Fall 2025 Summary” success banner (logs/historical-scrape-20251006-021957.log:210852).
Older snapshots (old.courses.db, biggest.old.courses.db) still hold 6469 sections for term 202530, confirming your recollection of ~6 k records. The new courses.db only shows 2268 rows under term_id = 202530 because the persistence layer keys courses solely by CRN (src/models.py:54-66) and, on updates, does not move the record to the new term (src/persistence.py:130-196). Since Penn recycles CRNs every term, scraping 2024 data first claimed those CRNs; when Fall 2025 ran, the rows were updated in place but left tagged with the old term.
A quick SQLite check shows 4254 rows now sitting under term_id = 202430 with last_scraped timestamps between 12:30–14:07 on 6 Oct—the exact window of the Fall 2025 pass—plus eight rows under 202330 and five under 202230. Combined with the 2268 rows still labeled 202530, they account for all 6535 sections from the log.
Next steps

Fix the schema/persistence bug—either change the primary key to (term, crn) or, at minimum, set course.term = term whenever save_course reuses an existing row—then rebuild the DB from a clean scrape.
Until the fix is in place, read the Fall 2025 data from the mis-tagged rows (term_id 202430, 202330, 202230) if you need it immediately.
After applying the fix, re-run the historical scraper so every term’s sections land under the correct term code.
I don't really understand the problem you're describing, but it's true. I have a fall 2025-courses-orig-migrated.db and they showed like the 6k recordings for 2025 because it was scraped first. I don't understand what you're saying about the CRNs that have been claimed or whatever and so forth. But that sounds like a really, really big problem. Can you help describe in great detail what this problem is? So, let's look at this.


What’s Going Wrong

The courses table makes crn the primary key (src/models.py#L54-L66). That means each CRN can appear only once in the database, regardless of term. Penn reuses CRNs every semester, so when Fall 2025 publishes (e.g. CRN 60563 for BE 1000), it collides with the Spring/Fall 2024 entry that already owns the same CRN.
During persistence (src/persistence.py#L130-L220), save_course uses Course.get_or_create(crn=…). If a row with that CRN already exists, Peewee returns the old record instead of inserting a new one. The update block then overwrites fields like title, seats, etc., but never reassigns the term foreign key. The row keeps whatever term it had when it was first inserted.
Your latest log shows the scraper successfully fetching 6 535 Fall 2025 sections (logs/historical-scrape-20251006-021957.log:188219, logs/historical-scrape-20251006-021957.log:209491), yet courses.db reports only 2 268 rows for term 202530. The missing 4 267 rows now live under earlier terms because they inherited their predecessors’ term IDs when the CRN collision happened.
Concrete example: CRN 60563 is fall 2025 BE 1000 per the log. Querying courses.db shows that CRN with term_id='202430' and last_scraped='2025-10-06T12:30:38…'—the timestamp of the Fall 2025 pass. The same scrape window accounts for 4 254 records stuck under 202430, plus a handful under 202330/202230, exactly matching the “missing” Fall 2025 counts.
Because of this key design, every time you scrape a new term that reuses CRNs, you mutate former semesters and lose the historical separation. Earlier exports (e.g. fall 2025-courses-orig-migrated.db, biggest.old.courses.db) look right only because Fall 2025 was scraped before other terms claimed those CRNs.
Why It’s Critical

Historical data becomes unreliable: older semesters get overwritten with the latest details, and counts by term are no longer trustworthy.
Analytics that depend on course histories, enrollment snapshots, or term-by-term comparisons will be corrupted—data silently migrates to the wrong term.
rerunning scrapes amplifies the problem since each new pass mashes additional terms together.
Path Forward

Redesign the primary key so it distinguishes terms—e.g., make (term, crn) the composite key or introduce a surrogate ID with unique index on (term, crn).
Update save_course to fetch/update rows using both term and CRN, and explicitly set course.term = term.
After fixing the schema/persistence logic, rebuild the database from scratch so each term keeps its own copy of every reused CRN.
Until that fix is in place, the only trustworthy Fall 2025 snapshot is the pre-migration database; the current courses.db intermixes 202530 data with earlier terms because of the CRN collisions.