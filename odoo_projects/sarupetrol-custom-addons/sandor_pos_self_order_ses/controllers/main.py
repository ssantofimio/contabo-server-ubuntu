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
        self._verify_pos_config(access_token)
        
        countries_sudo = request.env['res.country'].sudo().search_read([], ['id', 'name'])
        states_sudo = request.env['res.country.state'].sudo().search_read([], ['id', 'name', 'country_id'])
        id_types_sudo = request.env['l10n_latam.identification.type'].sudo().search_read([], ['id', 'name'])
        
        return {
            'countries': countries_sudo,
            'states': states_sudo,
            'identification_types': id_types_sudo,
        }

    @http.route("/pos-self-order/create-partner-custom", auth="public", type="json", website=True)
    def create_partner_custom(self, partner_data, access_token):
        self._verify_pos_config(access_token)
        
        try:
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

            if vals.get('vat') and vals.get('country_id'):
                country = request.env['res.country'].sudo().browse(vals['country_id'])
                if country.code == 'CO':
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
            _logger.error("Error creating partner: %s", str(e))
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

    # Odoo 18 Override
    @http.route("/pos-self-order/process-order-args/<device_type>/", auth="public", type="json", website=True)
    def process_order_args(self, order, access_token, table_identifier, device_type, **kwargs):
        # We handle partner_id if it's explicitly passed in order (which we do in JS update)
        # Standard sync_from_ui handles it, but let's be sure.
        res = super().process_order_args(order, access_token, table_identifier, device_type, **kwargs)
        
        # If successfully processed, and we have a partner_id in the original but Odoo somehow didn't link it 
        # (e.g. if it was draft and update didn't trigger partner set)
        partner_id = order.get('partner_id')
        if partner_id:
            try:
                # 'pos.order' is a list of results in Odoo 18 return
                if res.get('pos.order') and len(res['pos.order']) > 0:
                    order_id = res['pos.order'][0].get('id')
                    pos_order = request.env['pos.order'].sudo().browse(order_id)
                    if pos_order.exists() and not pos_order.partner_id:
                        pos_order.write({'partner_id': int(partner_id)})
                        # Refresh results with the new partner info if needed, 
                        # but usually the next fetch will handle it.
            except Exception as e:
                 _logger.error("Failed to force link partner: %s", str(e))
        
        return res

    # Odoo 18 Override - Fixes the 404 and the format mismatch
    @http.route(['/pos-self-order/get-orders/', '/pos-self-order/get-orders'], auth='public', type='json', website=True)
    def get_orders_by_access_token(self, access_token, order_access_tokens, table_identifier=None):
        pos_config = self._verify_pos_config(access_token)
        
        # Odoo 18 sends access tokens as a list of dicts: [{'access_token': '...', 'write_date': '...'}, ...]
        # We need to extract the tokens for the domain
        tokens = [data.get('access_token') for data in order_access_tokens if data.get('access_token')]
        
        _logger.info("DEBUG: get_orders requested for tokens in Odoo 18: %s", tokens)
        
        # Search criteria
        domain = [
            ("config_id", "=", pos_config.id),
            ("access_token", "in", tokens),
            ('state', 'not in', ['cancel']),
        ]
        
        orders = request.env['pos.order'].sudo().with_company(pos_config.company_id).search(domain)

        if not orders:
            return {} # Base Odoo 18 returns empty dict if nothing found

        return self._generate_return_values(orders, pos_config)
