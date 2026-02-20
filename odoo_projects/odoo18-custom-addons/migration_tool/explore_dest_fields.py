from migration_engine import MigrationEngine
import json

def explore_fields(model):
    engine = MigrationEngine('/opt/odoo/odoo18/custom-addons/migration_tool/config.json')
    if engine.destination.authenticate():
        fields = engine.destination.get_fields(model)
        with open(f'/opt/odoo/odoo18/custom-addons/migration_tool/dest_fields_{model}.json', 'w') as f:
            json.dump(fields, f, indent=4)
        print(f"Fields for {model} on DESTINATION written to dest_fields_{model}.json")

if __name__ == "__main__":
    explore_fields('account.tax.repartition.line')
