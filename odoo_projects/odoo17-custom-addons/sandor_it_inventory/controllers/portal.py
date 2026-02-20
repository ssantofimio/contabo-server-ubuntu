from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64

import logging
_logger = logging.getLogger(__name__)

class ITAssignmentPortal(http.Controller):

    @http.route(['/portal-sign/<int:assignment_id>'], type='http', auth="public", website=True, csrf=False)
    def portal_my_assignment_sign(self, assignment_id, access_token=None, **kw):
        try:
            assignment_sudo = request.env['it.assignment'].sudo().browse(assignment_id)
            if not assignment_sudo.exists() or (access_token != assignment_sudo.access_token):
                return "404 Not Found - Enlace inválido o token incorrecto"

            # Si ya está firmado, mostrar página de "Firma Completada"
            if assignment_sudo.state == 'signed' or assignment_sudo.signature:
                return request.render("sandor_it_inventory.portal_my_assignment_completed", {
                    'assignment': assignment_sudo,
                })

            values = {
                'page_name': 'assignment',
                'assignment': assignment_sudo,
                'access_token': access_token,
            }
            return request.render("sandor_it_inventory.portal_my_assignment_sign", values)
        except Exception as e:
            _logger.error("PORTAL ERROR sign: %s", str(e), exc_info=True)
            return "Internal Error: " + str(e)

    @http.route(['/portal-verify/<int:assignment_id>'], type='http', auth="public", website=True)
    def portal_my_assignment_verify(self, assignment_id, access_token=None, **kw):
        assignment_sudo = request.env['it.assignment'].sudo().browse(assignment_id)
        if not assignment_sudo.exists() or (access_token != assignment_sudo.access_token):
            return "404 Not Found"

        return request.render("sandor_it_inventory.portal_my_assignment_verify", {
            'assignment': assignment_sudo,
            'access_token': access_token,
        })

    @http.route(['/portal-pdf/<int:assignment_id>'], type='http', auth="public", website=True)
    def portal_my_assignment_pdf(self, assignment_id, access_token=None, original=False, **kw):
        assignment_sudo = request.env['it.assignment'].sudo().browse(assignment_id)
        if not assignment_sudo.exists() or (access_token != assignment_sudo.access_token):
             return "404 Not Found"
        
        pdf_content = None
        filename = "Acta_Entrega.pdf"
        
        # Lógica de búsqueda de adjuntos persistidos (los que generamos en el chatter)
        if original:
            # Buscar el acta de asignación (sin firmas)
            attachment = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'it.assignment'),
                ('res_id', '=', assignment_id),
                ('name', 'like', 'Acta_Asignada%')
            ], limit=1)
            if attachment:
                pdf_content = base64.b64decode(attachment.datas)
                filename = attachment.name
        else:
            # Buscar el acta firmada
            attachment = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'it.assignment'),
                ('res_id', '=', assignment_id),
                ('name', 'like', 'Acta_Firmada%')
            ], limit=1)
            if attachment:
                pdf_content = base64.b64decode(attachment.datas)
                filename = attachment.name

        # Si no hay adjunto guardado (o falla la búsqueda), generamos en vivo como respaldo
        if not pdf_content:
            _logger.info(">>> [PORTAL] PDF attachment not found, rendering live for %s", assignment_sudo.name)
            pdf_content = request.env['ir.actions.report'].sudo()._render_qweb_pdf('sandor_it_inventory.action_report_it_assignment', [assignment_id])[0]
        
        pdf_http_headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'inline; filename="{filename}"'),
        ]
        return request.make_response(pdf_content, headers=pdf_http_headers)

    @http.route(['/portal-return-sign/<int:assignment_id>'], type='http', auth="public", website=True, csrf=False)
    def portal_my_assignment_return_sign(self, assignment_id, access_token=None, **kw):
        try:
            assignment_sudo = request.env['it.assignment'].sudo().browse(assignment_id)
            if not assignment_sudo.exists() or (access_token != assignment_sudo.access_token):
                return "404 Not Found - Enlace inválido o token incorrecto"

            # Si ya se devolvió y firmó, mostrar página de éxito
            if assignment_sudo.state == 'returned' and assignment_sudo.return_signature:
                return request.render("sandor_it_inventory.portal_my_assignment_return_completed", {
                    'assignment': assignment_sudo,
                })

            values = {
                'page_name': 'assignment_return',
                'assignment': assignment_sudo,
                'access_token': access_token,
                'date_today': fields.Date.context_today(assignment_sudo),
            }
            return request.render("sandor_it_inventory.portal_my_assignment_return_sign", values)
        except Exception as e:
            _logger.error("PORTAL ERROR return sign: %s", str(e), exc_info=True)
            return "Internal Error: " + str(e)

    @http.route(['/portal-pdf-return/<int:assignment_id>'], type='http', auth="public", website=True)
    def portal_pdf_return(self, assignment_id, access_token=None, **kw):
        assignment_sudo = request.env['it.assignment'].sudo().browse(assignment_id)
        if not assignment_sudo.exists() or (access_token != assignment_sudo.access_token):
             return "404 Not Found"
        
        pdf_content = None
        filename = "Acta_Devolucion_Paz_y_Salvo.pdf"
        
        # Buscar el acta de devolución firmada
        attachment = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'it.assignment'),
            ('res_id', '=', assignment_id),
            ('name', 'like', 'Acta_Devolucion%')
        ], limit=1)
        
        if attachment:
            pdf_content = base64.b64decode(attachment.datas)
            filename = attachment.name
        
        if not pdf_content:
            # Fallback a renderizado en vivo
            pdf_content = request.env['ir.actions.report'].sudo()._render_qweb_pdf('sandor_it_inventory.action_report_it_return', [assignment_id])[0]
        
        pdf_http_headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'inline; filename="{filename}"'),
        ]
        return request.make_response(pdf_content, headers=pdf_http_headers)

    @http.route(['/portal-return-sign-update/<int:assignment_id>'], type='json', auth="public", website=True)
    def portal_my_assignment_return_sign_update(self, assignment_id, access_token=None, signature=None, **kw):
        assignment_sudo = request.env['it.assignment'].sudo().browse(assignment_id)
        
        if not assignment_sudo.exists() or not access_token or access_token != assignment_sudo.access_token:
            return {'error': _('Acceso denegado')}

        if assignment_sudo.state == 'returned' and assignment_sudo.return_signature:
            return {'error': _('Este reintegro ya ha sido formalizado.')}

        if not signature:
            return {'error': _('Firma requerida para el Paz y Salvo')}

        ip = request.httprequest.headers.get('X-Forwarded-For', request.httprequest.remote_addr)
        if ip and ',' in ip: ip = ip.split(',')[0].strip()
        
        # El write disparará el action_return_sign en el modelo
        assignment_sudo.write({
            'return_signature': signature.split(',')[1] if ',' in signature else signature,
            'return_signed_by': assignment_sudo.employee_id.name,
            'return_signed_on': fields.Datetime.now(),
            'state': 'returned',
            'return_signer_ip': ip,
            'return_signer_user_agent': request.httprequest.user_agent.string,
        })
        
        return {'success': True}

    @http.route(['/portal-sign-update/<int:assignment_id>'], type='json', auth="public", website=True)
    def portal_my_assignment_sign_update(self, assignment_id, access_token=None, signature=None, **kw):
        assignment_sudo = request.env['it.assignment'].sudo().browse(assignment_id)
        
        if not assignment_sudo.exists():
            return {'error': _('Registro no encontrado')}

        if not access_token or access_token != assignment_sudo.access_token:
            return {'error': _('Acceso denegado')}

        if assignment_sudo.state == 'signed' or assignment_sudo.signature:
            return {'error': _('Este documento ya ha sido firmado.')}

        if not signature:
            return {'error': _('Firma requerida')}

        ip = request.httprequest.headers.get('X-Forwarded-For', request.httprequest.remote_addr)
        if ip and ',' in ip: ip = ip.split(',')[0].strip()
        
        assignment_sudo.write({
            'signature': signature.split(',')[1] if ',' in signature else signature,
            'signed_by': assignment_sudo.employee_id.name,
            'signed_on': fields.Datetime.now(),
            'state': 'signed',
            'signer_ip': ip,
            'signer_user_agent': request.httprequest.user_agent.string,
        })
        
        return {'success': True}
