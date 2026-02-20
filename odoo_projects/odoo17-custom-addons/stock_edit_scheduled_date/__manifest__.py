{
    'name': 'Stock: Edit Scheduled Date',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Allows to edit the scheduled date on stock pickings after confirmation.',
    'author': 'Tu Nombre',
    'website': 'Tu Sitio Web',
    'depends': ['stock'],
    'data': [
        'security/stock_edit_scheduled_date_groups.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
