# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class StockAvailableReport(models.AbstractModel):
    _name = 'report.custom_reports.report_stock_avail'
    _description = 'Reporte de Existencias Mejorado'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}
        
        warehouse_ids = data.get('warehouse_ids')
        product_ids = data.get('product_ids')
        category_ids = data.get('category_ids')
        company_ids = data.get('company_ids') or [self.env.company.id]
        cost_method = data.get('cost_method', 'average')
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
                q.company_id,
                l.id as location_id,
                loc.complete_name as location_name,
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
                JOIN stock_location loc ON q.location_id = loc.id
                JOIN stock_warehouse w ON l.warehouse_id = w.id
                JOIN uom_uom u ON t.uom_id = u.id
            {where_clause}
            GROUP BY
                q.product_id, q.company_id, l.id, loc.complete_name, t.name, p.default_code, c.complete_name, w.name, u.name
            HAVING SUM(q.quantity) != 0
            ORDER BY w.name, c.complete_name, product_name
        """
        
        self.env.cr.execute(query, params)
        res_data = self.env.cr.dictfetchall()

        if not res_data:
            raise ValidationError("No se encontraron registros para los criterios dados!")

        product_all_ids = list(set([row['product_id'] for row in res_data]))
        products = self.env['product.product'].browse(product_all_ids)
        
        # Batch Fetch Costs
        historical_costs = {}
        if cost_method == 'average':
            historical_costs = self._get_batch_monthly_average_costs(product_all_ids, company_ids)

        for row in res_data:
            company_id = row['company_id']
            product_id = row['product_id']
            product = products.filtered(lambda x: x.id == product_id)
            
            if cost_method == 'average':
                cost = product.with_company(company_id).standard_price
                if cost <= 0:
                    cost = historical_costs.get(product_id) or 0.0
            else:
                price = self._get_last_purchase_price(product_id)
                cost = (price if price > 0 else product.with_company(company_id).standard_price) or 0.0
            
            row['cost'] = cost
            row['total_value'] = row['quantity'] * cost

        return {
            'data': res_data,
            'cost_method': 'Precio Promedio' if cost_method == 'average' else 'Último Precio de Compra',
            'company': ", ".join(self.env['res.company'].browse(company_ids).mapped('name'))
        }

    def _get_batch_monthly_average_costs(self, product_ids, company_ids):
        if not product_ids:
            return {}
        query = """
            WITH latest_move_months AS (
                SELECT 
                    sm.product_id, sm.company_id,
                    MAX(DATE_TRUNC('month', sm.date)) as last_month
                FROM stock_move sm
                WHERE sm.product_id = ANY(%s) AND sm.company_id = ANY(%s) AND sm.state = 'done'
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
                    sm.product_id = lmm.product_id AND sm.company_id = lmm.company_id AND DATE_TRUNC('month', sm.date) = lmm.last_month
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
