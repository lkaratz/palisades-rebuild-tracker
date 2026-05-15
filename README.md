# Rebuilding the Palisades

A community-facing tracker for Pacific Palisades fire rebuild permits, construction,
and milestones. Data is pulled daily from official LA City, LA County, and California
state dashboards and rendered as a clean, editorial-feel static site.

**Stack**: single static HTML page + Python scraper + GitHub Actions cron. No server,
no database, no build step. Free to host on GitHub Pages.

## What it does

1. Every morning at 6am Pacific, GitHub Actions runs `scripts/scrape.py`
2. The scraper pulls the latest permit numbers from the [California state rebuilding dashboard](https://www.ca.gov/lafires/rebuilding-la/), which itself aggregates official numbers from LA City, LA County, Malibu, and Pasadena
3. If the numbers have changed, the workflow commits a new `data/current.json`
4. GitHub Pages auto-redeploys; visitors see the new data on next page load

The City of LA section is the primary data for Palisades rebuilds, since the vast
majority of Palisades parcels fall under City of LA jurisdiction.

## File layout

```
.
├── index.html              # the entire site — self-contained, no build needed
├── data/
│   └── current.json        # the data, updated daily by the scraper
├── scripts/
│   ├── scrape.py           # the scraper
│   └── requirements.txt
└── .github/
    └── workflows/
        └── daily-update.yml  # GitHub Actions cron
```

## Local development

```bash
# Install Python deps and run the scraper once
pip install -r scripts/requirements.txt
python scripts/scrape.py

# Serve the site locally
python -m http.server 8000
# Then open http://localhost:8000
```

## Deploying to GitHub Pages

1. **Create a new GitHub repo** (e.g. `palisades-rebuild-tracker`) and push these files to it
2. **Settings → Pages → Source → Deploy from a branch**, pick `main` and `/ (root)`
3. **Settings → Actions → General → Workflow permissions →** select "Read and write permissions". This lets the daily scraper commit data updates.
4. **Actions tab → Daily data update → Run workflow** once to confirm the scraper works end-to-end
5. Visit `https://YOUR-USERNAME.github.io/palisades-rebuild-tracker/`

The site will update itself every morning from there. If you want a custom domain
like `palisadesrebuild.org`, point its DNS at GitHub Pages and add a `CNAME` file
with the domain in this repo.

## Customizing

- **Milestones, neighborhoods, resources, About copy** — edit `data/current.json` directly. The scraper only overwrites the four metric fields under each jurisdiction; everything else is preserved.
- **Visual design** — all CSS is at the top of `index.html` in a single `<style>` block.
- **Add new data sources** — extend `scripts/scrape.py`. The scraper has a permissive parser that walks the state page by HTML structure, so it's resilient to minor markup changes.

## When the scraper fails

The scraper exits non-zero on failure rather than overwriting `data/current.json`
with zeros or empty objects. The site keeps showing the last good data, and the
failure is visible in the Actions tab. Most likely cause: the source page structure
changed. Fix the parser in `scripts/scrape.py`.

## Data caveats

- **The state dashboard is the source of truth here**, and it updates "at least weekly" per its own copy. The City of LA's own dashboard updates hourly, but its numbers are loaded via embedded iframe and aren't easily scrapeable.
- **City of LA numbers reflect single-family residences, duplexes, and ADUs only.** Commercial permits and infrastructure permits are tracked separately and not included.
- **There are discrepancies between trackers.** Pali Builds, City of LA, and LA County all count "permits" differently (what qualifies as a rebuild permit, what counts as one project vs. one address, etc.). This site uses City of LA numbers as the canonical Palisades count and notes the source.
- **The "under construction" and "certificates of occupancy" numbers** come from City of LA press releases, not the daily scraped feed. Update these in `data/current.json` manually when new numbers are reported.

## Credits & disclaimer

Independent, community-facing aggregator. Not affiliated with the City of Los Angeles,
LA County, the State of California, or any government agency. For official information
or to file rebuild applications, see the resources listed on the site.
