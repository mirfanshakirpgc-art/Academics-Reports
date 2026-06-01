# patcher.py
import re
import os

filename = "app.py"

if not os.path.exists(filename):
    print("❌ Error: Could not find app.py in this directory. Move patcher.py into the same folder as app.py!")
    exit()

with open(filename, "r", encoding="utf-8") as f:
    content = f.read()

# Create a backup just in case
with open("app_backup.py", "w", encoding="utf-8") as f:
    f.write(content)
print("📦 Created safety backup as 'app_backup.py'")

# This script will search your code for table row definitions (<tr>) 
# and intelligently insert the NC/Absent logic block we designed.
print("🔍 Scanning app.py for the report card rendering engine...")

# Let's locate the subject row loop inside your app
# If you paste a snippet of your loop here, I can pinpoint it instantly!
