import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Initialize the database
def init_db():
    conn = sqlite3.connect("kitc_requisition.db")
    cursor = conn.cursor()

    # Create requisitions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requisitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT,
            quantity REAL,
            unit TEXT,
            total_quantity REAL,
            remaining_quantity REAL,
            requisition_date TEXT
        )
    """)

    # Create meals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_name TEXT,
            item TEXT,
            unit TEXT,
            quantity_per_portion REAL,
            number_of_portions INTEGER,
            total_quantity_used REAL,
            prepared_date TEXT
        )
    """)
    conn.commit()
    conn.close()

# Add a requisition to the database
def add_requisition(item, quantity, unit):
    conn = sqlite3.connect("kitc_requisition.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO requisitions (item, quantity, unit, total_quantity, remaining_quantity, requisition_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (item, quantity, unit, quantity, quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# Update a requisition in the database
def update_requisition(id, item, quantity, unit):
    conn = sqlite3.connect("kitc_requisition.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE requisitions 
        SET item = ?, quantity = ?, unit = ?, total_quantity = ?, remaining_quantity = ?
        WHERE id = ?
    """, (item, quantity, unit, quantity, quantity, id))
    conn.commit()
    conn.close()

# Deduct quantity for a specific meal
def deduct_quantity_for_meal(meal_name, meal_items):
    conn = sqlite3.connect("kitc_requisition.db")
    cursor = conn.cursor()

    for item, (quantity_per_portion, number_of_portions, unit) in meal_items.items():
        total_quantity_used = quantity_per_portion * number_of_portions

        cursor.execute("""
            SELECT remaining_quantity FROM requisitions WHERE item = ? AND unit = ? AND remaining_quantity >= ?
        """, (item, unit, total_quantity_used))
        row = cursor.fetchone()

        if row:
            cursor.execute("""
                UPDATE requisitions
                SET remaining_quantity = remaining_quantity - ?
                WHERE item = ? AND unit = ?
            """, (total_quantity_used, item, unit))
            cursor.execute("""
                INSERT INTO meals (meal_name, item, unit, quantity_per_portion, number_of_portions, total_quantity_used, prepared_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (meal_name, item, unit, quantity_per_portion, number_of_portions, total_quantity_used, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        else:
            st.error(f"Not enough {unit} remaining for {item}. Required: {total_quantity_used} {unit}.")

    conn.commit()
    conn.close()

# Get all requisitions within a date range
def get_requisitions(start_date, end_date):
    conn = sqlite3.connect("kitc_requisition.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM requisitions 
        WHERE requisition_date BETWEEN ? AND ?
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["ID", "Item", "Quantity", "Unit", "Total Quantity", "Remaining Quantity", "Requisition Date"])

# Get meal preparation logs within a date range
def get_meal_logs(start_date, end_date):
    conn = sqlite3.connect("kitc_requisition.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM meals 
        WHERE prepared_date BETWEEN ? AND ?
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["ID", "Meal Name", "Item", "Unit", "Quantity Per Portion", "Number of Portions", "Total Quantity Used", "Prepared Date"])

# Download function
def download_csv(dataframe, filename):
    csv = dataframe.to_csv(index=False).encode('utf-8')
    st.download_button(label=f"Download {filename}", data=csv, file_name=filename, mime="text/csv")

# Login functionality
def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            # Replace these with actual authentication logic (e.g., check against a database)
            if username == "admin" and password == "12345":
                st.session_state.logged_in = True
                st.success("Login successful!")
                st.session_state.rerun()  # This will refresh the page and hide the login form
            else:
                st.error("Incorrect username or password.")
    return st.session_state.logged_in

# Main application
def main():
    st.title("Kitchen Requisition and Meal Preparation Tracker")

    # Initialize the database
    init_db()

    # Handle login
    if not login():
        return  # Prevent access to the rest of the app until logged in

    # Hide login section if the user is logged in
    if st.session_state.logged_in:
        # Tabs for Requisition and Meal Preparation
        tabs = st.tabs(["🛒 Requisition Items", "🍴 Prepare a Meal", "🔧 Update Requisition"])

        with tabs[0]:
            st.header("Requisition Items")
            with st.form("requisition_form"):
                item = st.text_input("Item Name")
                quantity = st.number_input("Quantity", min_value=0.1, step=0.1)
                unit = st.selectbox("Unit", ["kg", "tubers", "pieces", "cubes", "pack"])
                submit_requisition = st.form_submit_button("Add Requisition")

                if submit_requisition:
                    if item and quantity > 0:
                        add_requisition(item, quantity, unit)
                        st.success(f"Requisition added for {item} ({quantity} {unit})!")
                    else:
                        st.error("Please fill in all fields correctly.")

            st.subheader("Requisitioned Items")
            start_date = st.date_input("Start Date", value=datetime.today())
            end_date = st.date_input("End Date", value=datetime.today())

            if start_date and end_date:
                requisitions_df = get_requisitions(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                if not requisitions_df.empty:
                    st.dataframe(requisitions_df)
                    download_csv(requisitions_df, "requisitions.csv")
                else:
                    st.write("No items found within the selected date range.")

        with tabs[1]:
            st.header("Prepare a Meal")
            with st.form("meal_preparation_form"):
                meal_name = st.text_input("Meal Name")
                meal_items = {}
                requisitions_df = get_requisitions("2000-01-01", datetime.today().strftime("%Y-%m-%d"))
                if not requisitions_df.empty:
                    selected_items = st.multiselect("Select items for the meal", requisitions_df["Item"].unique())
                    for item in selected_items:
                        unit = requisitions_df[requisitions_df["Item"] == item]["Unit"].iloc[0]
                        st.write(f"Details for {item} (Unit: {unit}):")
                        quantity_per_portion = st.number_input(f"Quantity per portion for {item} ({unit})", min_value=0.0, step=0.1, key=f"{item}_quantity")
                        number_of_portions = st.number_input(f"Number of portions for {item}", min_value=0, step=1, key=f"{item}_portions")
                        if quantity_per_portion > 0 and number_of_portions > 0:
                            meal_items[item] = (quantity_per_portion, number_of_portions, unit)

                submit_meal = st.form_submit_button("Prepare Meal")
                if submit_meal:
                    if meal_name and meal_items:
                        deduct_quantity_for_meal(meal_name, meal_items)
                        st.success(f"Meal '{meal_name}' prepared successfully!")
                    else:
                        st.error("Please provide a meal name and at least one item.")

            st.subheader("Meal Preparation Logs")
            start_date_meal = st.date_input("Meal Start Date", value=datetime.today())
            end_date_meal = st.date_input("Meal End Date", value=datetime.today())

            if start_date_meal and end_date_meal:
                meal_logs_df = get_meal_logs(start_date_meal.strftime("%Y-%m-%d"), end_date_meal.strftime("%Y-%m-%d"))
                if not meal_logs_df.empty:
                    st.dataframe(meal_logs_df)
                    download_csv(meal_logs_df, "meal_logs.csv")
                else:
                    st.write("No meals found within the selected date range.")

        with tabs[2]:
            st.header("Update Requisition")
        
        # Fetch available requisition items for the dropdown
        requisitions_df = get_requisitions("2000-01-01", datetime.today().strftime("%Y-%m-%d"))
        if not requisitions_df.empty:
            st.dataframe(requisitions_df)
            
            # Get the list of items for the dropdown
            available_items = requisitions_df["Item"].unique().tolist()
            
            # Select item to update
            selected_item = st.selectbox("Select Item to Update", available_items)
            
            # Fetch the details of the selected item
            selected_item_data = requisitions_df[requisitions_df["Item"] == selected_item].iloc[0]
            current_quantity = selected_item_data["Quantity"]
            current_unit = selected_item_data["Unit"]
            
            # Inputs for updating item details
            quantity = st.number_input("Updated Quantity", min_value=0.1, value=current_quantity, step=0.1)
            unit = st.selectbox("Updated Unit", ["kg", "tubers", "pieces", "cubes", "pack"], index=["kg", "tubers", "pieces", "cubes", "pack"].index(current_unit))

            if st.button("Update Requisition"):
                if quantity > 0:
                    # Update requisition in the database
                    update_requisition(selected_item_data["ID"], selected_item, quantity, unit)
                    st.success(f"Requisition for '{selected_item}' updated successfully!")
                else:
                    st.error("Please provide a valid quantity.")
        else:
            st.write("No requisitions found.")

if __name__ == "__main__":
    main()