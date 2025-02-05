from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    name_english = fields.Char(string="Product Name (English)")
