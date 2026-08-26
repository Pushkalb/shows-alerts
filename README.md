# Episode Tracker

Checks your chosen TV shows and anime every 12 hours and sends you a free
push notification (via [ntfy.sh](https://ntfy.sh)) when a new episode airs.

## One-time setup (~5 minutes)

1. **Create a GitHub repo** and upload all these files to it
   (`shows.json`, `state.json`, `check_episodes.py`, `README.md`, and the
   `.github/workflows/check-episodes.yml` file — keep that folder structure).

2. **Get the ntfy app** on your phone: search "ntfy" in the App Store /
   Play Store, or just open https://ntfy.sh/app in a browser.
   In the app, tap **Subscribe to topic** and make up a topic name —
   something long and hard to guess, e.g. `mia-episode-alerts-83f2`.
   (Topics on ntfy.sh are public if someone guesses the name, so avoid
   anything obvious.)

3. **Add that topic name as a GitHub secret**:
   - In your repo, go to **Settings → Secrets and variables → Actions**
   - Click **New repository secret**
   - Name: `NTFY_TOPIC`
   - Value: the topic name you picked (e.g. `mia-episode-alerts-83f2`)

That's it — the workflow will now run automatically every 12 hours.

## Adding or removing shows

Edit `shows.json` directly in GitHub (or locally and push). Each entry needs:

```json
{ "name": "Show or Anime Title", "type": "tv" }
```

Use `"type": "anime"` for anime (checked via AniList) or `"type": "tv"`
for everything else (checked via TVMaze). Use the show's common English or
romaji title — it does a fuzzy search, so it doesn't need to be exact.

Commit the change and it's picked up on the next run (or trigger it
immediately: go to the **Actions** tab → **Check Episodes** → **Run workflow**).

## How it works

- `check_episodes.py` looks up each show's latest *aired* episode.
- It compares that to what's stored in `state.json` (the last one it saw).
- If it's new, it sends a push notification with the episode number/title
  to your ntfy topic, and updates `state.json`.
- The workflow commits the updated `state.json` back to the repo so it
  remembers between runs.

## Notes / limits

- Free and requires no server — GitHub Actions runs it on their machines.
- TVMaze and AniList are free public APIs with no key needed.
- If a show name doesn't match anything, check the console log for that
  run (Actions tab → click the run → check_episodes step) — it'll say
  "No episode data found."
