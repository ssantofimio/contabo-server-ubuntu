# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PickingChangeStateWizard(models.TransientModel):
    _name = 'picking.change.state.wizard'
    _description = 'Wizard to change picking state'

    # Campo para la nueva fecha programada
    scheduled_date = fields.Datetime(
        string='Fecha operación:',
        required=True
    )

    def action_change_state_and_date(self):
        """
        Changes the picking state and date after validating the new date.
        """
        # Get the active picking from the context
        picking_id = self.env.context.get('active_id')
        picking = self.env['stock.picking'].browse(picking_id)
        
        # Get the done_done date (or write_date if done_done is not available)
        done_date = picking.date_done if picking.date_done else picking.write_date

        if picking:
            # Step 1: Validate the new scheduled_date
            if self.scheduled_date > done_date:
                raise ValidationError(
                    "No puedes programar una fecha posterior a la fecha de finalización del Picking. "
                    "La fecha de finalización es: %s" % fields.Datetime.to_string(done_date)
                )

            # Step 2: Change state to 'assigned' (Ready)
            picking.state = 'assigned'
            
            # Step 3: Update the scheduled date with the wizard's value
            picking.scheduled_date = self.scheduled_date
            
            # Step 4: Change state back to 'done'
            picking.state = 'done'
        
        return {'type': 'ir.actions.act_window_close'}
