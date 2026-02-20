from odoo import models

# Se usa el registro de modelos de Odoo para obtener la clase StockPicking.
def _check_scheduled_date_done_cancel_patched(self):
    # Esta es la función parcheada que anula la validación.
    pass

# Se usa un hook de Odoo que se ejecuta después de que todos los modelos se han cargado.
def post_load():
    # Obtener la clase StockPicking del registro de modelos.
    StockPicking = models.get('stock.picking')
    if StockPicking:
        # Reemplazar el método original con la versión parcheada.
        StockPicking._check_scheduled_date_done_cancel = _check_scheduled_date_done_cancel_patched
