#!/usr/bin/env python3
"""
Auto-Play Unique Hindi Songs Requester
======================================
Har 3.6 seconds mein ek unique (bina repeat hue) Hindi song ki YouTube video ID
ke saath API endpoint par request bhejta hai:
    https://host-repository.vercel.app/harshmanjjhi/xenobot2/url/{video_id}

Features:
- 53 verified unique Hindi songs (Aashiqui 2, Arijit Singh, Atif Aslam, KK,
  90s classics, 70s/80s evergreen old songs, aur 2024-2026 new hits).
- Zero-duplicate guarantee: ek baar jo song request ho gaya, wo dubara repeat
  nahi hoga (history `played_hindi_songs.json` mein save hoti hai).
- Built-in auto-discovery: jab 53 curated songs khatam ho jayein, to script
  automatically YouTube search se naye unique Hindi songs fetch karke bina
  repeat kiye chalti rahegi (zero external pip packages required).

Usage:
    python3 auto_play_hindi_songs.py
    python3 auto_play_hindi_songs.py --interval 3.6
    python3 auto_play_hindi_songs.py --reset        # Played history clear karke fresh start
    python3 auto_play_hindi_songs.py --dry-run      # Bina API hit kiye test karne ke liye
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# =============================================================================
# CONFIGURATION
# =============================================================================
API_BASE_URL = "https://host-repository.vercel.app/harshmanjjhi/xenobot2/url/{video_id}"
DEFAULT_INTERVAL_SECONDS = 3.6
REQUEST_TIMEOUT_SECONDS = 12.0
HISTORY_FILE = Path(__file__).with_name("played_hindi_songs.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# 53 Verified, 100% Unique Hindi Songs (New + Old + Romantic + Sad + Evergreen)
# Format: (youtube_video_id, song_title)
CURATED_HINDI_SONGS: List[Tuple[str, str]] = [
    # --- Aashiqui 2 & Arijit Singh Soulful Hits ---
    ("IJq0yyWug1k", "Tum Hi Ho - Aashiqui 2 (Arijit Singh)"),
    ("VdyBtGaspss", "Chahun Main Ya Naa - Aashiqui 2 (Arijit Singh, Palak Muchhal)"),
    ("GtPvCa3vvxA", "Milne Hai Mujhse Aayi - Aashiqui 2 (Arijit Singh)"),
    ("z3UHfi9vpbc", "Sunn Raha Hai Na Tu - Aashiqui 2 (Ankit Tiwari)"),
    ("284Ov7ysmfA", "Channa Mereya - Ae Dil Hai Mushkil (Arijit Singh)"),
    ("dhY8jRNELUc", "Agar Tum Saath Ho - Tamasha (Alka Yagnik, Arijit Singh)"),
    ("hoNb6HuNmU0", "Khairiyat - Chhichhore (Arijit Singh)"),
    ("vGHa_VcAIxM", "Shayad - Love Aaj Kal (Arijit Singh)"),
    ("AgX2II9si7w", "Tujhe Kitna Chahne Lage - Kabir Singh (Arijit Singh)"),
    ("2ltGXfmI6mk", "Muskurane Ki Wajah Tum Ho - CityLights (Arijit Singh)"),
    ("cYOB941gyXI", "Hawayein - Jab Harry Met Sejal (Arijit Singh)"),
    ("AEIVhBS6baE", "Gerua - Dilwale (Arijit Singh, Antara Mitra)"),
    ("zlt38OOqwDc", "Raabta - Agent Vinod (Arijit Singh)"),
    ("BddP6PYo2gs", "Kesariya - Brahmastra (Arijit Singh)"),
    ("ElZfdU54Cp8", "Apna Bana Le - Bhediya (Arijit Singh)"),

    # --- New Bollywood Romantic & Trending Hits (2023-2026) ---
    ("VAdGW7QDJiU", "Chaleya - Jawan (Arijit Singh, Shilpa Rao)"),
    ("Etkd-07gnxM", "O Maahi - Dunki (Arijit Singh)"),
    ("k3g_WjLCsXM", "Sajni - Laapataa Ladies (Arijit Singh)"),
    ("HrnrqYxYrbk", "Satranga - Animal (Arijit Singh)"),
    ("iAIBF2ngbWY", "Pehle Bhi Main - Animal (Vishal Mishra)"),
    ("RLzC55ai0eo", "Heeriye - Jasleen Royal ft. Arijit Singh"),
    ("k3ijQJjUbTs", "Soulmate - Badshah x Arijit Singh"),
    ("6d5SS0gS5bU", "Tainu Khabar Nahi - Munjya (Arijit Singh)"),
    ("Nnop2walGmM", "Tum Se - Teri Baaton Mein Aisa Uljha Jiya (Raghav Chaitanya)"),
    ("axepn8QqxRk", "Soni Soni - Ishq Vishk Rebound (Darshan Raval, Jonita Gandhi)"),
    ("k6q4lENp434", "Preet Re - Dhadak 2 (Darshan Raval, Jonita Gandhi)"),
    ("8SYPKQMW_2Q", "Tum Ho Toh - Saiyaara (Vishal Mishra, Hansika Pareek)"),
    ("0v5eHPfy5Lk", "Barbaad - Saiyaara (Jubin Nautiyal)"),
    ("43MwKFSkCjA", "Tu Saath Hai Toh - Mithoon, Vishal Mishra"),
    ("2-WI6cDLaok", "Tumhein Bhi Humse - Vishal Mishra, Mithoon"),
    ("gvyUuxdRdR4", "Raataan Lambiyan - Shershaah (Jubin Nautiyal, Asees Kaur)"),

    # --- Atif Aslam, KK, Mohit Chauhan, Sonu Nigam & Armaan Malik ---
    ("Dp6lbdoprZ0", "Main Rahoon Ya Na Rahoon - Armaan Malik"),
    ("Cb6wuzOurPc", "Tum Se Hi - Jab We Met (Mohit Chauhan)"),
    ("g0eO74UmRBs", "Kal Ho Naa Ho - Title Track (Sonu Nigam)"),
    ("rTuxUAuJRyY", "Tera Hone Laga Hoon - Ajab Prem Ki Ghazab Kahani (Atif Aslam)"),
    ("P8PWN1OmZOA", "Tu Jaane Na - Ajab Prem Ki Ghazab Kahani (Atif Aslam)"),
    ("pkzOBl1p7y4", "Jeene Laga Hoon - Ramaiya Vastavaiya (Atif Aslam, Shreya Ghoshal)"),
    ("swcCuuQKGJ4", "Pehli Nazar Mein - Race (Atif Aslam)"),
    ("GmbOGB91CYg", "Tere Bin - Bas Ek Pal (Atif Aslam)"),
    ("U2QNhsAgIIE", "Dil Ibaadat - Tum Mile (KK)"),
    ("-8C_2BBVWk8", "Zara Sa - Jannat (KK)"),
    ("cmMiyZaSELo", "Khuda Jaane - Bachna Ae Haseeno (KK, Shilpa Rao)"),
    ("4vI3mOS9gIo", "Tu Hi Meri Shab Hai - Gangster (KK)"),

    # --- 90s Romantic Classics ---
    ("cNV5hLSa9H8", "Tujhe Dekha Toh - DDLJ (Lata Mangeshkar, Kumar Sanu)"),
    ("SBfPs-PMGTA", "Pehla Nasha - Jo Jeeta Wohi Sikandar (Udit Narayan, Sadhana Sargam)"),
    ("nrqKoe7Moe8", "Shaam Bhi Khoob Hai - Karz (Alka Yagnik, Kumar Sanu, Udit Narayan)"),

    # --- 70s & 80s Evergreen Old Hindi Classics ---
    ("AMuRRXCuy-4", "Pal Pal Dil Ke Paas - Blackmail (Kishore Kumar)"),
    ("fj4MnkljFXc", "Lag Ja Gale - Woh Kaun Thi (Lata Mangeshkar)"),
    ("otSbGQIYgpQ", "Tere Bina Zindagi Se - Aandhi (Lata Mangeshkar, Kishore Kumar)"),
    ("6yL7e60G17c", "Mere Sapno Ki Rani - Aradhana (Kishore Kumar)"),
    ("Z5D1dhTMclI", "Kya Hua Tera Wada - Hum Kisise Kum Naheen (Mohammed Rafi)"),
    ("XuCp0r3vhPQ", "Chura Liya Hai Tumne Jo Dil Ko - Yaadon Ki Baaraat (Asha Bhosle)"),
    ("DYfRjDlAiCM", "Ek Pyar Ka Naghma Hai - Shor (Lata Mangeshkar, Mukesh)"),
]

# Auto-discovery queries (used only after all curated songs are played)
DISCOVERY_QUERIES: List[str] = [
    "Arijit Singh romantic Hindi song official video T-Series",
    "Atif Aslam Bollywood romantic song official video",
    "KK hit Hindi song official video",
    "Shreya Ghoshal romantic Bollywood song official video",
    "Sonu Nigam evergreen Hindi song official video",
    "Jubin Nautiyal new Hindi song official video",
    "Vishal Mishra romantic Hindi song official video",
    "Darshan Raval Hindi love song official video",
    "90s Bollywood romantic song Udit Narayan Kumar Sanu official",
    "Kishore Kumar Lata Mangeshkar evergreen Hindi song Saregama",
    "Mohammed Rafi old classic Hindi song Saregama",
    "New Bollywood romantic song 2025 2026 T-Series Zee Music",
    "Pritam Bollywood hit romantic song Sony Music India",
    "AR Rahman Hindi romantic song official video",
    "Mohit Chauhan Bollywood hit song official video",
    "Rahat Fateh Ali Khan Bollywood romantic song official video",
    "Mithoon emotional Hindi song official video",
    "Emraan Hashmi hit romantic song official video",
]


def load_played_ids(history_path: Path) -> Set[str]:
    """Load previously played YouTube video IDs from disk."""
    if not history_path.exists():
        return set()
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(item) for item in data if item}
    except (json.JSONDecodeError, OSError):
        pass
    return set()


def save_played_ids(history_path: Path, played_ids: Set[str]) -> None:
    """Persist played YouTube video IDs so restarts never repeat songs."""
    try:
        history_path.write_text(
            json.dumps(sorted(played_ids), indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[WARN] History save nahi ho payi: {exc}")


def build_unique_curated_queue(played_ids: Set[str]) -> List[Tuple[str, str]]:
    """Return a shuffled, deduplicated list of unplayed curated songs."""
    seen: Set[str] = set()
    queue: List[Tuple[str, str]] = []
    for vid, title in CURATED_HINDI_SONGS:
        if vid not in seen and vid not in played_ids:
            seen.add(vid)
            queue.append((vid, title))
    random.shuffle(queue)
    return queue


def discover_more_hindi_songs(
    played_ids: Set[str],
    queued_ids: Set[str],
    query: str,
) -> List[Tuple[str, str]]:
    """
    Fetch additional unique YouTube Hindi song video IDs from YouTube search
    using only Python standard library (no pip install needed).
    Filters out jukeboxes/mashups/compilations and already-played IDs.
    """
    encoded_q = urllib.parse.quote_plus(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded_q}"
    req = urllib.request.Request(search_url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        print(f"[WARN] Auto-discovery search failed ({query}): {exc}")
        return []

    # Extract videoId + title pairs from YouTube's embedded JSON
    pattern = re.compile(
        r'"videoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"([^"]+)"\}\]',
        re.DOTALL,
    )
    skip_keywords = ("jukebox", "mashup", "nonstop", "non-stop", "1 hour", "2 hour", "top 20", "top 50", "top 100")

    discovered: List[Tuple[str, str]] = []
    local_seen: Set[str] = set()

    for vid, raw_title in pattern.findall(html):
        if vid in played_ids or vid in queued_ids or vid in local_seen:
            continue
        title = raw_title.replace("\\u0026", "&").replace('\\"', '"')
        lower_title = title.lower()
        if any(bad in lower_title for bad in skip_keywords):
            continue
        local_seen.add(vid)
        discovered.append((vid, title))

    random.shuffle(discovered)
    return discovered


def send_song_request(
    index: int,
    video_id: str,
    title: str,
    dry_run: bool = False,
) -> Dict[str, object]:
    """Send GET request to the user's API with the YouTube video ID."""
    url = API_BASE_URL.format(video_id=video_id)
    now = datetime.now().strftime("%H:%M:%S")

    if dry_run:
        print(f"[#{index:03d}] {now} | [DRY-RUN] {title} | ID: {video_id} -> {url}")
        return {"ok": True, "status": 200, "video_id": video_id}

    start = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            status = resp.getcode()
            body_preview = resp.read(160).decode("utf-8", errors="ignore").strip().replace("\n", " ")
            elapsed = time.monotonic() - start
            print(
                f"[#{index:03d}] {now} | OK ({status}) in {elapsed:.2f}s | "
                f"{title} | ID: {video_id}"
                + (f" | Resp: {body_preview[:80]}" if body_preview else "")
            )
            return {"ok": True, "status": status, "video_id": video_id}
    except urllib.error.HTTPError as exc:
        elapsed = time.monotonic() - start
        print(
            f"[#{index:03d}] {now} | HTTP {exc.code} in {elapsed:.2f}s | "
            f"{title} | ID: {video_id}"
        )
        return {"ok": False, "status": exc.code, "video_id": video_id}
    except Exception as exc:
        elapsed = time.monotonic() - start
        print(
            f"[#{index:03d}] {now} | ERROR in {elapsed:.2f}s | "
            f"{title} | ID: {video_id} | {exc}"
        )
        return {"ok": False, "status": None, "video_id": video_id}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Har 3.6s mein unique Hindi song YouTube ID API par bhejne wali script."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Har request ke beech ka gap seconds mein (default: {DEFAULT_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--no-auto-discover",
        action="store_true",
        help="Sirf built-in 53 curated Hindi songs chalao, extra YouTube discovery band rakho.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Purani played_hindi_songs.json history clear karke fresh start karo.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max kitne songs bhejne hain (0 = unlimited / jab tak unique songs milein).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Actual API request bheje bina test run karo.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.reset and HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
        print("[INFO] Played history reset kar di gayi hai.")

    played_ids = load_played_ids(HISTORY_FILE)
    queue = build_unique_curated_queue(played_ids)
    queued_ids = {vid for vid, _ in queue}

    discovery_queries = DISCOVERY_QUERIES.copy()
    random.shuffle(discovery_queries)
    query_idx = 0

    print("=" * 72)
    print("  Hindi Unique Song Auto-Requester")
    print(f"  API Template : {API_BASE_URL}")
    print(f"  Interval     : {args.interval}s")
    print(f"  Curated Left : {len(queue)} / {len(CURATED_HINDI_SONGS)} (Already Played: {len(played_ids)})")
    print(f"  Auto-Discover: {'ON' if not args.no_auto_discover else 'OFF'}")
    print("  Stop karne ke liye Ctrl+C dabayein.")
    print("=" * 72)

    sent_count = 0
    next_tick = time.monotonic()

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        try:
            while True:
                if args.limit > 0 and sent_count >= args.limit:
                    print(f"\n[DONE] Limit ({args.limit} unique songs) complete ho gayi.")
                    break

                # Refill queue from YouTube auto-discovery if curated list finishes
                if not queue:
                    if args.no_auto_discover:
                        print("\n[DONE] Saare unique curated songs play ho chuke hain! (--reset se dubara chala sakte ho)")
                        break

                    print("\n[INFO] Curated songs complete! Naye unique Hindi songs YouTube se fetch ho rahe hain...")
                    found_any = False
                    attempts = 0
                    while attempts < len(discovery_queries):
                        q = discovery_queries[query_idx % len(discovery_queries)]
                        query_idx += 1
                        attempts += 1
                        fresh = discover_more_hindi_songs(played_ids, queued_ids, q)
                        if fresh:
                            queue.extend(fresh)
                            queued_ids.update(vid for vid, _ in fresh)
                            print(f"[INFO] {len(fresh)} naye unique Hindi songs queue mein add kiye gaye.")
                            found_any = True
                            break
                    if not found_any:
                        print("[DONE] Koi aur naya unique song nahi mila. Script ruk rahi hai.")
                        break

                video_id, title = queue.pop()
                queued_ids.discard(video_id)

                # Double-check zero-duplicate invariant before firing
                if video_id in played_ids:
                    continue

                played_ids.add(video_id)
                if not args.dry_run:
                    save_played_ids(HISTORY_FILE, played_ids)

                sent_count += 1
                executor.submit(send_song_request, sent_count, video_id, title, args.dry_run)

                # Drift-free 3.6s scheduling
                next_tick += args.interval
                sleep_for = next_tick - time.monotonic()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_tick = time.monotonic()

        except KeyboardInterrupt:
            print(f"\n[STOPPED] User ne script band ki. Total unique songs requested: {sent_count}")
            sys.exit(0)


if __name__ == "__main__":
    main()
