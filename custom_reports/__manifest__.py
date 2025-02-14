{
   'name': 'Custom Reports',
   'version': '1.0',
   'category': 'Sales',
   'author': 'Your Name', 
   'website': 'http://www.yourcompany.com',
   'depends': ['base', 'sale', 'stock', 'purchase', 'web','account',],
   'data': [
       'reports/sale_order_report.xml',
       'reports/report_actions.xml',       
   ],
   'assets': {
       'web.assets_backend': [
           'custom_reports/static/src/img/logoT.jpg',
       ],
   },
   'installable': True,
   'auto_install': False,
}