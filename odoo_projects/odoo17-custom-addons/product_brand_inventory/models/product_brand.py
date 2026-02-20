from odoo import models, fields, api


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char('Name', required=True)
    product_tmpl_count = fields.Integer('Product Templates', compute='_compute_product_counts')

    @api.depends('name')
    def _compute_product_counts(self):
        for rec in self:
            rec.product_tmpl_count = self.env['product.template'].search_count([('brand_id', '=', rec.id)])


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand', string='Brand')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    brand_id = fields.Many2one('product.brand', related='product_tmpl_id.brand_id', store=True, string='Brand')
