import csv
from pathlib import Path

csv_path = Path("data/Location.csv")

# Read the CSV
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

# Check if the new columns already exist in header
header = rows[0]
new_columns = ['sensory_experience', 'wayfinding', 'physical_access']

# Find where to insert the new columns (before thumbnails_image)
insert_index = header.index('thumbnails_image')

# Add new columns to header if not already present
for col in new_columns:
    if col not in header:
        header.insert(insert_index, col)

# Process each data row
for i, row in enumerate(rows[1:], start=1):
    # Ensure row has enough columns
    while len(row) < len(header) - len(new_columns):
        row.append('')
    
    # Insert empty values for new columns at the correct position
    for col in new_columns:
        if len(row) < insert_index + len(new_columns):
            row.insert(insert_index, '')

# Write back
with open(csv_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"Updated {csv_path} with new columns")
