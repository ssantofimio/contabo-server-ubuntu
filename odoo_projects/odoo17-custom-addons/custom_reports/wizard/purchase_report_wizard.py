# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseReportWizard(models.TransientModel):
    _name = 'purchase.report.wizard'
    _description = 'Wizard para Seleccionar Columnas del Reporte'

    # Campos para seleccionar columnas
    col_warehouse = fields.Boolean(string='Almacén', default=True)
    col_number = fields.Boolean(string='Número', default=True)
    col_date = fields.Boolean(string='Fecha', default=True)
    col_partner = fields.Boolean(string='Proveedor', default=True)
    col_partner_ref = fields.Boolean(string='Ref. Proveedor', default=False)
    col_buyer = fields.Boolean(string='Comprador', default=True)
    col_state = fields.Boolean(string='Estado', default=True)
    col_subtotal = fields.Boolean(string='Subtotal Base', default=True)
    col_tax = fields.Boolean(string='Impuesto', default=False)
    col_total = fields.Boolean(string='Total', default=True)
    col_planned_date = fields.Boolean(string='Entrega Esperada', default=False)
    col_receipt_status = fields.Boolean(string='Estado de Entrega', default=True)
    col_invoice_status = fields.Boolean(string='Estado de Facturación', default=True)
    col_invoice_state = fields.Boolean(string='Estado Factura', default=False)

    # IDs de las órdenes seleccionadas
    purchase_order_ids = fields.Many2many('purchase.order', string='Órdenes de Compra')

    @api.model
    def default_get(self, fields):
        res = super(PurchaseReportWizard, self).default_get(fields)
        # Si venimos de una selección, pre-cargar los registros
        if self.env.context.get('active_model') == 'purchase.order' and self.env.context.get('active_ids'):
            res['purchase_order_ids'] = [(6, 0, self.env.context.get('active_ids'))]
        return res

    def action_print_report(self):
        """Genera el reporte con las columnas seleccionadas"""
        self.ensure_one()
        
        # Preparar los datos para el reporte
        data = {
            'columns': {
                'warehouse': self.col_warehouse,
                'number': self.col_number,
                'date': self.col_date,
                'partner': self.col_partner,
                'partner_ref': self.col_partner_ref,
                'buyer': self.col_buyer,
                'state': self.col_state,
                'subtotal': self.col_subtotal,
                'tax': self.col_tax,
                'total': self.col_total,
                'planned_date': self.col_planned_date,
                'receipt_status': self.col_receipt_status,
                'invoice_status': self.col_invoice_status,
                'invoice_state': self.col_invoice_state,
            },
            'order_ids': self.purchase_order_ids.ids,
        }
        
        # Generar el reporte pasando los datos
        return self.env.ref('custom_reports.action_report_purchase_order').report_action(
            self.purchase_order_ids, data=data
        )
