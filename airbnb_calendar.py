import requests
import pandas as pd
from icalendar import Calendar
from datetime import datetime, date
import ace_tools_open as tools
import json
import os


def get_airbnb_ical(ical_url):
    response = requests.get(ical_url)
    if response.status_code == 200:
        return response.text
    else:
        print("Erro ao obter o calendário iCal.")
        return None


def load_cleaners():
    """Load cleaner assignments from JSON file"""
    filename = "~/.streamlit/cleaners.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []


def load_calendars():
    """Load cleaner assignments from JSON file"""
    filename = "calendars.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []


def load_bookings():
    """Load existing bookings from JSON file"""
    filename = "~/.streamlit/bookings.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {"flats": []}


def save_bookings(bookings_data):
    """Save bookings to JSON file"""
    filename = "~/.streamlit/bookings.json"
    with open(filename, "w") as f:
        json.dump(bookings_data, f, indent=2)


def parse_ical_data(flat, ical_text):
    calendar = Calendar.from_ical(ical_text)
    cleaning_schedule = []
    cleaning_interval = None

    # Load existing bookings
    bookings_data = load_bookings()

    # Find or create flat entry in bookings
    flat_entry = next((f for f in bookings_data["flats"] if f["flat"] == flat), None)
    if flat_entry is None:
        flat_entry = {"flat": flat, "bookings": []}
        bookings_data["flats"].append(flat_entry)

    # Get current bookings from iCal
    current_bookings = []
    events = sorted(calendar.walk("VEVENT"), key=lambda event: event.get("DTSTART").dt)

    today = pd.Timestamp.now().normalize()

    for event in events:
        booking = {
            "UID": str(event.get("UID")),
            "CheckIn": event.get("DTSTART").dt.strftime("%Y-%m-%d"),
            "CheckOut": event.get("DTEND").dt.strftime("%Y-%m-%d"),
        }
        current_bookings.append(booking)

    # Update flat bookings
    new_bookings = []
    existing_uids = {b["UID"] for b in current_bookings}
    current_bookings_dict = {b["UID"]: b for b in current_bookings}

    # First, process existing bookings
    for booking in flat_entry["bookings"]:
        if booking["UID"] in existing_uids:
            # Merge booking data: keep Cleaner from existing, dates from current
            current_booking = current_bookings_dict[booking["UID"]]
            new_booking = {
                "UID": booking["UID"],
                "CheckIn": current_booking["CheckIn"],
                "CheckOut": current_booking["CheckOut"],
                "Cleaner": booking.get("Cleaner"),  # Preserve existing Cleaner
            }
            new_bookings.append(new_booking)
        elif pd.to_datetime(booking["CheckOut"]) <= today:
            # Keep past bookings as they are
            new_bookings.append(booking)

    # Add new bookings that weren't in flat_entry
    existing_uids = {b["UID"] for b in new_bookings}
    for booking in current_bookings:
        if booking["UID"] not in existing_uids:
            new_bookings.append(
                {
                    "UID": booking["UID"],
                    "CheckIn": booking["CheckIn"],
                    "CheckOut": booking["CheckOut"],
                    "Cleaner": None,
                }
            )

    flat_entry["bookings"] = new_bookings
    save_bookings(bookings_data)

    booking_count = 0
    for booking in new_bookings:
        booking_count += 1
        start = pd.to_datetime(booking["CheckIn"]).date()
        if cleaning_interval is not None:
            if booking_count < len(new_bookings):
                cleaning_interval["NextCheckIn"] = start
                cleaning_interval["Cleaner"] = booking["Cleaner"]
            if end == start:
                cleaning_interval["HotBed"] = True
            cleaning_schedule.append(cleaning_interval)
        end = pd.to_datetime(booking["CheckOut"]).date()
        cleaning_interval = {
            "Flat": flat,
            "CheckOut": end,
            "NextCheckIn": None,
            "Cleaner": None,
            "HotBed": False,
        }

    # for event in events:
    #     event_count += 1
    #     start = event.get("DTSTART").dt
    #     if cleaning_interval is not None:
    #         if event_count < len(events):
    #             cleaning_interval["NextCheckIn"] = start
    #         if end == start:
    #             cleaning_interval["HotBed"] = True
    #         cleaning_schedule.append(cleaning_interval)
    #     end = event.get("DTEND").dt
    #     cleaning_interval = {
    #         "Flat": flat,
    #         "CheckOut": end,
    #         "NextCheckIn": None,
    #         "Cleaner": None,
    #         "HotBed": False,
    #     }

    return cleaning_schedule


def cleaning_schedule(ical_calendars, months=3):
    schedule = []
    for ical_calendar in ical_calendars:
        ical_text = get_airbnb_ical(ical_calendar["url"])
        if not ical_text:
            return None
        flat_cleaning_schedule = parse_ical_data(ical_calendar["flat"], ical_text)
        schedule.extend(flat_cleaning_schedule)

    df = pd.DataFrame(schedule)
    df["CheckOut"] = pd.to_datetime(df["CheckOut"])
    df["NextCheckIn"] = pd.to_datetime(df["NextCheckIn"])

    # Filter for future check-ins or NaT values
    today = pd.Timestamp.now().normalize()
    df = df[(df["NextCheckIn"].isna()) | (df["NextCheckIn"] >= today)]

    df = df.fillna("")
    df = df.sort_values(
        by=["NextCheckIn", "CheckOut", "Flat", "Cleaner"], na_position="last"
    )
    df["NextCheckIn"] = df["NextCheckIn"].astype(str).replace("NaT", "")

    return df


def save_cleaner_info(ap, entrada, fx):
    """Save cleaner information to bookings.json"""
    # Load existing bookings
    filename = "~/.streamlit/bookings.json"
    if not os.path.exists(filename):
        raise FileNotFoundError("Arquivo de bookings não encontrado")

    with open(filename, "r") as f:
        bookings_data = json.load(f)

    # Find flat entry
    flat_entry = next((f for f in bookings_data["flats"] if f["flat"] == ap), None)
    if flat_entry is None:
        raise ValueError(f"Apartamento {ap} não encontrado")

    # Convert date to match bookings.json format
    try:
        entrada_date = pd.to_datetime(entrada.split()[0]).strftime("%Y-%m-%d")
    except:
        raise ValueError("Data de entrada inválida")

    # Find booking by CheckIn date and update Cleaner
    for booking in flat_entry["bookings"]:
        if booking["CheckIn"] == entrada_date:
            booking["Cleaner"] = fx.replace("🔥 ", "").replace("🔥", "").strip()
            # Save updated bookings
            with open(filename, "w") as f:
                json.dump(bookings_data, f, indent=2)
            return True

    raise ValueError("Reserva não encontrada")


if __name__ == "__main__":
    ical_calendars = load_calendars()

    df_cleaning = cleaning_schedule(ical_calendars)

    if df_cleaning is not None:

        tools.display_dataframe_to_user("Limpeza dos Airbnbs", df_cleaning)
