import streamlit as st
import pandas as pd
import airbnb_calendar


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


def format_date_with_indicator(date_str):
    """Format date string and add indicator for past/today dates"""
    if not date_str or date_str == "":
        return ""
    try:
        date = pd.to_datetime(date_str)
        formatted_date = date.strftime("%d/%m/%Y")
        # Add green circle if date is today or past
        if date.date() <= pd.Timestamp.now().date():
            return f"{formatted_date} 🟢"
        return formatted_date
    except:
        return ""


def format_checkout_indicator(date_str):
    """Format checkout date and add green indicator for past/today dates"""
    if not date_str or date_str == "":
        return ""
    try:
        date = pd.to_datetime(date_str)
        formatted_date = date.strftime("%d/%m/%Y")
        # Add green circle if date is today or past
        if date.date() <= pd.Timestamp.now().date():
            return f"{formatted_date} 🟢"
        return formatted_date
    except:
        return ""


def format_checkin_indicator(date_str):
    """Format check-in date and add red/yellow indicators based on urgency"""
    if not date_str or date_str == "":
        return ""
    try:
        date = pd.to_datetime(date_str)
        formatted_date = date.strftime("%d/%m/%Y")
        today = pd.Timestamp.now().date()
        tomorrow = today + pd.Timedelta(days=1)

        # Add colored circle based on date
        if date.date() == today:
            return f"{formatted_date} 🔴"  # Red for today's check-in
        elif date.date() == tomorrow:
            return f"{formatted_date} 🟡"  # Yellow for tomorrow's check-in
        return formatted_date
    except:
        return ""


def save_cleaner_info(row):
    """UI wrapper for saving cleaner information"""
    try:
        # Convert date from dd/mm/yyyy to yyyy-mm-dd
        entrada_date = pd.to_datetime(
            row["Entrada"].split()[0], format="%d/%m/%Y"
        ).strftime("%Y-%m-%d")

        if airbnb_calendar.save_cleaner_info(row["AP"], entrada_date, row["FX"]):
            st.success("Informações de faxina salvas com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar informações: {str(e)}")


def main():
    st.title("VanGogh AirBnB")

    ical_calendars = airbnb_calendar.load_calendars()

    df = airbnb_calendar.cleaning_schedule(ical_calendars)

    if df is not None:
        # Format the dates and prepare display DataFrame
        df_display = df.copy()
        df_display["CheckOut"] = df_display["CheckOut"].apply(format_checkout_indicator)
        df_display["NextCheckIn"] = df_display["NextCheckIn"].apply(
            format_checkin_indicator
        )

        # Modify Cleaner column to include 🔥 for HotBed
        df_display["Cleaner"] = df_display.apply(
            lambda row: f"🔥 {row['Cleaner']}"
            if row["HotBed"] and row["Cleaner"]
            else "🔥"
            if row["HotBed"]
            else row["Cleaner"]
            if row["Cleaner"]
            else "",
            axis=1,
        )

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
                }
            )
            columns_order = ["AP", "Saída", "Entrada", "FX"]
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
                font-size: 12px !important;  /* Reduced from 14px */
                width: 100% !important;
                text-align: center !important;
                table-layout: fixed !important;
            }
            .dataframe td, .dataframe th {
                white-space: nowrap;
                padding: 6px !important;     /* Reduced from 8px */
                text-align: center !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                font-size: 12px !important;  /* Added explicit font size for cells */
            }
            .dataframe th {
                font-size: 13px !important;  /* Slightly larger font for headers */
                font-weight: bold !important;
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
