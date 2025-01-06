# __manifest__.py
{
    'name': 'Sales Order Car Extension',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Add car field to sale orders',
    'description': """
        This module adds car/vehicle field to sale orders.
        Features:
        - Link vehicles to sale orders
        - Track changes on vehicle field
        - Integrate with fleet management
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'sale_management',
        'fleet',
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/fleet_service_views.xml',
        'views/stock_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {},
}