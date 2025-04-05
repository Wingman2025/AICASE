import sqlite3

db_path = 'c:/Users/GarcJ88/OneDrive - BASF/Documents/Getting Started/AICASE/data/supply_chain.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check the production_plan value for the specified date
date_to_check = '03-04-2025'
cursor.execute("SELECT production_plan FROM daily_data WHERE date = ?", (date_to_check,))
result = cursor.fetchone()

if result:
    print(f"Production plan for {date_to_check}: {result[0]}")
else:
    print(f"No record found for date {date_to_check}.")

conn.close()
