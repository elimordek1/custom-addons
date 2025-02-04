{
    'name': 'Custom Invoice Template',
    'version': '1.0',
    'depends': ['base', 'sale', ],
    'data': [
        'report/sale_order_report.xml',
        'views/sale_order_form.xml',
        'views/INV_Draft_GEO.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'pdf/static/src/scss/INV_Draft_GEO.scss',
        ],
    },
}
