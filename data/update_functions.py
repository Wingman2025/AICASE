import sqlite3

def update_production_plan(db_path, date, production_plan):
    """
    Update the production plan value for a specific date in the database.

    Args:
        db_path (str): Path to the SQLite database file.
        date (str): Date of the record to update (format: DD-MM-YYYY).
        production_plan (int): New production plan value to set.

    Returns:
        str: Success message or error message.
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE daily_data SET production_plan = ? WHERE date = ?", (production_plan, date))
        conn.commit()
        if cursor.rowcount == 0:
            return f"No record found for date {date}."
        return f"Production plan for {date} updated successfully."
    except Exception as e:
        return f"Error updating record: {str(e)}"
    finally:
        conn.close()
