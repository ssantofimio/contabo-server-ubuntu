# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from odoo import http, fields, _
from odoo.http import request
from werkzeug.exceptions import NotFound, BadRequest, Unauthorized
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController

_logger = logging.getLogger(__name__)

class PosSelfOrderCustomerController(PosSelfOrderController):

    @http.route("/pos-self-order/search-partner-by-nif", auth="public", type="json", website=True)
    def search_partner_by_nif(self, nif, access_token):
        pos_config = self._verify_pos_config(access_token)
        partner = request.env['res.partner'].sudo().search([
            ('vat', '=', nif),
            '|', ('company_id', '=', False), ('company_id', '=', pos_config.company_id.id)
        ], limit=1)
        
        if partner:
            # Look for active confirmed orders for this partner in this POS config
            # We look for orders from the last 24 hours that are not paid or cancelled
            active_orders_sudo = request.env['pos.order'].sudo().search([
                ('partner_id', '=', partner.id),
                ('state', 'not in', ['paid', 'cancel']),
                ('config_id', '=', pos_config.id),
                ('date_order', '>=', fields.Datetime.now() - timedelta(hours=24)),
            ], order='id desc')

            orders_data = []
            for order in active_orders_sudo:
                orders_data.append({
                    'id': order.id,
                    'access_token': order.access_token,
                    'pos_reference': order.pos_reference,
                    'state': order.state,
                    'table_id': order.table_id.id if order.table_id else False,
                })

            return {
                'id': partner.id,
                'name': partner.name,
                'street': partner.street,
                'zip': partner.zip,
                'city': partner.city,
                'email': partner.email,
                'phone': partner.phone,
                'mobile': partner.mobile,
                'vat': partner.vat,
                'country_id': partner.country_id.id,
                'state_id': partner.state_id.id,
                'active_orders': orders_data
            }
        return False

    @http.route("/pos-self-order/get-customer-form-data", auth="public", type="json", website=True)
    def get_customer_form_data(self, access_token):
        pos_config = self._verify_pos_config(access_token)
        
        countries_sudo = request.env['res.country'].sudo().search_read([], ['id', 'name'])
        
        # Only fetch states if we have a default country to optimize, or return all if needed
        # For simplicity and to match previous logic, let's return all states
        states_sudo = request.env['res.country.state'].sudo().search_read([], ['id', 'name', 'country_id'])
        
        id_types_sudo = request.env['l10n_latam.identification.type'].sudo().search_read([], ['id', 'name'])
        
        return {
            'countries': countries_sudo,
            'states': states_sudo,
            'identification_types': id_types_sudo,
        }

    @http.route("/pos-self-order/create-partner-custom", auth="public", type="json", website=True)
    def create_partner_custom(self, partner_data, access_token):
        pos_config = self._verify_pos_config(access_token)
        
        try:
            # Prepare values
            vals = {
                'name': partner_data.get('name'),
                'street': partner_data.get('street'),
                'street2': partner_data.get('street2'),
                'zip': partner_data.get('zip'),
                'city': partner_data.get('city'),
                'email': partner_data.get('email'),
                'phone': partner_data.get('phone'),
                'mobile': partner_data.get('mobile'),
                'vat': partner_data.get('vat'),
                'country_id': partner_data.get('country_id'),
                'state_id': partner_data.get('state_id'),
                'lang': partner_data.get('lang', request.env.context.get('lang')),
                'l10n_latam_identification_type_id': partner_data.get('l10n_latam_identification_type_id'),
            }

            # Handle Colombian localization if present
            if vals.get('vat') and vals.get('country_id'):
                country = request.env['res.country'].sudo().browse(vals['country_id'])
                if country.code == 'CO':
                    # Default to NIT/RUT if it contains a hyphen, or CC if it is only numbers
                    # This is a heuristic, better would be to let user choose, but for kiosk simplicity we can guess or use a default.
                    # Or just find 'NIT' or 'CC' type.
                    type_code = 'rut' if '-' in vals['vat'] else 'cc'
                    id_type = request.env['l10n_latam.identification.type'].sudo().search([
                        ('country_id', '=', country.id),
                        ('l10n_co_document_code', '=', type_code)
                    ], limit=1)
                    if id_type:
                        vals['l10n_latam_identification_type_id'] = id_type.id

            partner = request.env['res.partner'].sudo().create(vals)
            return {
                'id': partner.id,
                'name': partner.name,
                'vat': partner.vat,
                'mobile': partner.mobile,
                'phone': partner.phone,
                'email': partner.email,
            }
        except Exception as e:
            # Log the error so it can be seen in odoo logs (if accessible)
            request.env['ir.logging'].sudo().create({
                'name': 'sandor_pos_self_order_ses',
                'type': 'server',
                'level': 'error',
                'dbname': request.db,
                'message': str(e),
                'path': 'controllers/main.py',
                'func': 'create_partner_custom',
                'line': '50',
            })
            return {'error': str(e)}

    @http.route("/pos-self-order/update-partner-custom", auth="public", type="json", website=True)
    def update_partner_custom(self, partner_id, partner_data, access_token):
        self._verify_pos_config(access_token)
        partner = request.env['res.partner'].sudo().browse(partner_id)
        if not partner.exists():
            return {'error': _("Partner not found")}
        
        try:
            vals = {
                'name': partner_data.get('name'),
                'email': partner_data.get('email'),
                'phone': partner_data.get('phone'),
                'mobile': partner_data.get('mobile'),
                'vat': partner_data.get('vat'),
                'street': partner_data.get('street'),
                'city': partner_data.get('city'),
                'zip': partner_data.get('zip'),
                'country_id': partner_data.get('country_id'),
                'state_id': partner_data.get('state_id'),
                'l10n_latam_identification_type_id': partner_data.get('l10n_latam_identification_type_id'),
            }
            # Remove None values
            vals = {k: v for k, v in vals.items() if v is not None}
            partner.write(vals)
            return {
                'id': partner.id,
                'name': partner.name,
                'vat': partner.vat,
                'mobile': partner.mobile,
                'phone': partner.phone,
                'email': partner.email,
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route("/pos-self-order/process-new-order/<device_type>/", auth="public", type="json", website=True)
    def process_new_order(self, order, access_token, table_identifier, device_type):
        _logger.info("DEBUG: process_new_order incoming order keys: %s", list(order.keys()))
        _logger.info("DEBUG: partner_id in order (frontend): %s", order.get('partner_id'))
        
        res = super(PosSelfOrderCustomerController, self).process_new_order(order, access_token, table_identifier, device_type)
        
        partner_id = order.get('partner_id')
        if not partner_id and order.get('data') and isinstance(order['data'], dict):
             partner_id = order['data'].get('partner_id')

        if isinstance(partner_id, list) and len(partner_id) > 0:
            partner_id = partner_id[0]
            
        if partner_id:
            try:
                partner_id_int = int(partner_id)
                order_id = res.get('id')
                _logger.info("DEBUG: Attempting to link order %s to partner %s", order_id, partner_id_int)
                
                pos_order = request.env['pos.order'].sudo().browse(order_id)
                if pos_order.exists():
                    pos_order.write({'partner_id': partner_id_int})
                    _logger.info("DEBUG: Order %s (%s) linked to partner %s SUCCESS", pos_order.name, order_id, partner_id_int)
                    
                    # Force re-export to ensure frontend gets updated partner info
                    res = pos_order.with_context(from_self=True)._export_for_self_order()
                else:
                    _logger.error("DEBUG ERROR: Order %s not found in DB after creation", order_id)
            except Exception as e:
                _logger.error("DEBUG ERROR: Failed to link partner: %s", str(e))
        
        return res

    @http.route('/pos-self-order/get-orders', auth='public', type='json', website=True)
    def get_orders_by_access_token(self, access_token, order_access_tokens):
        pos_config = self._verify_pos_config(access_token)
        _logger.info("DEBUG: get_orders requested for tokens: %s", order_access_tokens)
        
        # FIX: Search globally in config, not just current session
        # Added with_company to ensure lines are visible if they are company-dependent
        orders = request.env['pos.order'].sudo().with_company(pos_config.company_id).search([
            ("config_id", "=", pos_config.id),
            ("access_token", "in", order_access_tokens),
            ("date_order", ">=", fields.Datetime.now() - timedelta(days=7)),
            ('state', 'not in', ['cancel']),
        ])

        if not orders:
            _logger.warning("DEBUG: get_orders found NO matching orders")
            raise NotFound("Orders not found")

        orders_for_ui = []
        for order in orders:
            export = order._export_for_self_order()
            line_count = len(export.get('lines', []))
            _logger.info("DEBUG: Exporting order %s (ID: %s). Lines found: %d. Total: %s", 
                         order.pos_reference, order.id, line_count, export.get('amount_total'))
            orders_for_ui.append(export)

        return orders_for_ui

    @http.route('/pos-self-order/update-existing-order', auth="public", type="json", website=True)
    def update_existing_order(self, order, access_token, table_identifier):
        _logger.info("DEBUG: update_existing_order incoming order ID: %s", order.get('id'))
        
        # 1. Verify Config & Table (Copied logic)
        order_id = order.get('id')
        order_access_token = order.get('access_token')
        pos_config, table = self._verify_authorization(access_token, table_identifier, order.get('take_away'))
        
        # 2. Find Order Globally in Config (Bypassing session restriction)
        pos_order = request.env['pos.order'].sudo().search([
            ('id', '=', order_id),
            ('access_token', '=', order_access_token),
            ('config_id', '=', pos_config.id),
        ], limit=1)

        if not pos_order:
            raise Unauthorized("Order not found in the server !")
        elif pos_order.state != 'draft':
            raise Unauthorized("Order is not in draft state")

        # 3. Process Lines (Standard logic)
        lines = self._process_lines(order.get('lines'), pos_config, pos_order.id, order.get('take_away'))
        for line in lines:
            if line.get('id'):
                # we need to find by uuid because each time we update the order, id of orderlines changed.
                order_line = pos_order.lines.filtered(lambda l: l.uuid == line.get('uuid'))

                if line.get('qty') < order_line.qty:
                    line.set('qty', order_line.qty)

                if order_line:
                    order_line.write({
                        **line,
                    })
            else:
                pos_order.lines.create(line)

        # 4. Update Prices (Standard logic)
        amount_total, amount_untaxed = self._get_order_prices(lines)
        pos_order.write({
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
            'table_id': table.id if table else False,
            'table_stand_number': order.get('table_stand_number'),
        })

        pos_order.send_table_count_notification(pos_order.table_id)
        
        # 5. CUSTOM PARTNER LOGIC (Merged)
        partner_id = order.get('partner_id')
        force_update = order.get('force_partner_update', False)
        
        if not partner_id and order.get('data') and isinstance(order['data'], dict):
             partner_id = order['data'].get('partner_id')

        if isinstance(partner_id, list) and len(partner_id) > 0:
            partner_id = partner_id[0]

        if partner_id:
            try:
                partner_id_int = int(partner_id)
                if force_update or not pos_order.partner_id:
                    pos_order.write({'partner_id': partner_id_int})
                    _logger.info("DEBUG: Order %s (%s) partner linked to %s (force=%s)", pos_order.name, order_id, partner_id_int, force_update)
            except Exception as e:
                _logger.error("DEBUG ERROR: Failed to sync partner for existing order %s: %s", order.get('id'), str(e))

        return pos_order._export_for_self_order()
