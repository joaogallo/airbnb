import streamlit as st
import pandas as pd
from airbnb_calendar import cleaning_schedule

# Configure the page for mobile-first design
st.set_page_config(
    page_title="Airbnb Limpeza", layout="centered", initial_sidebar_state="collapsed"
)

# Custom CSS for mobile optimization
st.markdown(
    """
<style>
    /* Make text more readable on mobile */
    .stDataFrame {
        font-size: 14px !important;
    }
    
    /* Custom styles for the cards */
    .cleaning-card {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .hotbed {
        background-color: #ffebee !important;
    }
    
    .date-text {
        font-size: 1.1rem;
        font-weight: bold;
        color: #1a73e8;
    }
    
    .flat-text {
        font-size: 1.2rem;
        font-weight: bold;
        color: #202124;
    }
</style>
""",
    unsafe_allow_html=True,
)


def format_date(date_str):
    """Format date string to Brazilian format"""
    if not date_str or date_str == "":
        return ""
    try:
        return pd.to_datetime(date_str).strftime("%d/%m")
    except:
        return ""


def main():
    st.title("Limpeza VanGogh")

    ical_calendars = [
        {
            "flat": "606",
            "url": "https://www.airbnb.com.br/calendar/ical/1348473671779041594.ics?s=2f66c0dae2f36b7c846d5dd6e467c579",
            "owner": "João",
        },
        {
            "flat": "908",
            "url": "https://www.airbnb.com.br/calendar/ical/1197793524730371217.ics?s=27eb51cf5b5eb72eae6baad6416b4142",
            "owner": "João",
        },
        {
            "flat": "1108",
            "url": "https://www.airbnb.com.br/calendar/ical/562288913448118889.ics?s=a6b8340d6cf8a6642507685a2434255a",
            "owner": "João",
        },
    ]

    df = cleaning_schedule(ical_calendars)

    if df is not None:
        # Format the dates
        df_display = df.copy()
        df_display["CheckOut"] = df_display["CheckOut"].apply(format_date)
        df_display["NextCheckIn"] = df_display["NextCheckIn"].apply(format_date)

        # Add fire emoji for HotBed
        df_display["HotBed"] = df_display["HotBed"].apply(lambda x: "🔥" if x else "")

        # Rename columns for display
        df_display = df_display.rename(
            columns={
                "Flat": "Apto",
                "CheckOut": "Saída",
                "NextCheckIn": "Próxima Entrada",
                "Cleaner": "Limpeza",
                "HotBed": "Hot",
            }
        )

        # Reorder columns
        columns_order = ["Hot", "Apto", "Saída", "Próxima Entrada", "Limpeza"]
        df_display = df_display[columns_order]

        # Display as table with custom styling
        st.markdown(
            """
        <style>
        .dataframe {
            font-size: 14px !important;
            width: 100% !important;
            text-align: center !important;
        }
        .dataframe td, .dataframe th {
            white-space: nowrap;
            padding: 8px !important;
            text-align: center !important;
        }
        /* Make Hot column as narrow as possible */
        .dataframe td:first-child, .dataframe th:first-child {
            width: 1% !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.error("Não foi possível carregar a agenda de limpeza")


if __name__ == "__main__":
    main()
