import requests
import pandas as pd
from icalendar import Calendar
from datetime import datetime, date
import ace_tools_open as tools
import os
from pymongo import MongoClient
import urllib.parse
import streamlit as st


def connect_mongo():
    try:
        # Connect to MongoDB
        # Load environment variables
        db_user = st.secrets["DB_USER"]
        db_password = urllib.parse.quote_plus(st.secrets["DB_PASSWORD"])

        # Connect to MongoDB
        connection_string = f"mongodb+srv://{db_user}:{db_password}@cluster0.x29gn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        client = MongoClient(connection_string)
        return client
    except Exception as e:
        print(f"Error loading calendars from MongoDB: {str(e)}")
        return None


def get_airbnb_ical(ical_url):
    response = requests.get(ical_url)
    if response.status_code == 200:
        return response.text
    else:
        print("Erro ao obter o calendário iCal.")
        return None


# def load_cleaners():
#     """Load cleaner assignments from JSON file"""
#     filename = "~/.streamlit/cleaners.json"
#     if os.path.exists(filename):
#         with open(filename, "r") as f:
#             return json.load(f)
#     return []


def load_calendars():
    """Load calendar assignments from MongoDB"""
    try:
        client = connect_mongo()

        # Get database and collection
        db = client["airbnb"]
        calendars = db.calendars.find({}, {"_id": 0})  # Exclude MongoDB _id field

        # Convert cursor to list
        calendar_list = list(calendars)

        # Close connection
        client.close()

        return calendar_list
    except Exception as e:
        print(f"Error loading calendars: {str(e)}")
        return []


def load_bookings(flat: str = None):
    """Load existing bookings from MongoDB

    Args:
        flat (str, optional): Flat number to filter bookings. Defaults to None.

    Returns:
        list: List of booking documents from MongoDB, sorted by CheckIn date
    """
    try:
        client = connect_mongo()
        if not client:
            raise ConnectionError("Failed to connect to MongoDB")

        # Get database and collection
        db = client["airbnb"]

        # Create filter based on flat parameter
        filter_query = {"_id": 0}  # Exclude MongoDB _id field
        if flat:
            filter_query["flat"] = flat

        # Query with filter and sort by CheckIn
        bookings = db.bookings.find({"flat": flat} if flat else {}, {"_id": 0}).sort(
            "bookings.CheckIn", 1
        )  # 1 for ascending order

        # Convert cursor to list and sort bookings within each document
        booking_list = list(bookings)
        for doc in booking_list:
            if "bookings" in doc:
                doc["bookings"].sort(key=lambda x: x["CheckIn"])

        # Close connection
        client.close()

        return booking_list

    except Exception as e:
        print(f"Error loading bookings: {str(e)}")
        return []


def save_bookings(flat_entry):
    try:
        """Save bookings to MongoDB"""
        client = connect_mongo()

        # Get database and collection
        db = client["airbnb"]

        # Replace document for this flat
        result = db.bookings.replace_one(
            {"flat": flat_entry["flat"]},  # filter
            flat_entry,  # new document
            upsert=True,  # create if doesn't exist
        )

        # Close connection
        client.close()

        return result.acknowledged

    except Exception as e:
        print(f"Error saving bookings to MongoDB: {str(e)}")
        return False


def parse_ical_data(flat, ical_text):
    calendar = Calendar.from_ical(ical_text)
    cleaning_schedule = []
    cleaning_interval = None

    # Load existing bookings
    bookings_data = load_bookings(flat)

    # Find or create flat entry in bookings
    flat_entry = next((f for f in bookings_data if f["flat"] == flat), None)
    if flat_entry is None:
        flat_entry = {"flat": flat, "bookings": []}
        bookings_data.append(flat_entry)

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
    save_bookings(flat_entry)

    booking_count = 0
    for booking in new_bookings:
        booking_count += 1
        start = pd.to_datetime(booking["CheckIn"]).date()
        if cleaning_interval is not None:
            if booking_count < len(new_bookings):
                cleaning_interval["NextCheckIn"] = start
                try:
                    cleaning_interval["Cleaner"] = booking["Cleaner"]
                except:
                    cleaning_interval["Cleaner"] = None
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

    # Create Sorting column based on conditions
    df["Sorting"] = df.apply(
        lambda row: row["CheckOut"]
        if pd.isna(row["NextCheckIn"])
        else row["NextCheckIn"],
        axis=1,
    )

    df = df.fillna("")
    df = df.sort_values(
        by=["Sorting", "CheckOut", "Flat", "Cleaner"], na_position="last"
    )
    df["NextCheckIn"] = df["NextCheckIn"].astype(str).replace("NaT", "")
    df = df.drop("Sorting", axis=1)  # Remove temporary sorting column

    return df


def save_cleaner_info(flat, entrada, fx):
    """Save cleaner information to MongoDB"""
    # Load existing bookings
    bookings_data = load_bookings(flat)

    # Find flat entry
    flat_entry = next((f for f in bookings_data if f["flat"] == flat), None)
    if flat_entry is None:
        raise ValueError(f"Apartamento {flat} não encontrado")

    # Convert date to match bookings.json format
    try:
        entrada_date = pd.to_datetime(entrada.split()[0]).strftime("%Y-%m-%d")
    except:
        raise ValueError(f"Data de entrada inválida: {entrada}")

    # Find booking by CheckIn date and update Cleaner
    for booking in flat_entry["bookings"]:
        if booking["CheckIn"] == entrada_date:
            booking["Cleaner"] = fx.replace("🔥 ", "").replace("🔥", "").strip()
            return save_bookings(flat_entry)

    raise ValueError("Reserva não encontrada")


if __name__ == "__main__":
    ical_calendars = load_calendars()

    df_cleaning = cleaning_schedule(ical_calendars)

    if df_cleaning is not None:

        tools.display_dataframe_to_user("Limpeza dos Airbnbs", df_cleaning)
