{
    'name': 'Sandor POS Autopedido SES',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Identificar o crear cliente por CC/NIT en Autopedido POS',
    'description': """
        Este módulo amplía el estándar pos_self_order para permitir que los clientes se identifiquen 
        mediante CC/NIT o creen un nuevo perfil antes de confirmar el pedido.
    """,
    'author': 'Sarupetrol SAS',
    'depends': ['pos_self_order', 'point_of_sale'],
    'data': [
        'views/pos_config_view.xml',
    ],
    'assets': {
        'pos_self_order.assets': [
            'sandor_pos_self_order_ses/static/src/app/pages/customer_info_page/customer_info.css',
            'sandor_pos_self_order_ses/static/src/app/pages/customer_info_page/customer_info_page.js',
            'sandor_pos_self_order_ses/static/src/app/pages/customer_info_page/customer_info_page.xml',
            'sandor_pos_self_order_ses/static/src/app/pages/landing_page/landing_page_patch.js',
            'sandor_pos_self_order_ses/static/src/app/pages/landing_page/landing_page_patch.xml',
            'sandor_pos_self_order_ses/static/src/app/pages/confirmation_page/confirmation_page_patch.js',
            'sandor_pos_self_order_ses/static/src/app/pages/confirmation_page/confirmation_page_patch.xml',
            'sandor_pos_self_order_ses/static/src/app/pages/product_list_page/product_list_page_patch.js',
            'sandor_pos_self_order_ses/static/src/app/pages/product_list_page/product_list_page_patch.xml',
            'sandor_pos_self_order_ses/static/src/app/pages/cart_page/cart_page_patch.js',
            'sandor_pos_self_order_ses/static/src/app/pages/cart_page/cart_page_patch.xml',
            'sandor_pos_self_order_ses/static/src/app/models/order_patch.js',
            'sandor_pos_self_order_ses/static/src/app/self_order_service_patch.js',
            'sandor_pos_self_order_ses/static/src/app/self_order_index_patch.js',
            'sandor_pos_self_order_ses/static/src/app/pages/combo_page/combo_page_patch.js',
            'sandor_pos_self_order_ses/static/src/app/components/order_widget/order_widget_patch.js',
            'sandor_pos_self_order_ses/static/src/app/components/order_widget/order_widget.css',
            'sandor_pos_self_order_ses/static/src/app/self_order_index.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
