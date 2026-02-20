from migration_engine import MigrationEngine
import json

def check_accounts():
    engine = MigrationEngine('/opt/odoo/odoo18/custom-addons/migration_tool/config.json')
    print("Authenticating with destination...")
    uid = engine.destination.authenticate()
    print(f"Destination UID: {uid}")
    if uid:
        try:
            print("Searching accounts...")
            accounts = engine.destination.models.execute_kw(
                engine.destination.db, engine.destination.uid, engine.destination.password,
                'account.account', 'search_read',
                [[]],
                {'fields': ['code', 'name', 'company_id'], 'limit': 10}
            )
            print(f"Found {len(accounts)} accounts.")
            for acc in accounts:
                print(f"Code: {acc['code']}, Name: {acc['name']}, Company: {acc['company_id']}")
        except Exception as e:
            print(f"Error searching accounts: {str(e)}")
    else:
        print("Failed to authenticate.")

if __name__ == "__main__":
    check_accounts()
