"""
Episode Tracker
---------------
Reads shows.json (the list you maintain), checks each show's latest
released episode via TVMaze (TV) or AniList (anime), compares it to
what's stored in state.json, and sends an ntfy.sh push notification
for anything new. Updates state.json when it finds something new.
"""

import json
import os
from datetime import datetime, timezone

import requests

SHOWS_FILE = "shows.json"
STATE_FILE = "state.json"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else None


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def notify(title, message):
    if not NTFY_URL:
        print("NTFY_TOPIC not set, skipping notification:", title, message)
        return
    requests.post(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": "default", "Tags": "tv"},
        timeout=15,
    )


def get_latest_tv_episode(name):
    r = requests.get(
        "http://api.tvmaze.com/singlesearch/shows", params={"q": name}, timeout=15
    )
    if r.status_code != 200:
        return None
    show = r.json()
    show_id = show["id"]

    r2 = requests.get(f"http://api.tvmaze.com/shows/{show_id}/episodes", timeout=15)
    episodes = r2.json()

    now = datetime.now(timezone.utc)
    aired = []
    for e in episodes:
        stamp = e.get("airstamp")
        if not stamp:
            continue
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if when <= now:
            aired.append(e)

    if not aired:
        return None

    latest = max(aired, key=lambda e: (e["season"], e["number"]))
    return {
        "id": f"S{latest['season']:02d}E{latest['number']:02d}",
        "title": latest.get("name") or "",
        "show_title": show["name"],
        "air_date": latest.get("airdate") or "",
    }


def get_latest_anime_episode(name):
    search_query = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        id
        title { romaji }
      }
    }
    """
    r = requests.post(
        "https://graphql.anilist.co",
        json={"query": search_query, "variables": {"search": name}},
        timeout=15,
    )
    data = r.json()
    media = data.get("data", {}).get("Media")
    if not media:
        return None

    media_id = media["id"]
    romaji = media["title"]["romaji"]

    schedule_query = """
    query ($mediaId: Int) {
      Page(perPage: 1) {
        airingSchedules(mediaId: $mediaId, notYetAired: false, sort: TIME_DESC) {
          episode
          airingAt
        }
      }
    }
    """
    r2 = requests.post(
        "https://graphql.anilist.co",
        json={"query": schedule_query, "variables": {"mediaId": media_id}},
        timeout=15,
    )
    data2 = r2.json()
    nodes = data2.get("data", {}).get("Page", {}).get("airingSchedules", [])
    if not nodes:
        return None

    latest = nodes[0]
    air_date = ""
    if latest.get("airingAt"):
        air_date = datetime.fromtimestamp(
            latest["airingAt"], tz=timezone.utc
        ).strftime("%Y-%m-%d")

    return {
        "id": f"E{latest['episode']:02d}",
        "title": "",
        "show_title": romaji,
        "air_date": air_date,
    }


def main():
    shows = load_json(SHOWS_FILE, [])
    state = load_json(STATE_FILE, {})
    changed = False

    for show in shows:
        name = show["name"]
        show_type = show.get("type", "tv").lower()
        key = f"{show_type}:{name}"

        try:
            if show_type == "anime":
                latest = get_latest_anime_episode(name)
            else:
                latest = get_latest_tv_episode(name)
        except Exception as e:
            print(f"Error checking '{name}': {e}")
            notify(f"Error checking {name}", str(e))
            continue

        if not latest:
            print(f"No episode data found for '{name}'")
            notify(f"Not found: {name}", "Check the show name matches TVMaze/AniList exactly.")
            continue

        date_str = f" (aired {latest['air_date']})" if latest.get("air_date") else ""
        prev = state.get(key, {}).get("last_episode")
        show_title = latest["show_title"]

        if prev != latest["id"]:
            print(f"New episode for '{name}': {latest['id']}{date_str}")
            message = f"{show_title}: {latest['id']}{date_str}"
            if latest["title"]:
                message += f" — {latest['title']}"
            notify("NEW EPISODE", message)
            state[key] = {
                "last_episode": latest["id"],
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            changed = True
        else:
            print(f"No new episode for '{name}' (still {prev}){date_str}")
            message = f"{show_title}: still {prev}{date_str}"
            notify("NO NEW EPISODE", message)

    if changed:
        save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
