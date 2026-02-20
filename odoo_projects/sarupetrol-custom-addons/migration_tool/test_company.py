from migration_engine import MigrationEngine

def test_create():
    engine = MigrationEngine('/opt/odoo/odoo18/custom-addons/migration_tool/config.json')
    engine.destination.authenticate()
    # Try to create a partner in company 5
    vals = {
        'name': 'TEST COMPANY 5 PARTNER',
        'company_id': 5
    }
    ctx = {'allowed_company_ids': [5], 'company_id': 5}
    res_id = engine.destination.create('res.partner', vals, context=ctx)
    print(f"Created Partner ID: {res_id}")
    
    # Read it back
    res = engine.destination.search_read('res.partner', [[('id', '=', res_id)]], ['name', 'company_id'])
    print(f"Partner Info: {res}")

if __name__ == "__main__":
    test_create()
