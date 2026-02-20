import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class Assets(models.Model):

    _name = "it.assets"
    _description = "IT Assets"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    item_code = fields.Char(string = "Asset Code")
    name = fields.Char(string = "Asset Name")
    item_user = fields.Many2one('res.users', string = "Asset User")
    all_components = fields.Many2many(
        'it.components',
        'component_asset_rel',   
        'asset_id',              
        'component_id',          
        string="All Components"
    )
    asset_repaired = fields.Boolean(string = 'Asset Repairing') 
    asset_type = fields.Many2one("asset.type", string = "Asset Type")
    system_id = fields.Many2one('system.system', string="System")
    image = fields.Binary()

    @api.model
    def create(self, vals):

        if vals.get('system_id'):
            system = self.env['system.system'].browse(vals['system_id'])
            if system.user:
                vals['item_user'] = system.user.id 
        
        asset = super(Assets, self).create(vals)

        user = asset.item_user
        components = asset.all_components

        for component in components:
            if component.available_quantity <= 0:
                raise ValidationError(
                    f"Component '{component.name}' has no available quantity to assign."
                )
            if user:
                if user.id not in component.user.ids:
                    component.user =  [(4, user.id)] 
            component.available_quantity -= 1 

        return asset
    
    def write(self, vals):
        if 'all_components' in vals:
            for record in self:
                new_user_id = vals.get('item_user') or (record.item_user.id if record.item_user else None)
                old_user_id = record.item_user.id if record.item_user else None

                old_components = record.all_components
                res = super(Assets, self).write(vals)  
                new_components = record.all_components

                added_components = new_components - old_components
                removed_components = old_components - new_components

                for component in added_components:
                    if component.available_quantity <= 0:
                        raise ValidationError(
                            f"Component '{component.name}' has no available quantity to assign."
                    )
                    if new_user_id not in component.user.ids:
                        component.user = [(4, new_user_id)]
                    component.available_quantity -= 1

                for component in removed_components:
                    if old_user_id and old_user_id in component.user.ids:
                        still_used = self.search_count([
                            ('all_components', 'in', component.id),
                            ('item_user', '=', old_user_id),
                            ('id', '!=', record.id)
                        ])
                        if not still_used:
                            component.user = [(3, old_user_id)]
                        component.available_quantity += 1 
            return res
        
        elif 'item_user' in vals:
            new_user_id = vals.get('item_user')
            for record in self:
               old_user_id = record.item_user.id if record.item_user else None
               components = record.all_components
               for component in components:
                    if old_user_id and old_user_id in component.user.ids:
                        component.user = [(3, old_user_id)]
                    if new_user_id not in component.user.ids and new_user_id:
                        component.user = [(4, new_user_id)]
                   
            result = super(Assets, self).write(vals)
            return result
        else:
            return super(Assets, self).write(vals)
    
    def unlink(self):
        for asset in self:
            user_id = asset.item_user.id
            for component in asset.all_components:
                component.available_quantity += 1 
                if user_id and user_id in component.user.ids:
                    still_used = self.search_count([
                        ('all_components', 'in', component.id),
                        ('item_user', '=', user_id),
                        ('id', '!=', asset.id)
                    ])
                    if not still_used:
                        component.user = [(3, user_id)]

        return super(Assets, self).unlink()
    
    def getAssetAndComponentCount(self):
        total_assets = self.env['it.assets'].search_count([])
        total_components = self.env['it.components'].search_count([])
        total_system = self.env['system.system'].search_count([])
        repairing_components = self.env['it.components'].search_count([('is_repair', '=', True)])
      
        return {
            'total_assets': total_assets,
            'total_system': total_system,
            'total_components': total_components,
            'repairing_components': repairing_components,
        }

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_in_it_inventory = fields.Boolean(
        string='Available in IT Inventory',
        help='Check if you want this product to appear in the IT Asset Management module.',
        default=False
    )
    it_unique_assignment = fields.Boolean(
        string='Unique Assignment (Serial)',
        help='If checked, this product can only be assigned to one employee at a time and will be hidden from assignment lists if already assigned.',
        default=False
    )
    it_serial_number = fields.Char(string='IT Serial Number')
    it_brand_id = fields.Many2one('asset.brand', string='IT Brand')
    it_asset_type_id = fields.Many2one('asset.type', string='Asset Type')

    it_current_assignment_id = fields.Many2one(
        'it.assignment', 
        string='Current Allocation',
        store=True
    )
    it_current_employee_id = fields.Many2one(
        'hr.employee', 
        string='Assigned Employee',
        store=True
    )
    it_assignment_date = fields.Date(
        string='Date Assigned',
        store=True
    )

    it_assignment_history_ids = fields.One2many(
        'it.assignment.line',
        'product_id',
        string='History of Assignments'
    )

    it_active_assignments = fields.Many2many(
        'it.assignment',
        string='Active Assignments',
        compute='_compute_it_active_assignments'
    )

    def _compute_it_active_assignments(self):
        for product in self:
            assignments = self.env['it.assignment'].search([
                ('line_ids.product_id', '=', product.id),
                ('state', '=', 'confirmed')
            ])
            product.it_active_assignments = assignments

    def write(self, vals):
        # Check if trying to disable available_in_it_inventory
        if 'available_in_it_inventory' in vals and not vals['available_in_it_inventory']:
            for product in self:
                if product.available_in_it_inventory:
                    # Check for active assignments
                    assignment_count = self.env['it.assignment'].search_count([
                        ('line_ids.product_id', '=', product.id),
                        ('state', '=', 'confirmed')
                    ])
                    if assignment_count > 0:
                        raise ValidationError(_(
                            "No se puede desactivar 'Disponible en Inventario TI' para el producto '%s' "
                            "porque tiene %s asignación(es) activa(s). "
                            "Por favor, devuelva o cancele todas las asignaciones antes de desactivar esta opción."
                        ) % (product.name, assignment_count))

        # 1. Standard write
        res = super(ProductTemplate, self).write(vals)

        # 2. If turning ON unique assignment, sync the assignment data
        if vals.get('it_unique_assignment'):
            for product in self:
                # Find the ONE active assignment (constraint ensures max 1)
                assignment = self.env['it.assignment'].search([
                    ('line_ids.product_id', '=', product.id),
                    ('state', '=', 'confirmed')
                ], limit=1)
                
                if assignment:
                    product.write({
                        'it_current_assignment_id': assignment.id,
                        'it_current_employee_id': assignment.employee_id.id,
                        'it_assignment_date': assignment.assignment_date
                    })
        return res

    @api.constrains('it_unique_assignment')
    def _check_unique_assignment_constraint(self):
        _logger.info("Checking unique assignment constraint for product IDs: %s", self.ids)
        for product in self:
            if product.it_unique_assignment:
                assignment_count = self.env['it.assignment'].search_count([
                    ('line_ids.product_id', '=', product.id),
                    ('state', '=', 'confirmed')
                ])
                _logger.info("Product %s has %s confirmed assignments", product.name, assignment_count)
                if assignment_count > 1:
                    raise ValidationError(_(
                        "Cannot enable 'Unique Assignment' because this product is currently assigned to multiple employees. "
                        "Please ensure it is assigned to 0 or 1 employee only before enabling this restriction."
                    ))

    @api.constrains('it_unique_assignment', 'it_serial_number')
    def _check_serial_number_required(self):
        """Validate that serial number is required when unique assignment is enabled."""
        for product in self:
            if product.it_unique_assignment and not product.it_serial_number:
                raise ValidationError(_(
                    "El campo 'Número de Serie TI' es obligatorio cuando se activa 'Asignación Única (Serie)'. "
                    "Por favor, ingrese un número de serie antes de activar esta opción."
                ))

    @api.constrains('available_in_it_inventory', 'it_asset_type_id')
    def _check_asset_type_required(self):
        """Validate that asset type is required when available in IT inventory is enabled."""
        for product in self:
            if product.available_in_it_inventory and not product.it_asset_type_id:
                raise ValidationError(_(
                    "El campo 'Tipo de Activo' es obligatorio cuando se activa 'Disponible en Inventario TI'. "
                    "Por favor, seleccione un tipo de activo antes de activar esta opción."
                ))

    def unlink(self):
        """Prevent deletion of products with active IT assignments."""
        for product in self:
            if product.available_in_it_inventory:
                assignment_count = self.env['it.assignment'].search_count([
                    ('line_ids.product_id', '=', product.id),
                    ('state', '=', 'confirmed')
                ])
                if assignment_count > 0:
                    raise ValidationError(_(
                        "No se puede eliminar el producto '%s' porque tiene %s asignación(es) activa(s). "
                        "Por favor, devuelva o cancele todas las asignaciones antes de eliminar este producto."
                    ) % (product.name, assignment_count))
        return super(ProductTemplate, self).unlink()

    def action_open_product(self):
        """Open the product form from the product list in IT Assignment."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product'),
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
