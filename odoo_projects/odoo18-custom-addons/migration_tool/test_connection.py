from migration_engine import MigrationEngine
import logging

logging.basicConfig(level=logging.INFO)

def test_connection():
    engine = MigrationEngine('/opt/odoo/odoo18/custom-addons/migration_tool/config.json')
    if engine.connect():
        print("SUCCESS: Connected to both source and destination!")
        
        # Test reading some data from source
        companies = engine.source.search_read('res.company', fields=['name'])
        print(f"Source Companies: {companies}")
        
        dest_companies = engine.destination.search_read('res.company', fields=['name'])
        print(f"Destination Companies: {dest_companies}")
    else:
        print("FAILURE: Could not connect. Check credentials and URLs.")

if __name__ == "__main__":
    test_connection()
