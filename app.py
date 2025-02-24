import streamlit as st
import pandas as pd
from airbnb_calendar import cleaning_schedule, load_calendars
import json
import os

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
        return pd.to_datetime(date_str).strftime("%d/%m/%Y")
    except:
        return ""


def save_cleaner_info(row):
    """Save cleaner information to JSON file"""
    cleaner_data = {
        "Flat": row["AP"],
        "NextCheckIn": row["Entrada"],
        "Cleaner": row["FX"],
    }

    # Load existing data
    filename = "/mount/cleaners.json"
    existing_data = []
    if os.path.exists(filename):
        with open(filename, "r") as f:
            existing_data = json.load(f)
    else:
        os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Update or add new entry
    updated = False
    for entry in existing_data:
        if (
            entry["Flat"] == cleaner_data["Flat"]
            and entry["NextCheckIn"] == cleaner_data["NextCheckIn"]
        ):
            entry["Cleaner"] = cleaner_data["Cleaner"]
            updated = True
            break

    if not updated:
        existing_data.append(cleaner_data)

    # Save back to file
    with open(filename, "w") as f:
        json.dump(existing_data, f, indent=2)


def main():
    st.title("Limpeza VanGogh")

    ical_calendars = load_calendars()

    df = cleaning_schedule(ical_calendars)

    if df is not None:
        # Format the dates and prepare display DataFrame
        df_display = df.copy()
        df_display["CheckOut"] = df_display["CheckOut"].apply(format_date)
        df_display["NextCheckIn"] = df_display["NextCheckIn"].apply(format_date)
        df_display["HotBed"] = df_display["HotBed"].apply(lambda x: "🔥" if x else "")

        # Create a unique key for each row based on Flat and CheckOut
        df_display["row_key"] = df_display.apply(
            lambda row: f"{row['Flat']}_{row['CheckOut']}", axis=1
        )

        # Create columns for layout
        col1, col2 = st.columns([7, 3])

        with col1:
            # Rename and reorder columns as before
            display_df = df_display.rename(
                columns={
                    "Flat": "AP",
                    "CheckOut": "Saída",
                    "NextCheckIn": "Entrada",
                    "Cleaner": "FX",
                    "HotBed": "H",
                }
            )
            columns_order = ["H", "AP", "Saída", "Entrada", "FX"]
            display_df = display_df[columns_order]

            # Display table with callback
            edited_df = st.data_editor(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    # ...existing column config...
                },
                key="cleaning_table",
            )

            # Check for changes and save
            if edited_df is not None and not edited_df.equals(display_df):
                # Find the changed row by comparing the dataframes
                changed_mask = (edited_df != display_df).any(axis=1)
                changed_row = edited_df[changed_mask].iloc[0]
                save_cleaner_info(changed_row)

        # Update custom CSS
        st.markdown(
            """
            <style>
            .dataframe {
                font-size: 14px !important;
                width: 100% !important;
                text-align: center !important;
                table-layout: fixed !important;
            }
            .dataframe td, .dataframe th {
                white-space: nowrap;
                padding: 8px !important;
                text-align: center !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }
            .dataframe td:first-child, .dataframe th:first-child {
                width: 40px !important;
                min-width: 40px !important;
                max-width: 40px !important;
                padding-left: 4px !important;
                padding-right: 4px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    else:
        st.error("Não foi possível carregar a agenda de limpeza")


if __name__ == "__main__":
    main()
