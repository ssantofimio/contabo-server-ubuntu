# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import SUPERUSER_ID
from functools import partial
from itertools import groupby



class ProductPack(models.Model):
	_name = 'product.pack'
	_description = "Product Pack"

	bi_product_template = fields.Many2one(comodel_name='product.template', string='Product pack')
	bi_product_product = fields.Many2one(comodel_name='product.product', string='Product pack.',related='bi_product_template.product_variant_id')
	name = fields.Char(related='category_id.name', readonly=True)
	is_required = fields.Boolean('Required')
	category_id = fields.Many2one('pos.category','Category',required=True)
	product_ids = fields.Many2many(comodel_name='product.product', string='Product', required=True,domain="[('pos_categ_ids','=', category_id)]")

	@api.model
	def _load_pos_data_domain(self, data):
		return []

	@api.model
	def _load_pos_data_fields(self, config_id):
		return []

	def _load_pos_data(self, data):
		domain = self._load_pos_data_domain(data)
		fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
		user = self.search_read(domain, fields, load=False)
		return {
			'data': user,
			'fields': fields,
		}

class pos_config(models.Model):
	_inherit = 'pos.config'
	
	use_combo = fields.Boolean('Use combo in POS')
	combo_pack_price = fields.Selection([('all_product', "Total of all combo items "), ('main_product', "Take Price from the Main product")], string='Total Combo Price', default='all_product')


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'


	use_combo = fields.Boolean(related='pos_config_id.use_combo',readonly=False)
	combo_pack_price = fields.Selection(related='pos_config_id.combo_pack_price',readonly=False)

class PosOrderlineSubProduct(models.Model):
	_name = 'pos.orderline.comboproduct'
	_description = "Pos Orderline Combo Products"

	line_uuid = fields.Char()
	combo_product_id = fields.Many2one(comodel_name="product.product")
	combo_qty = fields.Integer(string="Combo Quantity")

	@api.model
	def _load_pos_data_domain(self, data):
		return []

	@api.model
	def _load_pos_data_fields(self, config_id):
		return ['line_uuid', 'combo_product_id', 'combo_qty']

	def _load_pos_data(self, data):
		fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
		user = self.search_read([], [], load=False)
		return {
			'data': user,
			'fields': fields,
		}


class ProductProduct(models.Model):
	_inherit = 'product.template'

	is_pack = fields.Boolean(string='Is Combo Product')
	pack_ids = fields.One2many(comodel_name='product.pack', inverse_name='bi_product_template', string='Product pack')
	combo_limitation = fields.Integer(string="Combo Limitation")


class ProductProduct(models.Model):
	_inherit = 'product.product'

	combo_qty = fields.Integer(string="Combo quantity")

	
	@api.model
	def _load_pos_data_fields(self, config_id):
		result = super()._load_pos_data_fields(config_id)
		result.extend(['is_pack','pack_ids','combo_limitation','combo_qty'])
		return result
	

class POSOrderLoad(models.Model):
	_inherit = 'pos.session'

	@api.model
	def _load_pos_data_models(self, config_id):
		result = super()._load_pos_data_models(config_id)
		m_list = ['product.pack', 'pos.orderline.comboproduct']
		result.extend(m_list)
		return result

class PosOrderLine(models.Model):
	_inherit = 'pos.order.line'

	combo_prod_ids = fields.Many2many("product.product",string="Combo Produts")
	is_pack = fields.Boolean(
		string='Pack',
	)

	@api.model
	def _load_pos_data_fields(self, config_id):
		result = super()._load_pos_data_fields(config_id)
		result.extend(['is_pack','combo_prod_ids'])
		return result


class RelatedPosStock(models.Model):
    _inherit = 'stock.picking'

    def _prepare_stock_move_vals_for_sub_product(self, first_line, item, order_lines):
        return {
            'name': first_line.name,
            'product_uom': item.combo_product_id.uom_id.id,
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': item.combo_product_id.id,
            'product_uom_qty': abs(item.combo_qty),
            'state': 'draft',
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
        }

    def _create_move_from_pos_order_lines(self, lines):
        self.ensure_one()

        if not any(line.combo_prod_ids for line in lines):
            return super()._create_move_from_pos_order_lines(lines)

        all_moves = self.env['stock.move']

        lines_by_product = groupby(sorted(lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)

        for product, olines in lines_by_product:
            order_lines = self.env['pos.order.line'].concat(*olines)
            first_line = order_lines[0]

            # Create main product move
            main_move = self.env['stock.move'].create(
                self._prepare_stock_move_vals(first_line, order_lines)
            )
            if not main_move or not main_move.exists():
                raise UserError(_("Failed to create stock move for main product: %s") % first_line.product_id.display_name)
            all_moves |= main_move

            # Create sub-product moves (combos)
            for line in order_lines:
                combo_sub_prod_ids = self.env['pos.orderline.comboproduct'].search([
                    ('line_uuid', '=', line.uuid),
                    ('combo_product_id', '!=', False)
                ])
                for item in combo_sub_prod_ids:
                    sub_move = self.env['stock.move'].create(
                        self._prepare_stock_move_vals_for_sub_product(first_line, item, order_lines)
                    )
                    if not sub_move or not sub_move.exists():
                        raise UserError(_("Failed to create stock move for combo product: %s") % item.combo_product_id.display_name)
                    all_moves |= sub_move

        if not all_moves:
            raise UserError(_("No stock moves were created for this POS order."))

        confirmed_moves = all_moves._action_confirm()
        confirmed_moves._add_mls_related_to_order(lines, are_qties_done=True)
        confirmed_moves.picked = True

        # Handle lot/serial tracking
        for move in confirmed_moves:
            product = move.product_id
            tracking = product.tracking
            is_main = any(line.product_id == product for line in lines)
            use_lot = self.picking_type_id.use_existing_lots or self.picking_type_id.use_create_lots

            if is_main and tracking != 'none' and use_lot:
                related_lines = [line for line in lines if line.product_id == product]
                for line in related_lines:
                    sum_of_lots = 0
                    for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                        qty = 1 if tracking == 'serial' else abs(line.qty)
                        ml_vals = move._prepare_move_line_vals(qty)
                        ml_vals.update({'quantity': qty})

                        if self.picking_type_id.use_existing_lots:
                            existing_lot = self.env['stock.lot'].search([
                                ('company_id', '=', self.company_id.id),
                                ('product_id', '=', product.id),
                                ('name', '=', lot.lot_name),
                            ], limit=1)

                            if not existing_lot and self.picking_type_id.use_create_lots:
                                existing_lot = self.env['stock.lot'].create({
                                    'company_id': self.company_id.id,
                                    'product_id': product.id,
                                    'name': lot.lot_name,
                                })

                            quant = existing_lot.quant_ids.filtered(
                                lambda q: q.quantity > 0.0 and q.location_id.parent_path.startswith(move.location_id.parent_path)
                            )[-1:]
                            ml_vals.update({
                                'lot_id': existing_lot.id,
                                'location_id': quant.location_id.id if quant else move.location_id.id,
                            })
                        else:
                            ml_vals.update({'lot_name': lot.lot_name})

                        self.env['stock.move.line'].create(ml_vals)
                        sum_of_lots += qty

                    # Handle missing lot qty
                    if abs(line.qty) != sum_of_lots:
                        diff_qty = abs(line.qty) - sum_of_lots
                        ml_vals = move._prepare_move_line_vals()
                        if tracking == 'serial':
                            ml_vals.update({'quantity': 1})
                            for _ in range(int(diff_qty)):
                                self.env['stock.move.line'].create(ml_vals)
                        else:
                            ml_vals.update({'quantity': diff_qty})
                            self.env['stock.move.line'].create(ml_vals)

            else:
                # Handle non-tracked or sub-products
                move._action_assign()
                for move_line in move.move_line_ids:
                    move_line.quantity = move_line.product_packaging_qty
                if float_compare(move.product_uom_qty, move.quantity, precision_rounding=move.product_uom.rounding) > 0:
                    remaining_qty = move.product_uom_qty - move.quantity
                    ml_vals = move._prepare_move_line_vals()
                    ml_vals.update({'quantity': remaining_qty})
                    self.env['stock.move.line'].create(ml_vals)

        # Link owners on return pickings (Odoo stock feature)
        self._link_owner_on_return_picking(lines)

        return confirmed_moves
	
	
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
