# -*- coding: utf-8 -*-
{
    'name': 'POS Product Schedule',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Control de disponibilidad de productos por día de la semana en POS',
    'description': """
        POS Product Schedule
        ====================
        Este módulo permite configurar los días de la semana en que cada producto
        estará disponible en el Punto de Venta (POS).
    """,
    'author': 'Tu Empresa',
    'depends': ['point_of_sale', 'product', 'pos_self_order'],
    'data': [
        'security/ir.model.access.csv',
        'data/pos_product_schedule_data.xml',
        'views/pos_product_schedule_views.xml',
        'views/product_template_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_schedule/static/src/app/store/models.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
