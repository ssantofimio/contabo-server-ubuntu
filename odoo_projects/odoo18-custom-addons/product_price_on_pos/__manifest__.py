# -*- coding: utf-8 -*-
{
    'name': "Sales Price on POS Product Screen",

    'summary': "This Addon show product price on POS Product Screen",

    'description': """
            This Addon show product price on POS Product Screen 
    """,

    'author': "HSxTECH",
    'website': "https://www.hsxtech.net",
    'category': 'pos',
    'version': '18.0.1.0',
    'depends': ['point_of_sale'],
    'data': [],
    'license': 'LGPL-3',
    'images': [
    'static/description/banner.gif',
    'static/description/icon.png'
    ],
    'application': True,
    'maintainer': "Syed Hamza",
    'assets': {
        'point_of_sale._assets_pos': [
            'product_price_on_pos/static/src/**/*',
        ],
    },
}
