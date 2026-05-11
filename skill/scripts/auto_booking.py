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
from google import genai
from PIL import Image
import io
import os
import argparse
import sys
import json
import getpass

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH      = os.path.expanduser("~/.xmu_booking.json")
BUILTIN_GEMINI_KEY = ""  # Get your free key: https://aistudio.google.com/apikey
BASE_URL         = "https://eservices.xmu.edu.my"

# ── Room type table IDs ───────────────────────────────────────────────────────
ROOM_TABLE_IDS = {
    "silent":  "silent_study_room_table",       # N201-N214  cap 2  L2
    "study":   "study_room_table",              # S221-S234  cap 2  L2
    "group":   "group_discussion_room_table",   # E231-E236, W241-W246  cap 4  L2
    "success": "student_success_room_table",    # Room 1-3   cap 4/10  L3
}

# ── Available time slots (both weekday and weekend share the same 2-hr slots) ─
# Weekday:  09:00-11:00  11:00-13:00  13:00-15:00  15:00-17:00  17:00-19:00  19:00-21:00
# Weekend:  09:00-11:00  11:00-13:00  13:00-15:00  15:00-17:00
VALID_SLOTS = [
    ("09:00", "11:00"),
    ("11:00", "13:00"),
    ("13:00", "15:00"),
    ("15:00", "17:00"),
    ("17:00", "19:00"),  # weekday only
    ("19:00", "21:00"),  # weekday only
]

# Default preferences (tried in order, first available wins)
DEFAULT_WEEKDAY_TIMES = ["19:00-21:00", "17:00-19:00", "15:00-17:00"]
DEFAULT_WEEKEND_TIMES = ["15:00-17:00", "13:00-15:00", "11:00-13:00"]


def parse_time_slots(time_str):
    """Parse comma-separated 'HH:MM-HH:MM' into list of (start, end) tuples."""
    slots = []
    for s in time_str.split(","):
        s = s.strip()
        parts = s.split("-")
        if len(parts) == 2:
            slots.append((parts[0].strip(), parts[1].strip()))
    return slots


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def run_setup():
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

    gemini_key = input("Gemini API Key (https://aistudio.google.com/apikey): ").strip()
    if not gemini_key:
        print("✗ Gemini API Key is required for captcha recognition.")
        sys.exit(1)

    config = {"username": username, "password": password, "gemini_key": gemini_key}
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)
    print(f"\n✓ Saved to {CONFIG_PATH}")
    print("\nSetup complete! You can now run:")
    print("  python3 auto_booking.py")
    sys.exit(0)


# ── Load credentials ──────────────────────────────────────────────────────────
_cfg           = load_config()
GEMINI_API_KEY = os.environ.get("XMUM_GEMINI_KEY") or _cfg.get("gemini_key") or BUILTIN_GEMINI_KEY
USERNAME       = os.environ.get("XMUM_USERNAME")   or _cfg.get("username", "")
PASSWORD       = os.environ.get("XMUM_PASSWORD")   or _cfg.get("password", "")


def check_credentials():
    missing = []
    if not USERNAME:
        missing.append("XMUM_USERNAME")
    if not PASSWORD:
        missing.append("XMUM_PASSWORD")
    if not GEMINI_API_KEY:
        missing.append("XMUM_GEMINI_KEY")
    if missing:
        print("✗ Missing credentials:", ", ".join(missing))
        print("  Run: python3 auto_booking.py --setup")
        sys.exit(1)


def recognize_captcha(image_content):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        img = Image.open(io.BytesIO(image_content))
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=["Return ONLY the captcha characters, no explanations.", img],
        )
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
            return False
        print(f"✓ Captcha recognized: {captcha_text}")

        print("\n[4/4] Submitting login credentials...")
        csrf_input = soup.find("input", {"name": "_token"})
        login_data = {"campus-id": USERNAME, "password": PASSWORD, "captcha": captcha_text}
        if csrf_input:
            login_data["_token"] = csrf_input.get("value")

        r = session.post(BASE_URL + "/authenticate", data=login_data,
                         timeout=10, allow_redirects=True)

        if "logout" in r.text.lower() or "dashboard" in r.text.lower():
            print("✓ Login successful!")
            return True
        elif "captcha" in r.text.lower() and "incorrect" in r.text.lower():
            print("✗ Incorrect captcha")
        elif "password" in r.text.lower() and "incorrect" in r.text.lower():
            print("✗ Incorrect username or password")
        else:
            print("✗ Login failed  URL:", r.url)
        return False

    except Exception as e:
        print(f"✗ Login error: {e}")
        return False


def extract_csrf_token(session):
    try:
        response = session.get(BASE_URL + "/space-booking/library-space-booking", timeout=10)
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
                        room_type="group", target_start=None, target_end=None):
    """
    Return available rooms for the given date.
    If target_start/end is None, return ALL available rooms (any time).
    """
    table_id = ROOM_TABLE_IDS.get(room_type, ROOM_TABLE_IDS["group"])
    try:
        response = session.get(
            BASE_URL + "/space-booking/library-space-booking",
            params={"bookingDate": booking_date},
            headers={"X-Requested-With": "XMLHttpRequest", "X-CSRF-TOKEN": csrf_token},
            timeout=10,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.json().get("html", ""), "html.parser")

        table = soup.find("table", {"id": table_id})
        if not table:
            print(f"  ✗ Table '{table_id}' not found")
            return []

        available = []
        for btn in table.find_all("button", class_="booking-btn"):
            if btn.has_attr("disabled"):
                continue
            info = {
                "room_id":    btn.get("data-booking-room-id"),
                "room_name":  btn.get("data-booking-room-name"),
                "start_time": btn.get("data-booking-start-time"),
                "end_time":   btn.get("data-booking-end-time"),
                "date":       btn.get("data-booking-date"),
            }
            if target_start is None:  # any time
                available.append(info)
            elif info["start_time"] == target_start and info["end_time"] == target_end:
                available.append(info)

        return available

    except Exception as e:
        print(f"  ✗ Error getting rooms: {e}")
        return []


def book_room(session, room_info, csrf_token):
    try:
        r = session.post(
            BASE_URL + "/space-booking/book-library-room",
            data={
                "_token":           csrf_token,
                "bookingRoomId":    room_info["room_id"],
                "bookingDate":      room_info["date"],
                "bookingStartTime": room_info["start_time"],
                "bookingEndTime":   room_info["end_time"],
            },
            headers={"X-Requested-With": "XMLHttpRequest", "X-CSRF-TOKEN": csrf_token},
            timeout=10,
        )
        r.raise_for_status()
        result = r.json()
        print(f"  [*] {room_info['room_name']}  {room_info['date']}  "
              f"{room_info['start_time']}-{room_info['end_time']}")
        if result.get("code") == 200:
            print(f"  ✓ Booking successful!")
            return True
        else:
            print(f"  ✗ {result.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"  ✗ Error booking room: {e}")
        return False


def book_rooms(session, target_date=None, time_prefs=None, room_type="group"):
    """
    time_prefs: list of (start, end) tuples tried in order.
                None means try ALL available slots (any time).
    """
    print("\n" + "=" * 60)
    print("Starting room booking process...")
    print("=" * 60)

    csrf_token = extract_csrf_token(session)
    if not csrf_token:
        print("✗ Failed to extract CSRF token")
        return False
    print("✓ CSRF token obtained")

    if target_date:
        try:
            booking_date = datetime.strptime(target_date, "%Y-%m-%d")
            dates_to_book = [booking_date]
            print(f"\n[*] Booking for specified date: {target_date}")
        except ValueError:
            print(f"✗ Invalid date format: {target_date}. Use YYYY-MM-DD")
            return False
    else:
        booking_date = datetime.now() + timedelta(days=2)
        dates_to_book = [booking_date]
        day_type = "weekday" if booking_date.weekday() < 5 else "weekend"
        print(f"\n[*] Auto mode: {booking_date.strftime('%Y-%m-%d, %A')} ({day_type})")

    results = []
    for bd in dates_to_book:
        date_str   = bd.strftime("%Y-%m-%d")
        day_name   = bd.strftime("%A")
        is_weekend = bd.weekday() >= 5

        print(f"\n{'=' * 60}")
        print(f"{day_name}, {date_str}  [room: {room_type}]")
        print(f"{'=' * 60}")

        # Determine time preference list for this day
        if time_prefs is not None:
            slots_to_try = time_prefs  # user-specified
        elif is_weekend:
            slots_to_try = parse_time_slots(",".join(DEFAULT_WEEKEND_TIMES))
        else:
            slots_to_try = parse_time_slots(",".join(DEFAULT_WEEKDAY_TIMES))

        any_time = (slots_to_try == [])

        if any_time:
            print("  Time: any available slot")
        else:
            prefs_str = ", ".join(f"{s}-{e}" for s, e in slots_to_try)
            print(f"  Time preference: {prefs_str}")

        booked = False
        if any_time:
            rooms = get_available_rooms(session, date_str, csrf_token, room_type=room_type)
            if rooms:
                booked = book_room(session, rooms[0], csrf_token)
        else:
            for t_start, t_end in slots_to_try:
                rooms = get_available_rooms(session, date_str, csrf_token,
                                            room_type=room_type,
                                            target_start=t_start, target_end=t_end)
                if rooms:
                    print(f"  ✓ Found {len(rooms)} room(s) for {t_start}-{t_end}")
                    booked = book_room(session, rooms[0], csrf_token)
                    break
                else:
                    print(f"  ○ No rooms for {t_start}-{t_end}, trying next...")

        results.append({
            "date": date_str, "day": day_name,
            "status": "success" if booked else ("failed" if any([
                get_available_rooms(session, date_str, csrf_token, room_type=room_type,
                                    target_start=s, target_end=e)
                for s, e in (slots_to_try or [])
            ]) else "no_rooms"),
            "room": None
        })
        time.sleep(1)

    print(f"\n{'=' * 60}")
    print("BOOKING SUMMARY")
    print(f"{'=' * 60}")
    for r in results:
        icon = "✓" if r["status"] == "success" else ("○" if r["status"] == "no_rooms" else "✗")
        print(f"{icon} {r['day']}, {r['date']}: {r['status'].upper()}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="XMUM Auto Booking — books library rooms automatically"
    )
    parser.add_argument("--setup", action="store_true",
                        help="First-time setup: save credentials locally.")
    parser.add_argument("--date",
                        help="Book a specific date (YYYY-MM-DD).")
    parser.add_argument("--room-type", choices=list(ROOM_TABLE_IDS.keys()), default="group",
                        help="Room type. Options: silent, study, group (default), success")
    parser.add_argument("--time",
                        help=(
                            "Comma-separated time preferences in order, e.g. '19:00-21:00,17:00-19:00'. "
                            "Script tries each slot in order until one is available. "
                            f"Weekday default: {','.join(DEFAULT_WEEKDAY_TIMES)}  "
                            f"Weekend default: {','.join(DEFAULT_WEEKEND_TIMES)}"
                        ))
    args = parser.parse_args()

    if args.setup:
        run_setup()

    check_credentials()

    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 14 + "XMUM Auto Booking System" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    print(f"\nUser:      {USERNAME}")
    print(f"Room type: {args.room_type}")

    # Resolve time preferences
    if args.time:
        time_prefs = parse_time_slots(args.time)
        print(f"Time pref: {args.time}")
        any_time_mode = False
    elif args.date:
        time_prefs = []  # any time when date is manually specified
        print(f"Mode:      Manual → {args.date} (any available time)")
        any_time_mode = True
    else:
        time_prefs = None  # use day-based defaults
        print(f"Mode:      Auto (2 days from now)")
        print(f"           Weekday default: {', '.join(DEFAULT_WEEKDAY_TIMES)}")
        print(f"           Weekend default: {', '.join(DEFAULT_WEEKEND_TIMES)}")
        any_time_mode = False

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

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

    if any_time_mode:
        book_rooms(session, target_date=args.date, time_prefs=[], room_type=args.room_type)
    else:
        book_rooms(session, target_date=args.date, time_prefs=time_prefs, room_type=args.room_type)

    print("\n" + "=" * 60)
    print("Session complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
