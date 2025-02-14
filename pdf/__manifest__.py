{
    'name': 'Custom Invoice Template',
    'version': '1.0',
    'depends': ['base', 'sale','web' ],
    'data': [
        'views/INV_Draft_GEO.xml',
        'views/Pro-forma-Invoice.xml',
        'views/Proforma-invoice.xml',
        'views/Proforma-invoice-eng.xml',
        'views/nenew.xml',
        'report/sale_order_report.xml'

    ],
    'assets': {
        'web.assets_frontend': [
            'pdf/static/src/scss/INV_Draft_GEO.scss',
            'pdf/static/src/scss/Pro-forma-Invoice.scss'
        ],
    },
}
