{
    'name': 'Stock Change Scheduled Date',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Permite cambiar la fecha programada incluso en movimientos realizados o cancelados',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/change_scheduled_date_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
}
