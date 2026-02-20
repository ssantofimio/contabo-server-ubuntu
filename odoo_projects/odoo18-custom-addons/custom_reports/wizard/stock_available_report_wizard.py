# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class StockAvailableReportWizard(models.TransientModel):
    _name = 'stock.available.report.wizard'
    _description = 'Wizard de Reporte de Existencias'

    warehouse_ids = fields.Many2many('stock.warehouse', string='Almacenes', help="Seleccione los almacenes para generar el reporte")
    product_ids = fields.Many2many('product.product', string='Productos', help="Seleccione los productos para generar el reporte")
    category_ids = fields.Many2many('product.category', string='Categorías de Producto', help="Seleccione las categorías de producto para generar el reporte")
    company_ids = fields.Many2many('res.company', string='Compañías', default=lambda self: self.env.companies, help="Seleccione las compañías para generar el reporte")
    cost_method = fields.Selection([
        ('average', 'Precio Promedio'),
        ('last_purchase', 'Último Precio de Compra')
    ], string='Método de Costeo', default='average', required=True)
    is_multi_company = fields.Boolean(compute='_compute_is_multi_company')

    @api.depends('company_ids')
    def _compute_is_multi_company(self):
        for record in self:
            record.is_multi_company = len(self.env.companies) > 1

    @api.model
    def default_get(self, fields_list):
        res = super(StockAvailableReportWizard, self).default_get(fields_list)
        # If we come from the report or explicitly requesting adjustment
        if self.env.context.get('is_adjustment') or self.env.context.get('active_model') == 'stock.available.data.report':
            last_wizard = self.env['stock.available.report.wizard'].sudo().search(
                [('create_uid', '=', self.env.uid)],
                order='id desc',
                limit=1
            )
            if last_wizard:
                res.update({
                    'warehouse_ids': [(6, 0, last_wizard.warehouse_ids.ids)],
                    'product_ids': [(6, 0, last_wizard.product_ids.ids)],
                    'category_ids': [(6, 0, last_wizard.category_ids.ids)],
                    'company_ids': [(6, 0, last_wizard.company_ids.ids)],
                    'cost_method': last_wizard.cost_method,
                })
        return res

    def get_report_data(self):
        warehouse_ids = self.warehouse_ids.ids
        product_ids = self.product_ids.ids
        category_ids = self.category_ids.ids
        company_ids = self.company_ids.ids or [self.env.company.id]
        cost_method = self.cost_method
        lang = self.env.lang or 'en_US'

        params = [company_ids]
        where_clause = "WHERE l.usage = 'internal' AND q.company_id = ANY(%s)"
        
        if product_ids:
            where_clause += " AND q.product_id = ANY(%s)"
            params.append(product_ids)
        if category_ids:
            where_clause += " AND t.categ_id = ANY(%s)"
            params.append(category_ids)
        if warehouse_ids:
            where_clause += " AND l.warehouse_id = ANY(%s)"
            params.append(warehouse_ids)

        query = f"""
            SELECT
                q.product_id,
                t.categ_id as category_id,
                w.id as warehouse_id,
                l.id as location_id,
                q.company_id as company_id,
                COALESCE(t.name->>'{lang}', t.name->>'en_US') as product_name,
                p.default_code as default_code,
                c.complete_name as category_name,
                w.name as warehouse_name,
                SUM(q.quantity) as quantity,
                SUM(q.reserved_quantity) as reserved_quantity,
                SUM(q.quantity - q.reserved_quantity) as available_quantity,
                COALESCE(u.name->>'{lang}', u.name->>'en_US') as uom_name
            FROM
                stock_quant q
                JOIN product_product p ON q.product_id = p.id
                JOIN product_template t ON p.product_tmpl_id = t.id
                JOIN product_category c ON t.categ_id = c.id
                JOIN stock_location l ON q.location_id = l.id
                JOIN stock_warehouse w ON l.warehouse_id = w.id
                JOIN uom_uom u ON t.uom_id = u.id
            {where_clause}
            GROUP BY
                q.product_id, t.categ_id, w.id, l.id, q.company_id, t.name, p.default_code, c.complete_name, w.name, u.name
            HAVING SUM(q.quantity) != 0
            ORDER BY w.name, c.complete_name, product_name
        """
        
        self.env.cr.execute(query, params)
        res_data = self.env.cr.dictfetchall()

        if not res_data:
            return []

        product_all_ids = list(set([row['product_id'] for row in res_data]))
        products = self.env['product.product'].browse(product_all_ids)
        
        # Batch Fetch Costs
        historical_costs = {}
        if cost_method == 'average':
            historical_costs = self._get_batch_monthly_average_costs(product_all_ids, company_ids)
        else:
            # We already have a method for last purchase, could be batched too but let's see
            pass

        for row in res_data:
            company_id = row['company_id']
            product_id = row['product_id']
            product = products.filtered(lambda x: x.id == product_id)
            
            if cost_method == 'average':
                # Priority: 1. standard_price, 2. historical monthly average
                cost = product.with_company(company_id).standard_price
                if cost <= 0:
                    cost = historical_costs.get(product_id) or 0.0
            else:
                price = self._get_last_purchase_price(product_id)
                cost = (price if price > 0 else product.with_company(company_id).standard_price) or 0.0
            
            row['cost'] = cost
            row['total_value'] = row['quantity'] * cost

        return res_data

    def _get_batch_monthly_average_costs(self, product_ids, company_ids):
        """
        Calculates weighted average cost for the most recent month with incoming moves for each product.
        """
        if not product_ids:
            return {}
            
        query = """
            WITH latest_move_months AS (
                SELECT 
                    sm.product_id, 
                    sm.company_id,
                    MAX(DATE_TRUNC('month', sm.date)) as last_month
                FROM stock_move sm
                WHERE sm.product_id = ANY(%s) 
                  AND sm.company_id = ANY(%s)
                  AND sm.state = 'done'
                  AND sm.location_dest_id IN (SELECT id FROM stock_location WHERE usage = 'internal')
                  AND sm.location_id NOT IN (SELECT id FROM stock_location WHERE usage = 'internal')
                GROUP BY sm.product_id, sm.company_id
            ),
            monthly_totals AS (
                SELECT 
                    sm.product_id,
                    SUM(sm.price_unit * sm.product_uom_qty) as total_value,
                    SUM(sm.product_uom_qty) as total_qty
                FROM stock_move sm
                JOIN latest_move_months lmm ON (
                    sm.product_id = lmm.product_id AND 
                    sm.company_id = lmm.company_id AND 
                    DATE_TRUNC('month', sm.date) = lmm.last_month
                )
                WHERE sm.state = 'done'
                  AND sm.location_dest_id IN (SELECT id FROM stock_location WHERE usage = 'internal')
                  AND sm.location_id NOT IN (SELECT id FROM stock_location WHERE usage = 'internal')
                GROUP BY sm.product_id
            )
            SELECT product_id, total_value / NULLIF(total_qty, 0) as avg_price
            FROM monthly_totals
        """
        self.env.cr.execute(query, (product_ids, company_ids))
        res = self.env.cr.dictfetchall()
        return {r['product_id']: (r['avg_price'] or 0.0) for r in res}

    def _get_last_purchase_price(self, product_id):
        query = """
            SELECT pol.price_unit FROM purchase_order_line pol
            JOIN purchase_order po ON po.id = pol.order_id
            WHERE pol.product_id = %s AND po.state IN ('purchase', 'done')
                AND pol.qty_received >= pol.product_qty AND pol.product_qty > 0
                AND NOT EXISTS (
                    SELECT 1 FROM stock_move sm WHERE sm.purchase_line_id = pol.id 
                    AND (sm.origin_returned_move_id IS NOT NULL OR sm.location_dest_id IN (
                        SELECT id FROM stock_location WHERE usage = 'supplier')))
            ORDER BY po.date_approve DESC LIMIT 1
        """
        self.env.cr.execute(query, (product_id,))
        res = self.env.cr.fetchone()
        return res[0] if res else 0.0

    def action_pdf(self):
        self.ensure_one()
        res_data = self.get_report_data()
        if not res_data:
            raise ValidationError("No se encontraron registros para los criterios dados!")
        
        data = {
            'data': res_data,
            'cost_method': 'Precio Promedio' if self.cost_method == 'average' else 'Último Precio de Compra',
            'company': ", ".join(self.company_ids.mapped('name')),
            'date_to': fields.Date.today(),
        }
        return self.env.ref('custom_reports.action_report_stock_avail').report_action(self, data=data)

    def display_report_views(self):
        self.ensure_one()
        res_data = self.get_report_data()
        if not res_data:
            raise ValidationError("No se encontraron registros para los criterios dados!")

        self.env['stock.available.data.report'].search([('create_uid', '=', self.env.uid)]).unlink()

        for row in res_data:
            company = self.env['res.company'].browse(row['company_id'])
            self.env['stock.available.data.report'].create({
                'product_id': row['product_id'],
                'default_code': row['default_code'],
                'category_id': row['category_id'],
                'warehouse_id': row['warehouse_id'],
                'location_id': row['location_id'],
                'quantity': row['quantity'],
                'reserved_quantity': row['reserved_quantity'],
                'available_quantity': row['available_quantity'],
                'uom_name': row['uom_name'],
                'currency_id': company.currency_id.id,
                'cost': row['cost'],
                'total_value': row['total_value'],
                'data_id': self.id,
            })

        tree_view_id = self.env.ref('custom_reports.stock_available_data_report_view_tree_v3').id
        pivot_view_id = self.env.ref('custom_reports.stock_available_data_report_view_pivot').id

        action = self.env.ref('custom_reports.action_stock_available_data_report').sudo().read()[0]
        action['domain'] = [('data_id', '=', self.id)]
        action['target'] = 'main'
        return action

    def action_excel(self):
        # Future implementation
        pass
