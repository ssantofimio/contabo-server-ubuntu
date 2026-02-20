from migration_engine import MigrationEngine
from mappings import MappingDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OdooMigrator:
    def __init__(self, config_path):
        self.engine = MigrationEngine(config_path)
        self.db = MappingDB(self.engine.config['settings']['mapping_db'])
        
    def run(self):
        if not self.engine.connect():
            return
            
        # Set contexts for multi-company support
        # Source company 1 -> Destination company 5
        # Force Spanish (CO) context for source to get translated names (Journals, Accounts, etc.)
        self.engine.source.context = {'allowed_company_ids': [1], 'company_id': 1, 'lang': 'es_CO'}
        self.engine.destination.context = {'allowed_company_ids': [5], 'company_id': 5}
        
        logger.info("Starting Migration...")
        
        # Phase 1: Foundation
        self.migrate_model('res.company', fields=['name', 'email', 'phone', 'street', 'city', 'vat'])
        self.migrate_model('res.currency', fields=['name', 'symbol', 'rounding'], domain=[('active', '=', True)])
        self.migrate_model('res.country', fields=['name', 'code'])
        self.migrate_model('uom.category', fields=['name'])
        self.migrate_model('uom.uom', fields=['name', 'category_id', 'uom_type', 'factor', 'rounding'])
        
        # Phase 2: Financial Foundation
        self.migrate_model('account.account.tag', fields=['name', 'country_id', 'applicability'])
        self.migrate_model('account.tax.group', fields=['name', 'country_id', 'company_id'])
        
        # Odoo 18 Enterprise uses company_ids (M2M) for account.account
        self.migrate_model('account.account', fields=['code', 'name', 'account_type', 'currency_id', 'reconcile', 'tax_ids', 'tag_ids', 'company_ids'], search_field='code')
        
        # Taxes
        self.migrate_model('account.tax', fields=['name', 'type_tax_use', 'tax_scope', 'amount_type', 'amount', 'tax_group_id', 'country_id', 'description', 'price_include', 'include_base_amount', 'is_base_affected', 'company_id'])
        self.migrate_model('account.tax.repartition.line', fields=['factor_percent', 'repartition_type', 'account_id', 'tag_ids', 'tax_id', 'use_in_tax_closing', 'document_type', 'company_id'])
        
        self.migrate_model('account.journal', fields=['name', 'code', 'type', 'currency_id', 'default_account_id', 'suspense_account_id', 'company_id'], search_field='code')
        
        # Phase 3: Master Data
        self.migrate_model('res.users', fields=['name', 'login', 'partner_id', 'company_ids'], search_field='login')
        self.migrate_model('res.partner.category', fields=['name'])
        
        # Partners
        self.migrate_model('res.partner', fields=['name', 'email', 'phone', 'vat', 'category_id', 'company_id'])
        
        self.migrate_model('product.category', fields=['name'])
        self.migrate_model('product.template', fields=['name', 'type', 'categ_id', 'list_price', 'uom_id', 'uom_po_id', 'company_id'])
        
        # Map product variants (auto-created by Odoo)
        self.migrate_product_variants()
        
        # Phase 4: Transactional Data
        # self.migrate_account_moves()
        # self.migrate_orders()
        # self.migrate_inventory()
        self.migrate_payments()
        
        logger.info("All planned phases complete.")

    def migrate_payments(self):
        logger.info("Migrating Account Payments...")
        # Fetch payment methods for mapping
        source_methods = self.engine.source.search_read('account.payment.method', fields=['name', 'code', 'payment_type'])
        source_method_map = {m['id']: m['code'] for m in source_methods}
        logger.info(f"Found {len(source_methods)} payment methods in source.")

        try:
            logger.info("Attempting to fetch payments with limit=5 and ref field...")
            payments = self.engine.source.search_read('account.payment', limit=5, fields=['name', 'ref'])
            logger.info(f"search_read returned type: {type(payments)}")
            if isinstance(payments, list):
                logger.info(f"Found {len(payments)} payments in source.")
            else:
                logger.error(f"Payments is not a list: {payments}")
        except BaseException as e:
            logger.critical(f"CRITICAL FAILURE TO FETCH PAYMENTS: {e}")
            import traceback
            logger.critical(traceback.format_exc())
            return
        
        logger.info("Starting payment loop...")
        count = 0
        for pay in payments:
            source_id = pay.pop('id')
            if self.db.get_dest_id('account.payment', source_id):
                continue
            
            # Map relational fields
            vals = self.map_relational_fields('account.payment', pay)
            
            # Link to existing move if possible
            source_move_id = pay['move_id'][0] if pay['move_id'] else None
            dest_move_id = None
            if source_move_id:
                dest_move_id = self.db.get_dest_id('account.move', source_move_id)
                if dest_move_id:
                     vals['move_id'] = dest_move_id
            
            # Map Payment Method Line
            source_method_id = pay['payment_method_id'][0] if pay['payment_method_id'] else None
            if source_method_id and vals.get('journal_id'):
                method_code = source_method_map.get(source_method_id)
                dest_journal_id = vals['journal_id']
                payment_type = pay['payment_type']
                
                # Find line in destination
                # We need to find account.payment.method.line where journal_id = dest_journal_id and payment_method_id.code = method_code
                domain = [
                    ('journal_id', '=', dest_journal_id),
                    ('payment_type', '=', payment_type),
                    ('code', '=', method_code) # helper domain in Odoo usually works, or strictly payment_method_id
                ]
                # Try simple search first (payment_method_id.code is not directly searchable easily without join, but 'code' field on line might proxy it or we search method first)
                # Actually, account.payment.method.line has 'code' related field or we search by payment_method_id
                
                # Let's search by payment_method_id.code? 
                # Better: get method id in dest first.
                dest_method_id = self.get_dest_payment_method_id(method_code, payment_type)
                if dest_method_id:
                    domain = [('journal_id', '=', dest_journal_id), ('payment_method_id', '=', dest_method_id)]
                    line = self.engine.destination.search_read('account.payment.method.line', domain=domain, limit=1, fields=['id'])
                    if line:
                        vals['payment_method_line_id'] = line[0]['id']
            
            # Remove payment_method_id (source) from vals as Odoo 18 uses line_id
            vals.pop('payment_method_id', None)

            try:
                # If we have a move_id, we try to write to it? 
                # Creating a payment with move_id might not work if move is posted.
                # If move exists, we might just need to ensure payment exists.
                # In Odoo 17+, payment is a wrapper. 
                # If we create payment vals with move_id, it might work.
                
                # However, if the move is ALREADY POSTED, modifying it via create payment might fail.
                # Let's try creating.
                dest_id = self.engine.destination.create('account.payment', vals)
                logger.info(f"Migrated Payment: {pay.get('name')} -> {dest_id}")
                self.db.add_mapping('account.payment', source_id, dest_id)
            except Exception as e:
                logger.error(f"Failed to migrate Payment {source_id}: {str(e)}")

    def get_dest_payment_method_id(self, code, payment_type):
        # Cache this?
        domain = [('code', '=', code), ('payment_type', '=', payment_type)]
        res = self.engine.destination.search_read('account.payment.method', domain=domain, limit=1, fields=['id'])
        return res[0]['id'] if res else None
        logger.info("Migrating Inventory...")
        try:
            # Warehouses
            self.migrate_model('stock.warehouse', fields=['name', 'code', 'company_id'])
            
            # Locations (Hierarchy is tricky, migrate all flattened or level by level? 
            # Odoo parent_left/right is gone in newer versions, usually parent_id is enough.
            # Order by parent_id helps to ensure parents exist.)
            # We use search_read with order 'parent_path' or just try to create and rely on mapping DB if we assume correct order in source?
            # Creating simply.
            self.migrate_model('stock.location', fields=['name', 'usage', 'location_id', 'company_id', 'posx', 'posy', 'posz'])

            # Stock Picking
            pickings = self.engine.source.search_read('stock.picking', fields=['name', 'origin', 'note', 'state', 'date', 'date_done', 'partner_id', 'location_id', 'location_dest_id', 'picking_type_id', 'company_id'])
            
            for pick in pickings:
                source_id = pick.pop('id')
                if self.db.get_dest_id('stock.picking', source_id):
                    continue
                
                # Fetch moves
                moves = self.engine.source.search_read('stock.move', domain=[('picking_id', '=', source_id)], 
                                                       fields=['name', 'product_id', 'product_uom_qty', 'product_uom', 'location_id', 'location_dest_id', 'company_id', 'state', 'date'])
                
                pick_vals = self.map_relational_fields('stock.picking', pick)
                pick_vals['state'] = 'draft'
                
                mapped_moves = []
                for move in moves:
                    move.pop('id')
                    move.pop('picking_id', None)
                    m_vals = self.map_relational_fields('stock.move', move)
                    mapped_moves.append((0, 0, m_vals))
                
                pick_vals['move_ids_without_package'] = mapped_moves
                
                try:
                    # check_move_validity=False might no apply here, but let's try standard create
                    dest_id = self.engine.destination.create('stock.picking', pick_vals)
                    logger.info(f"Migrated Stock Picking: {pick.get('name')} -> {dest_id}")
                    self.db.add_mapping('stock.picking', source_id, dest_id)
                except Exception as e:
                    logger.error(f"Failed to migrate Stock Picking {source_id}: {str(e)}")

        except Exception as e:
            logger.warning(f"Skipping Inventory: {str(e)}")

    def migrate_orders(self):
        logger.info("Migrating Sales and Purchase Orders...")
        
        # Sales Orders
        try:
            orders = self.engine.source.search_read('sale.order', fields=['name', 'date_order', 'partner_id', 'partner_invoice_id', 'partner_shipping_id', 'user_id', 'company_id', 'pricelist_id', 'note'])
            for order in orders:
                source_id = order.pop('id')
                if self.db.get_dest_id('sale.order', source_id):
                    continue
                
                # Fetch lines
                lines = self.engine.source.search_read('sale.order.line', domain=[('order_id', '=', source_id)], 
                                                       fields=['product_id', 'name', 'product_uom_qty', 'price_unit', 'tax_id', 'company_id'])
                
                order_vals = self.map_relational_fields('sale.order', order)
                 # Force draft state for safety
                order_vals['state'] = 'draft'

                mapped_lines = []
                for line in lines:
                    line.pop('id')
                    line.pop('order_id', None)
                    l_vals = self.map_relational_fields('sale.order.line', line)
                    mapped_lines.append((0, 0, l_vals))
                
                order_vals['order_line'] = mapped_lines
                
                try:
                    dest_id = self.engine.destination.create('sale.order', order_vals)
                    logger.info(f"Migrated Sale Order: {order.get('name')} -> {dest_id}")
                    self.db.add_mapping('sale.order', source_id, dest_id)
                except Exception as e:
                    logger.error(f"Failed to migrate Sale Order {source_id}: {str(e)}")
        except Exception as e:
            logger.warning(f"Skipping Sales Orders: {str(e)}")

        # Purchase Orders
        try:
            purchases = self.engine.source.search_read('purchase.order', fields=['name', 'date_order', 'partner_id', 'user_id', 'company_id', 'currency_id', 'notes'])
            for po in purchases:
                source_id = po.pop('id')
                if self.db.get_dest_id('purchase.order', source_id):
                    continue
                
                lines = self.engine.source.search_read('purchase.order.line', domain=[('order_id', '=', source_id)], 
                                                       fields=['product_id', 'name', 'product_qty', 'price_unit', 'taxes_id', 'company_id', 'date_planned'])
                
                po_vals = self.map_relational_fields('purchase.order', po)
                po_vals['state'] = 'draft'
                
                mapped_lines = []
                for line in lines:
                    line.pop('id')
                    line.pop('order_id', None)
                    l_vals = self.map_relational_fields('purchase.order.line', line)
                    mapped_lines.append((0, 0, l_vals))
                
                po_vals['order_line'] = mapped_lines
                
                try:
                    dest_id = self.engine.destination.create('purchase.order', po_vals)
                    logger.info(f"Migrated Purchase Order: {po.get('name')} -> {dest_id}")
                    self.db.add_mapping('purchase.order', source_id, dest_id)
                except Exception as e:
                    logger.error(f"Failed to migrate Purchase Order {source_id}: {str(e)}")
        except Exception as e:
            logger.warning(f"Skipping Purchase Orders: {str(e)}")

    def migrate_product_variants(self):
        logger.info("Mapping Product Variants...")
        variants = self.engine.source.search_read('product.product', fields=['product_tmpl_id', 'default_code'])
        for v in variants:
            source_id = v['id']
            source_tmpl_id = v['product_tmpl_id'][0]
            dest_tmpl_id = self.db.get_dest_id('product.template', source_tmpl_id)
            if not dest_tmpl_id:
                continue
            
            domain = [('product_tmpl_id', '=', dest_tmpl_id)]
            if v.get('default_code'):
                domain.append(('default_code', '=', v['default_code']))
            
            dest_variants = self.engine.destination.search_read('product.product', domain=domain, fields=['id'])
            if dest_variants:
                self.db.add_mapping('product.product', source_id, dest_variants[0]['id'])

    def migrate_account_moves(self):
        logger.info("Migrating Account Moves...")
        # Get moves from source
        # We filter by state='posted' to ensure we only migrate finalized data
        # Include invoice_date and invoice_date_due to preserve historical dates
        fields = ['name', 'ref', 'date', 'invoice_date', 'invoice_date_due', 'journal_id', 'move_type', 'partner_id', 'currency_id', 'company_id']
        moves = self.engine.source.search_read('account.move', domain=[('state', '=', 'posted')], fields=fields)
        
        for move in moves:
            source_id = move.pop('id')
            if self.db.get_dest_id('account.move', source_id):
                continue
                
            # Fetch lines
            lines = self.engine.source.search_read('account.move.line', domain=[('move_id', '=', source_id)], 
                                                   fields=['account_id', 'name', 'debit', 'credit', 'partner_id', 'tax_ids', 'quantity', 'price_unit', 'product_id', 'company_id'])
            
            # Map move header
            move_vals = self.map_relational_fields('account.move', move)
            
            # Map lines
            mapped_lines = []
            for line in lines:
                line.pop('id')
                line.pop('move_id', None)
                l_vals = self.map_relational_fields('account.move.line', line)
                
                if not l_vals.get('account_id'):
                    l_vals['account_id'] = 1364 # Migration Adjustment 2
                    logger.warning(f"Used dummy account for line in move {source_id}: {line.get('name')}")

                mapped_lines.append((0, 0, l_vals))
            
            move_vals['line_ids'] = mapped_lines
            
            # Create move in destination
            try:
                # Note: creating moves as 'draft' first is safer, then posting.
                # However, for speed we try to create as is.
                # Use check_move_validity=False to avoid "Unbalanced" errors due to strict Odoo validation on invoices
                # We use the source 'date' and 'invoice_date' to prevent "today" dates.
                dest_id = self.engine.destination.create('account.move', move_vals, context={'check_move_validity': False})
                logger.info(f"Migrated Account Move: {move.get('name')} -> {dest_id}")
                self.db.add_mapping('account.move', source_id, dest_id)
            except Exception as e:
                logger.error(f"Failed to migrate Account Move {source_id}: {str(e)}")

    def map_relational_fields(self, model_name, values):
        """Automatically map Many2one and Many2many fields using the mapping DB."""
        fields_info = self.engine.source.get_fields(model_name)
        dest_fields_info = self.engine.destination.get_fields(model_name)
        new_values = values.copy()
        
        for field_name, value in values.items():
            if not value:
                continue
            
            info = fields_info.get(field_name)
            if not info:
                continue
            
            # Special case for company_id -> company_ids (Odoo 18)
            dest_field_name = field_name
            if field_name == 'company_id' and 'company_ids' in dest_fields_info:
                dest_field_name = 'company_ids'
            
            dest_info = dest_fields_info.get(dest_field_name)
            if not dest_info:
                continue

            if info['type'] == 'many2one':
                # value is [id, name] for many2one in search_read
                source_id = value[0] if isinstance(value, list) else value
                relation = info['relation']
                
                dest_id = self.db.get_dest_id(relation, source_id)
                if dest_id:
                    if dest_info['type'] == 'many2many':
                        new_values[dest_field_name] = [(6, 0, [dest_id])]
                        print(f"DEBUG: Mapped {field_name} {source_id} to {dest_field_name} {dest_id}")
                        if dest_field_name != field_name:
                            new_values.pop(field_name, None)
                    else:
                        new_values[dest_field_name] = dest_id
                else:
                    new_values[dest_field_name] = False
                    logger.warning(f"Relation {relation} ID {source_id} for field {field_name} not found.")

            elif info['type'] == 'many2many':
                # value is a list of IDs
                source_ids = value
                relation = info['relation']
                mapped_ids = []
                for s_id in source_ids:
                    d_id = self.db.get_dest_id(relation, s_id)
                    if d_id:
                        mapped_ids.append(d_id)
                
                if mapped_ids:
                    # Odoo M2M format for write/create: [(6, 0, [ids])]
                    new_values[field_name] = [(6, 0, mapped_ids)]
                elif field_name == 'tax_ids':
                     # Explicitly clear taxes to avoid auto-computation from product
                     new_values[field_name] = [(6, 0, [])]
                else:
                    new_values.pop(field_name, None)
        
        return new_values

    def migrate_model(self, model_name, fields, domain=None, search_field='name'):
        logger.info(f"Migrating {model_name}...")
        records = self.engine.source.search_read(model_name, domain=domain, fields=fields)
        
        for rec in records:
            source_id = rec.pop('id')
            dest_id = None
            
            # Check if already migrated
            dest_id = self.db.get_dest_id(model_name, source_id)
            if dest_id:
                continue
            
            # Map relations
            rec = self.map_relational_fields(model_name, rec)
            
            # Search logic handles company_id or company_ids
            if search_field in rec:
                search_domain = [(search_field, '=', rec[search_field])]
                comp_id = None
                if 'company_id' in rec and rec['company_id']:
                    comp_id = rec['company_id']
                    search_domain.append(('company_id', '=', comp_id))
                elif 'company_ids' in rec and rec['company_ids']:
                    # rec['company_ids'] is [(6, 0, [id])]
                    comp_id = rec['company_ids'][0][2][0]
                    search_domain.append(('company_ids', 'in', [comp_id]))
                
                logger.info(f"Searching {model_name} with domain {search_domain} (Company Context: {comp_id})")
                existing = self.engine.destination.search_read(model_name, domain=search_domain, fields=['id'])
                if existing:
                    dest_id = existing[0]['id']
                    logger.info(f"Found existing {model_name}: {rec.get(search_field)} -> {dest_id}")
            
            if not dest_id:
                try:
                    dest_id = self.engine.destination.create(model_name, rec)
                    logger.info(f"Created {model_name}: {rec.get(search_field, 'ID '+str(source_id))} -> {dest_id}")
                except Exception as e:
                    logger.error(f"Failed to create {model_name} {source_id}: {str(e)}")
                    continue
            
            if dest_id:
                self.db.add_mapping(model_name, source_id, dest_id)

if __name__ == "__main__":
    migrator = OdooMigrator('/opt/odoo/odoo18/custom-addons/migration_tool/config.json')
    migrator.run()
