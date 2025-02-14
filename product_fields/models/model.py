from odoo import models, fields

class ProductExtraData(models.Model):
    _name = 'product.extra.data'  # Changed * to _
    _description = 'Дополнительные данные для продукта'  # Changed * to _

    model_name = fields.Char('ავტომობილის მოდელი')
    engine_capacity = fields.Char('ძრავის მოცულობა')
    exterior_color = fields.Char('ექსტერიერის ფერი')
    exterior_color_eng = fields.Char('ექსტერიერის ფერი ENG')
    year_of_manufacture = fields.Date('გამოშვების წელი')
    product_id = fields.Many2one('product.template', string='Product', required=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'  # Changed * to _

    car_model_ids = fields.One2many(  # Removed * from car*model_ids
        'product.extra.data', 'product_id', string='ავტომობილის მოდელი'
    )
    engine_capacity_ids = fields.One2many(
        'product.extra.data', 'product_id', string='ძრავის მოცულობა'
    )
    exterior_color_ids = fields.One2many(
        'product.extra.data', 'product_id', string='ექსტერიერის ფერი'
    )
    exterior_color_eng_ids = fields.One2many(
        'product.extra.data', 'product_id', string='ექსტერიერის ფერი ENG'
    )
    manufacture_year_ids = fields.One2many(
        'product.extra.data', 'product_id', string='გამოშვების წელი'
    )
    vin_code = fields.Text('ვინ კოდი')