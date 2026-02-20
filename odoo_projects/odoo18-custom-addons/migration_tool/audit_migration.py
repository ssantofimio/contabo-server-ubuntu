from migration_engine import MigrationEngine
from mappings import MappingDB
import logging
import sys

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationAuditor:
    def __init__(self, config_path):
        self.engine = MigrationEngine(config_path)
        self.db = MappingDB(self.engine.config['settings']['mapping_db'])

    def _count(self, instance, model, domain=None):
        domain = domain or []
        return instance.models.execute_kw(
            instance.db, instance.uid, instance.password,
            model, 'search_count', [domain]
        )

    def audit(self):
        if not self.engine.connect():
            return

        # Force Spanish context for source to match translated destination data
        self.engine.source.context = {'lang': 'es_CO'}

        models = [
            ('res.company',       [],                                 []),
            ('res.currency',      [('active','=',True)],              []),
            ('account.account',   [],                                 [('company_ids','in',[5])]),
            ('account.tax',       [],                                 [('company_id','=',5)]),
            ('account.journal',   [],                                 [('company_id','=',5)]),
            ('res.users',         [],                                 []),
            ('res.partner',       [],                                 []),
            ('product.template',  [],                                 []),
            ('account.move',      [('state','=','posted')],           []),
            ('account.payment',   [],                                 []),
        ]

        print("\n" + "="*80)
        print(f"{'Model':<30} | {'Source':<10} | {'Dest':<10} | {'Mapped':<10} | {'Status'}")
        print("-" * 80)

        for model, src_domain, dst_domain in models:
            try:
                src = self._count(self.engine.source, model, src_domain)
            except Exception:
                src = 'N/A'
            try:
                dst = self._count(self.engine.destination, model, dst_domain)
            except Exception:
                dst = 'N/A'

            # Count from our mapping DB
            mapped = self.db.conn.cursor().execute(
                "SELECT count(*) FROM id_mappings WHERE model_name=?", (model,)
            ).fetchone()[0]

            if isinstance(src, int) and isinstance(dst, int):
                status = "OK" if mapped >= src else f"MISSING {src - mapped}"
            else:
                status = "CHECK"

            print(f"{model:<30} | {str(src):<10} | {str(dst):<10} | {str(mapped):<10} | {status}")

        print("=" * 80)

        # Spot-check: sample 3 account.moves and compare dates
        print("\n--- Spot Check: account.move dates (sample 3) ---")
        rows = self.db.conn.cursor().execute(
            "SELECT source_id, dest_id FROM id_mappings WHERE model_name='account.move' LIMIT 3"
        ).fetchall()
        for src_id, dst_id in rows:
            try:
                src_rec = self.engine.source.search_read('account.move', domain=[('id','=',src_id)], fields=['name','date','invoice_date'])
                dst_rec = self.engine.destination.search_read('account.move', domain=[('id','=',dst_id)], fields=['name','date','invoice_date'])
                if src_rec and dst_rec:
                    s, d = src_rec[0], dst_rec[0]
                    date_ok = s['date'] == d['date']
                    inv_ok = s.get('invoice_date') == d.get('invoice_date')
                    print(f"  Move {s['name']}: date={'OK' if date_ok else 'MISMATCH('+s['date']+' vs '+d['date']+')'}, "
                          f"invoice_date={'OK' if inv_ok else 'MISMATCH('+str(s.get('invoice_date'))+' vs '+str(d.get('invoice_date'))+')'}")
            except Exception as e:
                print(f"  Error checking move {src_id}: {e}")

        # Spot-check: sample 3 journals and compare names
        print("\n--- Spot Check: account.journal names ---")
        rows = self.db.conn.cursor().execute(
            "SELECT source_id, dest_id FROM id_mappings WHERE model_name='account.journal' LIMIT 5"
        ).fetchall()
        for src_id, dst_id in rows:
            try:
                src_rec = self.engine.source.search_read('account.journal', domain=[('id','=',src_id)], fields=['name','code'])
                dst_rec = self.engine.destination.search_read('account.journal', domain=[('id','=',dst_id)], fields=['name','code'])
                if src_rec and dst_rec:
                    s, d = src_rec[0], dst_rec[0]
                    name_ok = s['name'] == d['name']
                    print(f"  Journal {s['code']}: src='{s['name']}' dst='{d['name']}' {'OK' if name_ok else 'NAME MISMATCH'}")
            except Exception as e:
                print(f"  Error checking journal {src_id}: {e}")

if __name__ == "__main__":
    auditor = MigrationAuditor('/opt/odoo/odoo18/custom-addons/migration_tool/config.json')
    auditor.audit()
