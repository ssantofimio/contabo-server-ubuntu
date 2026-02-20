"""
Fix script to:
1. Update invoice_date on already-migrated account.move records
2. Update journal names to Spanish
3. Migrate account.payment records
"""
from migration_engine import MigrationEngine
from mappings import MappingDB
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = '/opt/odoo/odoo18/custom-addons/migration_tool/config.json'

def main():
    engine = MigrationEngine(CONFIG)
    db = MappingDB(engine.config['settings']['mapping_db'])
    if not engine.connect():
        return

    # Force Spanish context
    engine.source.context = {'allowed_company_ids': [1], 'company_id': 1, 'lang': 'es_CO'}
    engine.destination.context = {'allowed_company_ids': [5], 'company_id': 5}

    # ─── 1. Fix invoice_date on existing moves ───────────────────────────
    logger.info("=== Phase 1: Fixing invoice_date on migrated moves ===")
    rows = db.conn.cursor().execute(
        "SELECT source_id, dest_id FROM id_mappings WHERE model_name='account.move'"
    ).fetchall()
    logger.info(f"Found {len(rows)} mapped moves to check.")

    fixed = 0
    for src_id, dst_id in rows:
        try:
            src = engine.source.search_read('account.move', domain=[('id','=',src_id)],
                                            fields=['invoice_date', 'invoice_date_due'])
            if not src:
                continue
            s = src[0]
            update_vals = {}
            if s.get('invoice_date'):
                update_vals['invoice_date'] = s['invoice_date']
            if s.get('invoice_date_due'):
                update_vals['invoice_date_due'] = s['invoice_date_due']
            if update_vals:
                engine.destination.write('account.move', dst_id, update_vals)
                fixed += 1
                if fixed % 50 == 0:
                    logger.info(f"  Fixed {fixed} invoice dates so far...")
        except Exception as e:
            logger.warning(f"  Could not fix move {src_id}->{dst_id}: {e}")

    logger.info(f"Fixed invoice_date on {fixed} moves.")

    # ─── 2. Fix journal names (Spanish) ───────────────────────────────
    logger.info("=== Phase 2: Updating journal names to Spanish ===")
    rows = db.conn.cursor().execute(
        "SELECT source_id, dest_id FROM id_mappings WHERE model_name='account.journal'"
    ).fetchall()

    for src_id, dst_id in rows:
        try:
            src = engine.source.search_read('account.journal', domain=[('id','=',src_id)],
                                            fields=['name'])
            if src:
                spanish_name = src[0]['name']
                engine.destination.write('account.journal', dst_id, {'name': spanish_name})
                logger.info(f"  Journal {dst_id} -> '{spanish_name}'")
        except Exception as e:
            logger.warning(f"  Could not update journal {src_id}->{dst_id}: {e}")

    # ─── 3. Migrate payments ─────────────────────────────────────────
    logger.info("=== Phase 3: Migrating Account Payments ===")

    # Fetch all source payments
    payments = engine.source.search_read('account.payment', fields=[
        'name', 'date', 'amount', 'partner_id', 'journal_id',
        'currency_id', 'payment_type', 'partner_type',
        'payment_method_id', 'move_id', 'company_id'
    ])
    logger.info(f"Found {len(payments)} payments in source.")

    # Build helper maps
    source_methods = engine.source.search_read('account.payment.method', fields=['code', 'payment_type'])
    src_method_map = {m['id']: m for m in source_methods}

    # Cache destination payment method lines per (journal_id, method_code, payment_type)
    dest_method_line_cache = {}

    def get_method_line(journal_id, method_code, payment_type):
        key = (journal_id, method_code, payment_type)
        if key in dest_method_line_cache:
            return dest_method_line_cache[key]
        # Find dest method id
        methods = engine.destination.search_read('account.payment.method',
            domain=[('code','=',method_code), ('payment_type','=',payment_type)], limit=1, fields=['id'])
        if methods:
            lines = engine.destination.search_read('account.payment.method.line',
                domain=[('journal_id','=',journal_id), ('payment_method_id','=',methods[0]['id'])],
                limit=1, fields=['id'])
            result = lines[0]['id'] if lines else None
        else:
            result = None
        dest_method_line_cache[key] = result
        return result

    migrated = 0
    skipped = 0
    failed = 0
    for pay in payments:
        source_id = pay['id']
        if db.get_dest_id('account.payment', source_id):
            skipped += 1
            continue

        # Build vals
        vals = {
            'date': pay['date'],
            'amount': pay['amount'],
            'payment_type': pay['payment_type'],
            'partner_type': pay['partner_type'],
        }

        # Map partner
        if pay.get('partner_id'):
            dest_partner = db.get_dest_id('res.partner', pay['partner_id'][0])
            if dest_partner:
                vals['partner_id'] = dest_partner

        # Map journal
        if pay.get('journal_id'):
            dest_journal = db.get_dest_id('account.journal', pay['journal_id'][0])
            if dest_journal:
                vals['journal_id'] = dest_journal

        # Map currency
        if pay.get('currency_id'):
            dest_currency = db.get_dest_id('res.currency', pay['currency_id'][0])
            if dest_currency:
                vals['currency_id'] = dest_currency

        # Map payment method line
        if pay.get('payment_method_id') and vals.get('journal_id'):
            src_method = src_method_map.get(pay['payment_method_id'][0])
            if src_method:
                line_id = get_method_line(vals['journal_id'], src_method['code'], pay['payment_type'])
                if line_id:
                    vals['payment_method_line_id'] = line_id

        try:
            dest_id = engine.destination.create('account.payment', vals)
            db.add_mapping('account.payment', source_id, dest_id)
            migrated += 1
            if migrated % 50 == 0:
                logger.info(f"  Migrated {migrated} payments so far...")
        except Exception as e:
            logger.error(f"  Failed payment {source_id} ({pay.get('name')}): {e}")
            failed += 1

    logger.info(f"Payments complete: {migrated} migrated, {skipped} skipped, {failed} failed.")
    logger.info("=== All fixes applied ===")

if __name__ == "__main__":
    main()
