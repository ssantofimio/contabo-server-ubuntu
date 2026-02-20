from odoo import api, fields, models

class ChangePartnerWizard(models.TransientModel):
    _name = "change.partner.wizard"
    _description = "Cambiar contacto en Picking y documentos asociados"

    picking_id = fields.Many2one("stock.picking", string="Documento No.", required=True, readonly=True)
    partner_id = fields.Many2one("res.partner", string="Nuevo contacto", required=True)

    def action_confirm(self):
        self.ensure_one()
        picking = self.picking_id
        new_partner = self.partner_id

        # Cambiar en el picking
        picking.partner_id = new_partner

        # Cambiar en el origen (orden de venta o compra)
        if picking.sale_id:
            picking.sale_id.partner_id = new_partner
            for invoice in picking.sale_id.invoice_ids:
                invoice.partner_id = new_partner
        if picking.purchase_id:
            picking.purchase_id.partner_id = new_partner
            for invoice in picking.purchase_id.invoice_ids:
                invoice.partner_id = new_partner

        # Cambiar en facturas ligadas al picking
        invoices = self.env["account.move"].search([("invoice_origin", "=", picking.origin)])
        for inv in invoices:
            inv.partner_id = new_partner

        # Cambiar también en devoluciones relacionadas
        return_picks = self.env["stock.picking"].search([("origin", "=", picking.name)])
        for ret in return_picks:
            ret.partner_id = new_partner

        return {"type": "ir.actions.act_window_close"}
