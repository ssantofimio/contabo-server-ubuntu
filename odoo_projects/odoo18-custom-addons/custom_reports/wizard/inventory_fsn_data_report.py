# -*- coding: utf-8 -*-
###############################################################################
#
#  Cybrosys Technologies Pvt. Ltd.
#
#  Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#  Author: Jumana Haseen (odoo@cybrosys.com)
#
#  You can modify it under the terms of the GNU LESSER
#  GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#  You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#  (LGPL v3) along with this program.
#  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import fields, models


class InventoryFSNDataReport(models.TransientModel):
    """This model is for creating a wizard for viewing the report data"""
    _name = "inventory.fsn.data.report"
    _description = "Inventory FSN Data Report"

    product_id = fields.Many2one(
        "product.product", string="Product",
        help="Seleccione los productos para generar el reporte")
    category_id = fields.Many2one(
        "product.category", string="Category",
        help="Seleccione las categorías de producto para generar el reporte")
    company_id = fields.Many2one(
        "res.company", string="Compañía",
        help="Seleccione las compañías para generar el reporte"                         )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        help="Select the warehouse you want to generate the report for")
    opening_stock = fields.Float(
        string="Opening Stock",
        help="Quantity of stock available at the beginning.")
    closing_stock = fields.Float(
        string="Closing Value",
        help="Quantity of stock at the the time of closing.")
    average_stock = fields.Float(string="Average Stock",
                                 help="The average stock inventory.")
    sales = fields.Float(string="Sales",
                         help="Total quantity or value of stock sold.")
    turnover_ratio = fields.Float(string="Turnover Ratio",
                                  help="The frequency at which stock is sold"
                                       " and replaced during a specific period")
    fsn_classification = fields.Char(
        string="FSN Classification",
        help="FSN classification of the stock, which categorizes items based on"
             " their consumption or movement rate.")
    data_id = fields.Many2one('inventory.fsn.report',
                              string="FSN Data", help="corresponding FSN data")
