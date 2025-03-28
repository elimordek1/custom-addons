{
    "name":"Sales Payments",
    "version":"1.0",
    "website": "odoo18",
    "author":"xote",
    "description": """
     Sales Payments 
     """,
    "category":"",
    "depends":['sale'],
    "data":[
        'security/ir.model.access.csv',
        'views/sales_payments_view.xml'
    ],
     "demo":[
    ],

    "installable":True,
    "application":True,
    "licens":"LGPL-3",
}
