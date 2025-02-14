# __manifest__.py
{
    'name': 'Product Fields',
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
        'base','product',
    ],
    'data': [
        'views/product_view.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}