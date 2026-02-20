from odoo import models, fields, api, _, http
from odoo.http import request
from odoo.exceptions import ValidationError
import base64
import hashlib
import logging
_logger = logging.getLogger(__name__)

class ITAssignment(models.Model):
    _name = 'it.assignment'
    _description = 'IT Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'assignment_date desc, name desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id', readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id', readonly=True, store=True)
    employee_id_type_id = fields.Many2one('l10n_latam.identification.type', string='ID Type', 
                                         compute='_compute_employee_id_data', store=True)
    employee_id_number = fields.Char(string='ID Number', compute='_compute_employee_id_data', store=True)
    employee_email = fields.Char(string='Email', related='employee_id.work_email', readonly=True)
    work_location_id = fields.Many2one('hr.work.location', string='Work Location', related='employee_id.work_location_id', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    assignment_date = fields.Date(string='Assignment Date', default=fields.Date.context_today, tracking=True)
    amount_total = fields.Monetary(string='Total Value', compute='_compute_amount_total', store=True, currency_field='currency_id')

    @api.depends('line_ids.standard_price')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('standard_price'))

    @api.depends('employee_id', 'employee_id.work_contact_id', 'employee_id.work_contact_id.l10n_latam_identification_type_id', 'employee_id.work_contact_id.vat')
    def _compute_employee_id_data(self):
        for rec in self:
            id_type = False
            vat = False
            if rec.employee_id and rec.employee_id.work_contact_id:
                partner = rec.employee_id.work_contact_id
                id_type = getattr(partner, 'l10n_latam_identification_type_id', False)
                vat = getattr(partner, 'vat', False)
            rec.employee_id_type_id = id_type
            rec.employee_id_number = vat
    
    line_ids = fields.One2many('it.assignment.line', 'assignment_id', string='Assignment Lines')
    asset_ids = fields.Many2many('it.assets', string='Equipment (Serial Numbers)', tracking=True)
    component_ids = fields.Many2many('it.components', string='Components', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('signed', 'Asignado'),
        ('returning', 'En Devolución'),
        ('returned', 'Devuelto'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')

    discount_ids = fields.One2many('it.assignment.discount', 'assignment_id', string='Discounts/Depreciation')
    
    signature = fields.Binary(string='Firma Empleado', help='Firma capturada del empleado', copy=False)
    signed_by = fields.Char(string='Firmado por', help='Nombre de la persona que firmó', copy=False)
    signed_on = fields.Datetime(string='Firmado el', help='Fecha y hora de la firma', copy=False)
    signer_ip = fields.Char(string='IP del Firmante', help='Dirección IP desde donde se realizó la firma', copy=False)
    signer_user_agent = fields.Text(string='Dispositivo/Navegador', help='Información detallada del dispositivo y navegador del firmante', copy=False)
    document_hash = fields.Char(string='Hash del Documento (SHA256)', help='Identificador único del contenido del documento al momento de firmar', copy=False)
    
    # Campos de Auditoría para Devolución
    return_signature = fields.Binary(string='Firma de Devolución', help='Firma capturada al momento del reintegro', copy=False)
    return_signed_by = fields.Char(string='Devuelto por', help='Nombre de la persona que devuelve', copy=False)
    return_signed_on = fields.Datetime(string='Devuelto el', help='Fecha y hora de la devolución', copy=False)
    return_signer_ip = fields.Char(string='IP de Devolución', help='IP desde donde se firmó el reintegro', copy=False)
    return_signer_user_agent = fields.Text(string='Dispositivo de Devolución', help='Información del dispositivo que firma la devolución', copy=False)
    return_document_hash = fields.Char(string='Hash de Devolución', help='Hash único que certifica el cierre del acta', copy=False)

    portal_sign_url = fields.Char(string='Enlace de Firma', compute='_compute_portal_urls', help='Enlace para que el empleado firme el acta desde el portal.')
    portal_return_url = fields.Char(string='Enlace de Devolución', compute='_compute_portal_urls', help='Enlace para formalizar la devolución desde el portal.')
    portal_verify_url = fields.Char(string='Enlace de Verificación', compute='_compute_portal_urls', help='Enlace para verificar la autenticidad del acta.')

    def _compute_portal_urls(self):
        base_url = self.get_base_url()
        for rec in self:
            if not rec.access_token:
                rec._portal_ensure_token()
            sign_url = f"/portal-sign/{rec.id}?access_token={rec.access_token}"
            rec.portal_sign_url = f"{base_url.rstrip('/')}{sign_url}"
            return_url = f"/portal-return-sign/{rec.id}?access_token={rec.access_token}"
            rec.portal_return_url = f"{base_url.rstrip('/')}{return_url}"
            verify_url = f"/portal-verify/{rec.id}?access_token={rec.access_token}"
            rec.portal_verify_url = f"{base_url.rstrip('/')}{verify_url}"


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = _('New')
        return super(ITAssignment, self).create(vals_list)

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_("Operación no válida: Debe agregar líneas antes de validar."))
            
            # Validación de datos obligatorios para legalidad de firma
            missing_fields = []
            if not rec.employee_id_type_id: missing_fields.append(_("Tipo de Identificación"))
            if not rec.employee_id_number: missing_fields.append(_("Número de Identificación"))
            if not rec.employee_email: missing_fields.append(_("Email"))
            
            if missing_fields:
                raise ValidationError(_(
                    "No se puede confirmar la asignación porque los siguientes datos del empleado son obligatorios para la legalidad del acta:\n- %s\n\nPor favor, complete estos datos en la ficha del empleado o en su contacto vinculado."
                ) % "\n- ".join(missing_fields))

            # --- ADVERTENCIA DE DESCUENTOS (NO BLOQUEANTE) ---
            if not self.env.context.get('skip_discount_check'):
                discountable_lines = rec.line_ids.filtered(lambda l: l.it_asset_type_id.is_discountable)
                existing_discount_line_ids = rec.discount_ids.mapped('assignment_line_id').ids
                missing_discounts = discountable_lines.filtered(lambda l: l.id not in existing_discount_line_ids)
                
                if missing_discounts:
                    return {
                        'name': _('Advertencia de Descuentos'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'it.assignment.confirm.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_assignment_id': rec.id,
                            'default_product_ids': missing_discounts.mapped('product_id').ids,
                            'default_message': _(
                                "¡ATENCIÓN! Los siguientes productos están sujetos a depreciación pero no se han configurado en la pestaña de Descuentos.\n"
                                "¿Desea confirmar el acta de todas formas o prefiere regresar para agregarlos?"
                            )
                        }
                    }
            # ---------------------------------------------------------

            if rec.name == _('New'):
                rec.name = self.env['ir.sequence'].next_by_code('it.assignment') or _('New')

            for line in rec.line_ids:
                if line.product_id and line.product_id.it_unique_assignment:
                    current_assign = line.product_id.it_current_assignment_id
                    if current_assign and current_assign.id != rec.id and current_assign.state in ('confirmed', 'signed'):
                        raise ValidationError(_(
                            "El producto '%s' ya se encuentra asignado en el documento %s. "
                            "No se puede confirmar esta entrega hasta que el producto esté disponible."
                        ) % (line.product_id.name, current_assign.name))

            rec.state = 'confirmed'
            if rec.name == _('New'):
                rec.name = self.env['ir.sequence'].next_by_code('it.assignment') or _('New')
            
            rec._generate_and_attach_report(message=_("El Documento de Entrega ha sido generado automáticamente al confirmar la asignación."))

            if rec.employee_id.user_id:
                for asset in rec.asset_ids:
                    asset.item_user = rec.employee_id.user_id
                for component in rec.component_ids:
                    if rec.employee_id.user_id.id not in component.user.ids:
                        component.user = [(4, rec.employee_id.user_id.id)]
            
            for line in rec.line_ids:
                if line.product_id:
                    line.product_id.write({
                        'it_current_assignment_id': rec.id,
                        'it_current_employee_id': rec.employee_id.id,
                        'it_assignment_date': rec.assignment_date
                    })

    def action_return(self):
        for rec in self:
            if rec.state not in ('confirmed', 'signed'):
                raise ValidationError(_("Solo se pueden registrar devoluciones de documentos confirmados o firmados."))
            
            # Cambiar a estado de retorno en proceso
            rec.state = 'returning'
            
            # Generar acta de devolución inicial (sin firma)
            rec._generate_and_attach_return_report(
                message=_("Se ha iniciado el proceso de devolución. El empleado puede ahora firmar el Acta de Devolución y Paz y Salvo desde el portal para formalizar la entrega de equipos.")
            )

    def action_return_sign(self, ip_address=None, user_agent=None):
        for rec in self:
            if rec.state not in ['returning', 'returned']:
                continue
            if not rec.return_signature:
                continue
            
            if not rec.return_document_hash:
                _logger.info(">>> [DEBUG RETURN] Generating hash for %s", rec.name)
                vals = {
                    'state': 'returned'
                }
                if not rec.return_signed_by:
                    vals['return_signed_by'] = rec.employee_id.name
                if not rec.return_signed_on:
                    vals['return_signed_on'] = fields.Datetime.now()
                
                if not ip_address and request and hasattr(request, 'httprequest'):
                    ip = request.httprequest.headers.get('X-Forwarded-For', request.httprequest.remote_addr)
                    if ip and ',' in ip: ip = ip.split(',')[0].strip()
                    ip_address = ip
                
                if not user_agent and request and hasattr(request, 'httprequest'):
                    user_agent = request.httprequest.user_agent.string
                    
                vals['return_signer_ip'] = ip_address or rec.return_signer_ip or ''
                vals['return_signer_user_agent'] = user_agent or rec.return_signer_user_agent or ''
                
                s_on = vals.get('return_signed_on', rec.return_signed_on)
                s_by = vals.get('return_signed_by', rec.return_signed_by)
                s_ip = vals.get('return_signer_ip', rec.return_signer_ip)
                s_ua = vals.get('return_signer_user_agent', rec.return_signer_user_agent)
                
                meta = f"RETURN-{rec.id}-{s_on}-{s_by}-{s_ip}-{s_ua}-{rec.access_token}"
                vals['return_document_hash'] = hashlib.sha256(meta.encode()).hexdigest()
                
                _logger.info(">>> [DEBUG RETURN] Generated Return Hash: %s", vals['return_document_hash'])
                rec.with_context(__no_sign_recursion=True).write(vals)
                
                # AHORA SÍ, liberamos los equipos del inventario
                for line in rec.line_ids:
                    if line.product_id and line.product_id.it_current_assignment_id == rec:
                        line.product_id.write({
                            'it_current_assignment_id': False,
                            'it_current_employee_id': False,
                            'it_assignment_date': False
                        })
                
                _logger.info(">>> [DEBUG RETURN] Lifecycle closed for %s. Products released.", rec.name)

            # Generar Acta de Devolución Final y Paz y Salvo
            rec._generate_and_attach_return_report(
                message=_("✅ Ciclo Cerrado: El empleado ha firmado la devolución satisfactoriamente. Se adjunta el Acta de Devolución y Certificado de Paz y Salvo legalizado.")
            )

    def _generate_and_attach_return_report(self, message=None):
        report_action = self.env.ref('sandor_it_inventory.action_report_it_return', raise_if_not_found=False)
        if not report_action:
            _logger.error("!!! [DEBUG REPORT] Return Report action NOT FOUND")
            return
            
        for rec in self:
            try:
                prefix = "Acta_Devolucion" if rec.state == 'returned' else "Borrador_Devolucion"
                file_name = f"{prefix}_{rec.name.replace('/', '_')}.pdf"
                
                pdf_content, report_type = report_action.sudo()._render_qweb_pdf('sandor_it_inventory.action_report_it_return', res_ids=rec.ids)
                
                if pdf_content:
                    rec.sudo().message_post(
                        body=message or "Se ha generado el documento de devolución.",
                        attachments=[(file_name, pdf_content)],
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment'
                    )
            except Exception as e:
                _logger.error("!!! [DEBUG REPORT] Error in Return Report for %s: %s", rec.name, str(e))

    def action_sign(self, ip_address=None, user_agent=None):
        if self._context.get('__no_sign_recursion'):
            return
            
        for rec in self:
            _logger.info(">>> [DEBUG SIGN] Starting action_sign for %s (ID: %s, State: %s)", rec.name, rec.id, rec.state)
            if rec.state not in ['confirmed', 'signed']:
                continue
            if not rec.signature:
                continue
            
            # Solo generamos hash y actualizamos si no tiene hash (primera vez)
            if not rec.document_hash:
                vals = {
                    'state': 'signed'
                }
                if not rec.signed_by:
                    vals['signed_by'] = rec.employee_id.name
                if not rec.signed_on:
                    vals['signed_on'] = fields.Datetime.now()
                
                if not ip_address and request and hasattr(request, 'httprequest'):
                    ip = request.httprequest.headers.get('X-Forwarded-For', request.httprequest.remote_addr)
                    if ip and ',' in ip: ip = ip.split(',')[0].strip()
                    ip_address = ip
                
                if not user_agent and request and hasattr(request, 'httprequest'):
                    user_agent = request.httprequest.user_agent.string
                    
                vals['signer_ip'] = ip_address or rec.signer_ip or ''
                vals['signer_user_agent'] = user_agent or rec.signer_user_agent or ''
                
                s_on = vals.get('signed_on', rec.signed_on)
                s_by = vals.get('signed_by', rec.signed_by)
                s_ip = vals.get('signer_ip', rec.signer_ip)
                s_ua = vals.get('signer_user_agent', rec.signer_user_agent)
                
                metadata_str = f"{rec.id}-{s_on}-{s_by}-{s_ip}-{s_ua}"
                vals['document_hash'] = hashlib.sha256(metadata_str.encode()).hexdigest()
                
                _logger.info(">>> [DEBUG SIGN] Hash generated: %s", vals['document_hash'])
                rec.with_context(__no_sign_recursion=True).write(vals)
            
            # Siempre intentamos generar el reporte de firma si el mensaje no está o el usuario lo pide
            _logger.info(">>> [DEBUG SIGN] Triggering report for %s", rec.name)
            rec.with_context(__no_sign_recursion=True)._generate_and_attach_report(
                message=_("✅ Documento Legalizado: El acta ha sido firmada por el empleado. Se adjunta el PDF con el certificado de auditoría y código QR de verificación.")
            )

    def _generate_and_attach_report(self, message=None):
        report_action = self.env.ref('sandor_it_inventory.action_report_it_assignment')
        if not report_action:
            _logger.error("!!! [DEBUG REPORT] Report action NOT FOUND")
            return
            
        for rec in self:
            try:
                prefix = "Acta_Firmada" if rec.state == 'signed' else "Acta_Asignada"
                file_name = f"{prefix}_{rec.name.replace('/', '_')}.pdf"

                _logger.info(">>> [DEBUG REPORT] Generating and posting PDF for %s (State: %s)...", rec.name, rec.state)
                
                pdf_content, report_type = report_action.sudo()._render_qweb_pdf('sandor_it_inventory.action_report_it_assignment', res_ids=rec.ids)
                
                if pdf_content:
                    if message:
                        # Usamos el parámetro attachments directamente en message_post
                        rec.sudo().message_post(
                            body=message,
                            attachments=[(file_name, pdf_content)],
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment'
                        )
                        _logger.info(">>> [DEBUG REPORT] Message posted with attachment for %s", rec.name)
                else:
                    _logger.error("!!! [DEBUG REPORT] PDF content is empty for %s", rec.name)
            except Exception as e:
                _logger.error("!!! [DEBUG REPORT] Error for %s: %s", rec.name, str(e), exc_info=True)

    def write(self, vals):
        is_signing = 'signature' in vals and vals['signature']
        is_returning = 'return_signature' in vals and vals['return_signature']
        res = super(ITAssignment, self).write(vals)
        if not self._context.get('__no_sign_recursion'):
            if is_signing:
                _logger.info(">>> [DEBUG WRITE] Signature detected for %s", self.name)
                self.action_sign()
            if is_returning:
                _logger.info(">>> [DEBUG WRITE] Return Signature detected for %s", self.name)
                self.action_return_sign()
        return res

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'signed':
                raise ValidationError(_("No se puede cancelar un acta que ya ha sido firmada. Debe registrar una devolución si desea anular la entrega."))
            rec.state = 'cancelled'
            for line in rec.line_ids:
                if line.product_id and line.product_id.it_current_assignment_id == rec:
                    line.product_id.write({
                        'it_current_assignment_id': False,
                        'it_current_employee_id': False,
                        'it_assignment_date': False
                    })

    def action_send_email(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        
        # Seleccionar plantilla según el estado (V2 forzada)
        if self.state == 'returned':
            template_id = self.env.ref('sandor_it_inventory.email_template_it_assignment_signed_v2', raise_if_not_found=False) # Reuse signed or create new? Let's use return template if we want
        elif self.state == 'returning':
            template_id = self.env.ref('sandor_it_inventory.email_template_it_return_v2', raise_if_not_found=False)
        elif self.state == 'signed' or self.signature:
            template_id = self.env.ref('sandor_it_inventory.email_template_it_assignment_signed_v2', raise_if_not_found=False)
        else:
            template_id = self.env.ref('sandor_it_inventory.email_template_it_assignment_v2', raise_if_not_found=False)
            
        ctx = {
            'default_model': 'it.assignment',
            'default_res_ids': self.ids,
            'default_use_template': bool(template_id),
            'default_template_id': template_id.id if template_id else False,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'force_email_send': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def _fix_missing_assignments(self):
        assignments = self.search([('state', '=', 'confirmed')])
        for rec in assignments:
            for line in rec.line_ids:
                if line.product_id:
                    line.product_id.write({
                        'it_current_assignment_id': rec.id,
                        'it_current_employee_id': rec.employee_id.id,
                        'it_assignment_date': rec.assignment_date
                    })

class ITAssignmentLine(models.Model):
    _name = 'it.assignment.line'
    _description = 'IT Assignment Line'
    _rec_name = 'display_name'

    assignment_id = fields.Many2one('it.assignment', string='Assignment Reference', ondelete='cascade', index=True)
    product_id = fields.Many2one('product.template', string='Product', required=True,
                                 domain="[('available_in_it_inventory', '=', True), '|', ('it_unique_assignment', '=', False), ('it_current_assignment_id', '=', False)]")
    
    display_name = fields.Char(string='Line Name', compute='_compute_display_name', store=True)

    @api.constrains('product_id', 'assignment_id')
    def _check_duplicate_product(self):
        for rec in self:
            if not rec.product_id or not rec.assignment_id:
                continue
            if not rec.product_id.it_unique_assignment:
                continue
            duplicate = self.search([
                ('assignment_id', '=', rec.assignment_id.id),
                ('product_id', '=', rec.product_id.id),
                ('id', '!=', rec.id)
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    "El producto '%s' es de Asignación Única (Serie) y ya ha sido agregado a esta asignación. "
                    "No se permiten duplicados del mismo producto serializado en el mismo documento."
                ) % rec.product_id.name)

    @api.depends('product_id', 'product_id.name', 'product_id.default_code')
    def _compute_display_name(self):
        for rec in self:
            name = rec.product_id.name or ''
            if rec.product_id.default_code:
                name = f"[{rec.product_id.default_code}] {name}"
            rec.display_name = name
    
    state = fields.Selection(related='assignment_id.state', string='Status', store=True)
    employee_id = fields.Many2one('hr.employee', related='assignment_id.employee_id', string='Employee', readonly=True, store=True)
    department_id = fields.Many2one('hr.department', related='assignment_id.department_id', string='Department', readonly=True, store=True)
    assignment_date = fields.Date(related='assignment_id.assignment_date', string='Assignment Date', readonly=True, store=True)
    default_code = fields.Char(string='Internal Reference', related='product_id.default_code', readonly=True, store=True)
    it_brand_id = fields.Many2one('asset.brand', string='Brand', related='product_id.it_brand_id', readonly=True, store=True)
    it_asset_type_id = fields.Many2one('asset.type', string='Asset Type', related='product_id.it_asset_type_id', readonly=True, store=True)
    it_serial_number = fields.Char(string='Serial Number', related='product_id.it_serial_number', readonly=True, store=True)
    list_price = fields.Float(string='Sale Price', related='product_id.list_price', readonly=True, store=True)
    standard_price = fields.Float(string='Cost Price', related='product_id.standard_price', readonly=True, store=True)
    it_unique_assignment = fields.Boolean(related='product_id.it_unique_assignment', readonly=True, store=True)

class ITAssignmentDiscount(models.Model):
    _name = 'it.assignment.discount'
    _description = 'IT Assignment Discount Detail'

    assignment_id = fields.Many2one('it.assignment', string='Assignment', ondelete='cascade', index=True)
    currency_id = fields.Many2one('res.currency', related='assignment_id.currency_id')
    
    assignment_line_id = fields.Many2one(
        'it.assignment.line', 
        string='Assigned Asset', 
        required=True,
        domain="[('assignment_id', '=', assignment_id), ('it_asset_type_id.is_discountable', '=', True)]"
    )
    
    product_id = fields.Many2one('product.template', related='assignment_line_id.product_id', string='Product', readonly=True)
    default_code = fields.Char(string='Internal Reference', related='assignment_line_id.default_code', readonly=True)
    it_serial_number = fields.Char(string='Serial Number', related='assignment_line_id.it_serial_number', readonly=True)
    discount_value = fields.Monetary(string='Base Value for Table', currency_field='currency_id', required=True)

    @api.onchange('assignment_line_id')
    def _onchange_assignment_line_id(self):
        if self.assignment_line_id:
            self.discount_value = self.assignment_line_id.standard_price or self.assignment_line_id.product_id.list_price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('assignment_id'):
                assignment = self.env['it.assignment'].browse(vals['assignment_id'])
                if assignment.state != 'draft':
                    raise ValidationError(_("Solo se pueden agregar descuentos cuando el acta está en estado Borrador."))
        return super(ITAssignmentDiscount, self).create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.assignment_id.state != 'draft':
                raise ValidationError(_("No se pueden modificar descuentos una vez confirmada el acta."))
        return super(ITAssignmentDiscount, self).write(vals)

    def unlink(self):
        for rec in self:
            if rec.assignment_id.state != 'draft':
                raise ValidationError(_("No se pueden eliminar descuentos una vez confirmada el acta."))
        return super(ITAssignmentDiscount, self).unlink()

class ITAssignmentConfirmWizard(models.TransientModel):
    _name = 'it.assignment.confirm.wizard'
    _description = 'Wizard de Confirmación de Asignación'

    assignment_id = fields.Many2one('it.assignment', string='Asignación')
    message = fields.Text(string='Mensaje', readonly=True)
    product_ids = fields.Many2many('product.template', string='Productos sin descuento', readonly=True)

    def action_confirm_anyway(self):
        self.ensure_one()
        return self.assignment_id.with_context(skip_discount_check=True).action_confirm()
