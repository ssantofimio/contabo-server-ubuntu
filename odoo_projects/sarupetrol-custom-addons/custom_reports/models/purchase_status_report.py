# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseStatusReport(models.Model):
    _inherit = 'purchase.order'
    _description = 'Purchase Order Status Report'

    # Computed fields for Spanish translations and additional data
    state_display_es = fields.Char(
        string='Estado',
        compute='_compute_state_display_es',
        store=True,
        help='Estado de la orden de compra en español'
    )
    
    receipt_status_display_es = fields.Char(
        string='Estado de entrega',
        compute='_compute_receipt_status_display_es',
        store=True,
        help='Estado de recepción en español'
    )
    
    invoice_status_display_es = fields.Char(
        string='Estado de facturación',
        compute='_compute_invoice_status_display_es',
        store=True,
        help='Estado de facturación en español'
    )
    
    invoice_state_summary = fields.Char(
        string='Estado Factura',
        compute='_compute_invoice_state_summary',
        help='Estados de facturas relacionadas agregados'
    )
    
    warehouse_name = fields.Char(
        string='Almacén',
        compute='_compute_warehouse_name',
        store=True,
        help='Nombre del almacén desde el tipo de picking'
    )
    
    date_order_local = fields.Date(
        string='Fecha',
        compute='_compute_date_order_local',
        store=True,
        help='Fecha de orden ajustada a hora local (-5 horas)'
    )
    
    date_planned_local = fields.Date(
        string='Entrega Esperada',
        compute='_compute_date_planned_local',
        store=True,
        help='Fecha de entrega esperada ajustada a hora local (-5 horas)'
    )

    @api.depends('state')
    def _compute_state_display_es(self):
        """Translate purchase order state to Spanish"""
        state_translations = {
            'draft': 'Cotización',
            'sent': 'Cotización',
            'to approve': 'Por aprobar',
            'purchase': 'Orden de Compra',
            'done': 'Bloqueado',
            'cancel': 'Cancelado',
        }
        for record in self:
            record.state_display_es = state_translations.get(record.state, record.state or '')

    @api.depends('receipt_status')
    def _compute_receipt_status_display_es(self):
        """Translate receipt status to Spanish"""
        receipt_translations = {
            'pending': 'Sin Recibir',
            'partial': 'Parcial',
            'full': 'Recibido',
        }
        for record in self:
            # receipt_status comes from purchase_stock module
            receipt_status = getattr(record, 'receipt_status', False)
            if receipt_status:
                record.receipt_status_display_es = receipt_translations.get(receipt_status, receipt_status)
            else:
                record.receipt_status_display_es = ''

    @api.depends('invoice_status')
    def _compute_invoice_status_display_es(self):
        """Translate invoice status to Spanish"""
        invoice_translations = {
            'no': 'Nada por Facturar',
            'to invoice': 'Por Facturar',
            'invoiced': 'Facturado',
        }
        for record in self:
            record.invoice_status_display_es = invoice_translations.get(record.invoice_status, record.invoice_status or '')

    @api.depends('invoice_ids', 'invoice_ids.state')
    def _compute_invoice_state_summary(self):
        """Aggregate invoice states from related account.move records"""
        invoice_state_translations = {
            'draft': 'Borrador',
            'posted': 'Confirmada',
            'cancel': 'Cancelada',
        }
        for record in self:
            if record.invoice_ids:
                # Get unique translated states
                states = set()
                for invoice in record.invoice_ids:
                    if invoice.state:
                        translated_state = invoice_state_translations.get(invoice.state, invoice.state)
                        states.add(translated_state)
                # Join with comma separator
                record.invoice_state_summary = ', '.join(sorted(states)) if states else ''
            else:
                record.invoice_state_summary = ''

    @api.depends('picking_type_id', 'picking_type_id.warehouse_id', 'picking_type_id.warehouse_id.name')
    def _compute_warehouse_name(self):
        """Get warehouse name from picking type"""
        for record in self:
            if record.picking_type_id and record.picking_type_id.warehouse_id:
                record.warehouse_name = record.picking_type_id.warehouse_id.name
            else:
                record.warehouse_name = ''

    @api.depends('date_order')
    def _compute_date_order_local(self):
        """Convert date_order to local date (UTC - 5 hours)"""
        for record in self:
            if record.date_order:
                # Subtract 5 hours and convert to date
                from datetime import timedelta
                local_datetime = record.date_order - timedelta(hours=5)
                record.date_order_local = local_datetime.date()
            else:
                record.date_order_local = False

    @api.depends('date_planned')
    def _compute_date_planned_local(self):
        """Convert date_planned to local date (UTC - 5 hours)"""
        for record in self:
            if record.date_planned:
                # Subtract 5 hours and convert to date
                from datetime import timedelta
                local_datetime = record.date_planned - timedelta(hours=5)
                record.date_planned_local = local_datetime.date()
            else:
                record.date_planned_local = False
