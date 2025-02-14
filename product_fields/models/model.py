from odoo import models, fields

class ProductCarModel(models.Model):
    _name = 'product.car.model'
    _description = 'Car Model'

    model_name = fields.Char('ავტომობილის მოდელი')
    product_id = fields.Many2one('product.template', string='Product', required=True)

class ProductEngineCapacity(models.Model):
    _name = 'product.engine.capacity'
    _description = 'Engine Capacity'

    engine_capacity = fields.Char('ძრავის მოცულობა')
    product_id = fields.Many2one('product.template', string='Product', required=True)

class ProductExteriorColor(models.Model):
    _name = 'product.exterior.color'
    _description = 'Exterior Color'

    exterior_color = fields.Char('ექსტერიერის ფერი')
    product_id = fields.Many2one('product.template', string='Product', required=True)

class ProductExteriorColorEng(models.Model):
    _name = 'product.exterior.color.eng'
    _description = 'Exterior Color English'

    exterior_color_eng = fields.Char('ექსტერიერის ფერი ENG')
    product_id = fields.Many2one('product.template', string='Product', required=True)

class ProductManufactureYear(models.Model):
    _name = 'product.manufacture.year'
    _description = 'Manufacture Year'

    year_of_manufacture = fields.Date('გამოშვების წელი')
    product_id = fields.Many2one('product.template', string='Product', required=True)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    car_model_ids = fields.One2many(
        'product.car.model', 'product_id', string='ავტომობილის მოდელი'
    )
    engine_capacity_ids = fields.One2many(
        'product.engine.capacity', 'product_id', string='ძრავის მოცულობა'
    )
    exterior_color_ids = fields.One2many(
        'product.exterior.color', 'product_id', string='ექსტერიერის ფერი'
    )
    exterior_color_eng_ids = fields.One2many(
        'product.exterior.color.eng', 'product_id', string='ექსტერიერის ფერი ENG'
    )
    manufacture_year_ids = fields.One2many(
        'product.manufacture.year', 'product_id', string='გამოშვების წელი'
    )
    vin_code = fields.Text('ვინ კოდი')