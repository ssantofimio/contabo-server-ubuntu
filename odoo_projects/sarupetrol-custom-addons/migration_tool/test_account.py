from migration_engine import MigrationEngine

def test_account():
    engine = MigrationEngine('/opt/odoo/odoo18/custom-addons/migration_tool/config.json')
    engine.destination.authenticate()
    # Try to create an account in company 5
    vals = {
        'name': 'TEST COMPANY 5 ACCOUNT',
        'code': 'TEST999',
        'account_type': 'asset_current',
        'company_ids': [(6, 0, [5])]
    }
    ctx = {'allowed_company_ids': [5], 'company_id': 5}
    try:
        res_id = engine.destination.create('account.account', vals, context=ctx)
        print(f"Created Account ID: {res_id}")
        
        # Read it back
        res = engine.destination.read('account.account', [res_id], ['name', 'code', 'company_ids'])
        print(f"Account Info: {res}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_account()
