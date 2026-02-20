# -*- coding: utf-8 -*-
from odoo import fields, models

class StockAvailableDataReport(models.TransientModel):
    _name = "stock.available.data.report"
    _description = "Datos del Reporte de Existencias"

    product_id = fields.Many2one("product.product", string="Producto")
    default_code = fields.Char(string="Código")
    category_id = fields.Many2one("product.category", string="Categoría")
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén")
    location_id = fields.Many2one("stock.location", string="Ubicación")
    quantity = fields.Float(string="Cantidad a Mano")
    reserved_quantity = fields.Float(string="Cantidad Reservada")
    available_quantity = fields.Float(string="Disponible")
    uom_name = fields.Char(string="UdM")
    currency_id = fields.Many2one('res.currency', string='Moneda')
    cost = fields.Float(string="Costo Unitario", digits='Product Price')
    total_value = fields.Float(string="Valor Total")
    data_id = fields.Many2one('stock.available.report.wizard', string="Asistente Origen")
