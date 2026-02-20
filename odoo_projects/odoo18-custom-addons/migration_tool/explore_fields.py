from migration_engine import MigrationEngine
import json

def explore_fields(model):
    engine = MigrationEngine('/opt/odoo/odoo18/custom-addons/migration_tool/config.json')
    if engine.source.authenticate():
        fields = engine.source.get_fields(model)
        with open(f'/opt/odoo/odoo18/custom-addons/migration_tool/fields_{model}.json', 'w') as f:
            json.dump(fields, f, indent=4)
        print(f"Fields for {model} written to fields_{model}.json")

if __name__ == "__main__":
    explore_fields('account.tax.repartition.line')
