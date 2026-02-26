#!/usr/bin/env python3
"""
XMUM eServices Auto Booking Script
Automatically login and book library rooms.

First-time setup:
  python3 auto_booking.py --setup

Credential priority:
  1. Environment variables (XMUM_USERNAME, XMUM_PASSWORD, XMUM_GEMINI_KEY)
  2. Config file (~/.xmu_booking.json, saved via --setup)
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import google.generativeai as genai
from PIL import Image
import io
import os
import argparse
import sys
import json
import getpass

# ── Config file path ──────────────────────────────────────────────────────────
CONFIG_PATH = os.path.expanduser("~/.xmu_booking.json")
BUILTIN_GEMINI_KEY = ""  # Get your free key at https://aistudio.google.com/apikey

def load_config():
    """Load saved credentials from config file."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def run_setup():
    """Interactive first-time credential setup."""
    print("=" * 60)
    print("XMUM Booking — First-time Setup")
    print("=" * 60)
    print("Credentials will be saved to ~/.xmu_booking.json")
    print("(readable only by you, never uploaded anywhere)\n")

    username = input("Campus ID: ").strip()
    password = getpass.getpass("Password: ")
    if not username or not password:
        print("✗ Username and password cannot be empty.")
        sys.exit(1)

    gemini_key = input(
        f"Gemini API Key [press Enter to use built-in key]: "
    ).strip()
    if not gemini_key:
        gemini_key = BUILTIN_GEMINI_KEY
        print("  → Using built-in Gemini API Key")

    config = {"username": username, "password": password, "gemini_key": gemini_key}
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)
    print(f"\n✓ Saved to {CONFIG_PATH}")
    print("\nSetup complete! You can now run:")
    print("  python3 auto_booking.py")
    sys.exit(0)

# ── Load credentials (env vars override config file) ─────────────────────────
_cfg = load_config()
GEMINI_API_KEY = os.environ.get("XMUM_GEMINI_KEY") or _cfg.get("gemini_key") or BUILTIN_GEMINI_KEY
USERNAME       = os.environ.get("XMUM_USERNAME")   or _cfg.get("username", "")
PASSWORD       = os.environ.get("XMUM_PASSWORD")   or _cfg.get("password", "")

BASE_URL = "https://eservices.xmu.edu.my"

# ── Room type table IDs ───────────────────────────────────────────────────────
ROOM_TABLE_IDS = {
    "silent":  "silent_study_room_table",       # Silent Study Rooms    N201-N214 (cap 2)
    "study":   "study_room_table",              # Study Rooms           S221-S234 (cap 2)
    "group":   "group_discussion_room_table",   # Group Discussion Rooms E231-E236, W241-W246 (cap 4)
    "success": "student_success_room_table",    # Student Success Rooms  Room 1-3 (cap 4/10)
}

# ── Default booking times ─────────────────────────────────────────────────────
WEEKDAY_START = "19:00"
WEEKDAY_END   = "21:00"
WEEKEND_START = "15:00"
WEEKEND_END   = "17:00"


def check_credentials():
    missing = []
    if not USERNAME:
        missing.append("XMUM_USERNAME")
    if not PASSWORD:
        missing.append("XMUM_PASSWORD")
    if missing:
        print("✗ Missing environment variables:", ", ".join(missing))
        print("  See SETUP.md for configuration instructions.")
        sys.exit(1)


def recognize_captcha(image_content):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-flash-latest")
        img = Image.open(io.BytesIO(image_content))
        prompt = ("Please analyze this CAPTCHA image and return ONLY the "
                  "text/characters you see. No explanations, just the characters.")
        response = model.generate_content([prompt, img])
        return response.text.strip()
    except Exception as e:
        print(f"✗ Captcha recognition error: {e}")
        return None


def login(session):
    print("=" * 60)
    print("Logging in to XMUM eServices...")
    print("=" * 60)
    try:
        print("\n[1/4] Fetching login page...")
        login_page = session.get(BASE_URL, timeout=10)
        login_page.raise_for_status()

        soup = BeautifulSoup(login_page.text, "html.parser")
        captcha_img = soup.find("img", src=lambda x: x and "captcha" in x.lower())
        if not captcha_img:
            print("✗ Could not find captcha image")
            return False

        captcha_url = captcha_img["src"]
        if not captcha_url.startswith("http"):
            captcha_url = BASE_URL + captcha_url
        print("✓ Login page loaded")

        print("\n[2/4] Downloading captcha...")
        captcha_response = session.get(captcha_url, timeout=10)
        captcha_response.raise_for_status()
        print(f"✓ Captcha downloaded ({len(captcha_response.content)} bytes)")

        print("\n[3/4] Recognizing captcha with Gemini API...")
        captcha_text = recognize_captcha(captcha_response.content)
        if not captcha_text:
            print("✗ Failed to recognize captcha")
            return False
        print(f"✓ Captcha recognized: {captcha_text}")

        print("\n[4/4] Submitting login credentials...")
        csrf_input = soup.find("input", {"name": "_token"})
        login_data = {
            "campus-id": USERNAME,
            "password":  PASSWORD,
            "captcha":   captcha_text,
        }
        if csrf_input:
            login_data["_token"] = csrf_input.get("value")

        login_response = session.post(
            BASE_URL + "/authenticate",
            data=login_data,
            timeout=10,
            allow_redirects=True,
        )

        if "logout" in login_response.text.lower() or "dashboard" in login_response.text.lower():
            print("✓ Login successful!")
            return True
        elif "captcha" in login_response.text.lower() and "incorrect" in login_response.text.lower():
            print("✗ Incorrect captcha")
            return False
        elif "password" in login_response.text.lower() and "incorrect" in login_response.text.lower():
            print("✗ Incorrect username or password")
            return False
        else:
            print("✗ Login failed (unknown reason)")
            print("  Response URL:", login_response.url)
            return False

    except Exception as e:
        print(f"✗ Login error: {e}")
        return False


def extract_csrf_token(session):
    try:
        response = session.get(
            BASE_URL + "/space-booking/library-space-booking", timeout=10
        )
        soup = BeautifulSoup(response.text, "html.parser")
        meta = soup.find("meta", {"name": "csrf-token"})
        if meta:
            return meta.get("content")
        inp = soup.find("input", {"name": "_token"})
        if inp:
            return inp.get("value")
        return None
    except Exception as e:
        print(f"✗ Error extracting CSRF token: {e}")
        return None


def get_available_rooms(session, booking_date, csrf_token,
                        room_type="group", any_time=False,
                        target_start=None, target_end=None):
    table_id = ROOM_TABLE_IDS.get(room_type, ROOM_TABLE_IDS["group"])
    try:
        response = session.get(
            BASE_URL + "/space-booking/library-space-booking",
            params={"bookingDate": booking_date},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-TOKEN": csrf_token,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        soup = BeautifulSoup(data.get("html", ""), "html.parser")

        table = soup.find("table", {"id": table_id})
        if not table:
            print(f"  ✗ Room table '{table_id}' not found in response")
            return []

        available, all_slots = [], []
        for btn in table.find_all("button", class_="booking-btn"):
            if btn.has_attr("disabled"):
                continue
            info = {
                "room_id":   btn.get("data-booking-room-id"),
                "room_name": btn.get("data-booking-room-name"),
                "start_time": btn.get("data-booking-start-time"),
                "end_time":   btn.get("data-booking-end-time"),
                "date":       btn.get("data-booking-date"),
            }
            all_slots.append(f"{info['room_name']} ({info['start_time']}-{info['end_time']})")
            if any_time:
                available.append(info)
                print(f"  ✓ Available: {info['room_name']} ({info['start_time']}-{info['end_time']})")
            elif info["start_time"] == target_start and info["end_time"] == target_end:
                available.append(info)
                print(f"  ✓ Target slot: {info['room_name']} ({info['start_time']}-{info['end_time']})")

        if not available and not any_time and all_slots:
            print(f"  ℹ No {target_start}-{target_end} slots. Available ({len(all_slots)}):")
            for s in all_slots[:5]:
                print(f"     - {s}")
            if len(all_slots) > 5:
                print(f"     ... and {len(all_slots) - 5} more")

        return available

    except Exception as e:
        print(f"  ✗ Error getting rooms: {e}")
        return []


def book_room(session, room_info, csrf_token):
    try:
        response = session.post(
            BASE_URL + "/space-booking/book-library-room",
            data={
                "_token":           csrf_token,
                "bookingRoomId":    room_info["room_id"],
                "bookingDate":      room_info["date"],
                "bookingStartTime": room_info["start_time"],
                "bookingEndTime":   room_info["end_time"],
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-TOKEN": csrf_token,
            },
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

        print(f"  [*] Booking: {room_info['room_name']}  {room_info['date']}  "
              f"{room_info['start_time']}-{room_info['end_time']}")

        if result.get("code") == 200:
            print(f"  ✓ Booking successful! {result.get('message', '')}")
            return True
        else:
            print(f"  ✗ Booking failed: {result.get('message', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"  ✗ Error booking room: {e}")
        return False


def book_rooms(session, target_date=None, any_time=False, room_type="group"):
    print("\n" + "=" * 60)
    print("Starting room booking process...")
    print("=" * 60)

    csrf_token = extract_csrf_token(session)
    if not csrf_token:
        print("✗ Failed to extract CSRF token")
        return False
    print("✓ CSRF token obtained")

    # Determine dates
    if target_date:
        try:
            booking_date = datetime.strptime(target_date, "%Y-%m-%d")
            dates_to_book = [booking_date]
            print(f"\n[*] Booking for specified date: {target_date} (any available time)")
        except ValueError:
            print(f"✗ Invalid date format: {target_date}. Use YYYY-MM-DD")
            return False
    else:
        today = datetime.now()
        booking_date = today + timedelta(days=2)
        dates_to_book = [booking_date]
        day_type = "weekday" if booking_date.weekday() < 5 else "weekend"
        print(f"\n[*] Auto mode: booking for {booking_date.strftime('%Y-%m-%d, %A')} ({day_type})")

    results = []
    for bd in dates_to_book:
        date_str  = bd.strftime("%Y-%m-%d")
        day_name  = bd.strftime("%A")
        is_weekend = bd.weekday() >= 5

        print(f"\n{'=' * 60}")
        print(f"Processing {day_name}, {date_str}  [room type: {room_type}]")
        print(f"{'=' * 60}")

        if any_time:
            t_start, t_end = None, None
        elif is_weekend:
            t_start, t_end = WEEKEND_START, WEEKEND_END
            print(f"  Time target: {t_start}-{t_end} (weekend)")
        else:
            t_start, t_end = WEEKDAY_START, WEEKDAY_END
            print(f"  Time target: {t_start}-{t_end} (weekday)")

        rooms = get_available_rooms(
            session, date_str, csrf_token,
            room_type=room_type, any_time=any_time,
            target_start=t_start, target_end=t_end,
        )

        if rooms:
            label = f"{len(rooms)} room(s)" + (f" for {t_start}-{t_end}" if not any_time else "")
            print(f"  ✓ Found {label}")
            success = book_room(session, rooms[0], csrf_token)
            results.append({"date": date_str, "day": day_name,
                            "status": "success" if success else "failed",
                            "room": rooms[0]["room_name"] if success else None})
            time.sleep(2)
        else:
            print(f"  ✗ No available rooms found")
            results.append({"date": date_str, "day": day_name,
                            "status": "no_rooms", "room": None})
        time.sleep(1)

    print(f"\n{'=' * 60}")
    print("BOOKING SUMMARY")
    print(f"{'=' * 60}")
    for r in results:
        if r["status"] == "success":
            print(f"✓ {r['day']}, {r['date']}: BOOKED → {r['room']}")
        elif r["status"] == "no_rooms":
            print(f"○ {r['day']}, {r['date']}: NO AVAILABLE ROOMS")
        else:
            print(f"✗ {r['day']}, {r['date']}: FAILED")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="XMUM Auto Booking — books library rooms automatically"
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="First-time setup: save your campus ID and password locally.",
    )
    parser.add_argument(
        "--date",
        help="Book a specific date (YYYY-MM-DD). Books ANY available slot.",
    )
    parser.add_argument(
        "--room-type",
        choices=list(ROOM_TABLE_IDS.keys()),
        default="group",
        help=f"Room type to book. Options: {list(ROOM_TABLE_IDS.keys())}. Default: group",
    )
    args = parser.parse_args()

    if args.setup:
        run_setup()  # exits after saving

    check_credentials()

    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "XMUM Auto Booking System" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    print(f"User:      {USERNAME}")
    print(f"Room type: {args.room_type}")
    if args.date:
        print(f"Mode:      Manual → {args.date} (any available time)")
        any_time_mode = True
    else:
        print(f"Mode:      Auto (2 days from now)")
        print(f"           Weekday {WEEKDAY_START}-{WEEKDAY_END} / Weekend {WEEKEND_START}-{WEEKEND_END}")
        any_time_mode = False

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    for attempt in range(1, 4):
        print(f"\nLogin attempt {attempt}/3")
        if login(session):
            break
        if attempt < 3:
            print("Retrying in 2 seconds...")
            time.sleep(2)
    else:
        print("\n✗ Failed to login after 3 attempts")
        sys.exit(1)

    book_rooms(session, target_date=args.date,
               any_time=any_time_mode, room_type=args.room_type)

    print("\n" + "=" * 60)
    print("Session complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
