import sqlite3

db_path = 'c:/Users/GarcJ88/OneDrive - BASF/Documents/Getting Started/AICASE/data/supply_chain.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create procurement_data table
cursor.execute('''
CREATE TABLE IF NOT EXISTS procurement_data (
    id INTEGER PRIMARY KEY,
    column1 TEXT,
    column2 TEXT,
    column3 TEXT
)
''')

# Insert sample data
cursor.execute('''
INSERT INTO procurement_data (column1, column2, column3)
VALUES ('Sample1', 'Sample2', 'Sample3')
''')

conn.commit()
conn.close()
print("Table created and sample data inserted.")
