import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse

# 1. Setup connection using the exact working IPv4 configuration we found
username = "postgres.qykueriwcvgxsbxbbtso"
password = "YOUR_NEW_PURE_ALPHANUMERIC_PASSWORD"  # <-- Put your clean password here
host = "3.114.238.169"  # Forced IPv4 Bridge
port = 6543
database = "postgres"

DB_URL = f"postgresql://{username}:{password}@{host}:{port}/{database}"
engine = create_engine(DB_URL)

def migrate_students():
    print("Reading student data from CSV/Excel...")
    # Read your local Student_Data file
    try:
        df = pd.read_csv("final sheet for result cards.xlsx - Student_Data.csv")
    except FileNotFoundError:
        print("Could not find the local student data file. Make sure it's in this folder!")
        return

    print(f"Found {len(df)} students. Preparing database sync...")
    
    with engine.begin() as conn:
        for idx, row in df.iterrows():
            # Skip empty rows if any
            if pd.isna(row['Roll No']):
                continue
                
            # Insert or update student master records
            conn.execute(text("""
                INSERT INTO students (
                    student_id, student_name, father_name, session, 
                    academic_system, class_level, discipline, section, roll_no, contact_1
                ) VALUES (
                    :student_id, :name, :father, :session, :system, :level, :discipline, :section, :roll, :contact
                ) ON CONFLICT (student_id) DO UPDATE SET
                    student_name = EXCLUDED.student_name,
                    section = EXCLUDED.section;
            """), {
                "student_id": str(int(row['Roll No'])),
                "name": str(row['Name']),
                "father": str(row['Father Name']),
                "session": "2025-2026", # Default fallback session matching your system rules
                "system": "Annual",
                "level": str(row['Class']),
                "discipline": str(row['Discipline']),
                "section": str(row['Section']),
                "roll": int(row['Roll No']),
                "contact": "N/A"
            })
            
    print("🎉 Student Directory Successfully Migrated to Supabase Cloud!")

if __name__ == "__main__":
    migrate_students()
