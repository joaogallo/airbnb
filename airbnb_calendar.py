import requests
import pandas as pd
from icalendar import Calendar
from datetime import datetime, date


def get_airbnb_ical(ical_url):
    response = requests.get(ical_url)
    if response.status_code == 200:
        return response.text
    else:
        print("Erro ao obter o calendário iCal.")
        return None


def parse_ical_data(flat, ical_text):
    calendar = Calendar.from_ical(ical_text)
    cleaning_schedule = []
    cleaning_interval = None

    # Criar uma lista de eventos e ordenar por DTSTART
    events = sorted(calendar.walk("VEVENT"), key=lambda event: event.get("DTSTART").dt)
    event_count = 0
    for event in events:
        event_count += 1
        start = event.get("DTSTART").dt
        if cleaning_interval is not None:
            if event_count < len(events):
                cleaning_interval["NextCheckIn"] = start
            if end == start:
                cleaning_interval["HotBed"] = True
            cleaning_schedule.append(cleaning_interval)
        end = event.get("DTEND").dt
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
    df = df.fillna("")
    df = df.sort_values(by=["NextCheckIn", "CheckOut", "Flat"], na_position="last")
    df["NextCheckIn"] = df["NextCheckIn"].astype(str).replace("NaT", "")

    return df


if __name__ == "__main__":
    ical_calendars = [
        {
            "flat": "606",
            "url": "https://www.airbnb.com.br/calendar/ical/1348473671779041594.ics?s=2f66c0dae2f36b7c846d5dd6e467c579",
        },
        {
            "flat": "908",
            "url": "https://www.airbnb.com.br/calendar/ical/1197793524730371217.ics?s=27eb51cf5b5eb72eae6baad6416b4142",
        },
        {
            "flat": "1108",
            "url": "https://www.airbnb.com.br/calendar/ical/562288913448118889.ics?s=a6b8340d6cf8a6642507685a2434255a",
        },
    ]

    df_cleaning = cleaning_schedule(ical_calendars, months=3)

    if df_cleaning is not None:
        import ace_tools_open as tools

        tools.display_dataframe_to_user("Limpeza dos Airbnbs", df_cleaning)
