# -*- coding: utf-8 -*-
{
    'name': 'POS Mostrar Precio en Tarjeta',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Agrega etiqueta de precio en la tarjeta del producto del POS',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale.assets': [
            'pos_show_price_on_card/static/src/xml/product_card_extension.xml',
            'pos_show_price_on_card/static/src/js/force_price.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}