import pandas as pd
import psycopg2
from psycopg2 import extras

# --- CONFIGURATION ---
# Use your actual filename
FILE_PATH = 'final_catalogue_ACCESSION_CORRECTED.xlsx' 

DB_CONFIG = {
    "dbname": "library_catalogue",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}

def sync_library_data():
    try:
        # 1. Load the Excel file
        # Note: 'openpyxl' must be installed (pip install openpyxl)
        df = pd.read_excel(FILE_PATH)
        print(f"Successfully read {len(df)} rows from {FILE_PATH}")

        # 2. Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 3. Prepare the Update Query
        # We update every field based on the 'SL No'
        update_query = """
            UPDATE items 
            SET 
                new_accession_no = %s,
                title = %s,
                language = %s,
                category = %s,
                original_language = %s,
                genre = %s,
                author = %s,
                publisher = %s,
                translation_compilation = %s,
                ddc = %s,
                year = %s,
                call_no = %s,
                shelf = %s,
                isbn = %s,
                notes = %s
            WHERE serial_no = %s;
        """

        # 4. Process data for batch update
        update_data = []
        for _, row in df.iterrows():
            # Mapping Excel headers to the query parameters
            update_data.append((
                str(row['Accession No']),
                row['Title'],
                row['Language'],
                row['Category'],
                row['Original Language'],
                row['Genre'],
                row['Author'],
                row['Publisher'],
                row['Translation/compilation'],
                row['DDC'],
                int(row['Year']) if pd.notnull(row['Year']) else 0,
                row['Call No'],
                row['Shelf'],
                row['ISBN'],
                row['Notes'],
                int(row['SL No']) # The 'WHERE' clause anchor
            ))

        # 5. Execute Update
        cursor.executemany(update_query, update_data)
        
        conn.commit()
        print(f"Successfully updated {cursor.rowcount} records in the 'items' table.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    sync_library_data()