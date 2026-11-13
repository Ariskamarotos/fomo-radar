# FOMO Trending JSON Bridge

This repo reads the FOMOAPI.io trending leaderboard once per hour and publishes **only public token fields** in `data/trending.json`. The private API key is stored in a GitHub Actions repository secret named `FOMO_API_KEY`, never in a file or command.

## Setup
1. Create a new **public** GitHub repository (e.g. `fomo-radar`).
2. Upload `scripts/update.py` and `.github/workflows/fomo-radar.yml` into the same paths on the default `main` branch. GitHub's web Add file > Upload files can create folders; ensure paths are exact.
3. Repository **Settings > Secrets and variables > Actions > New repository secret**: name `FOMO_API_KEY` and enter the API key. Never share the key with ChatGPT or commit it.
4. Repository **Settings > Actions > General > Workflow permissions**: select **Read and write permissions** (if available). Otherwise the workflow cannot push its JSON updates.
5. Repository **Actions > Update FOMO Trending > Run workflow**. Check for a green run.
6. Inspect `https://raw.githubusercontent.com/YOUR_USERNAME/fomo-radar/main/data/trending.json` (replace username/repo). This URL must return JSON without a login.
7. Give ChatGPT **only the public raw JSON URL**, not the API key. We can then test retrieval from this chat and update the hourly monitoring instructions to consume this URL. An automation fetch must be tested separately before considering it confirmed.

## Usage limits and warnings
Per the API provider's documentation, each successful trending leaderboard read costs 250 credits from a free 250,000 credit/month allowance. Hourly polling ~720 calls per 30 days = ~180,000 credits, leaving a buffer. Avoid every-5-minute polling on this plan. The service is unofficial and the live board may be cached. `capturedAt` is the API's fetch time. `stale:false` doesn't by itself prove new FOMO source data. The data file becomes **publicly visible**. No personal credentials, wallet addresses, or private keys should be added.

Scheduled GitHub Actions can run late or occasionally be skipped, so monitor the `polledAt` field. Public JSON changes on each successful hourly fetch. No trading decisions should rely on this snapshot alone.
