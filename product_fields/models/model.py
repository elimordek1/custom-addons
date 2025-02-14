# models/vehicle_info.py
from odoo import models, fields, api

class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    vehicle_model_ids = fields.One2many('vehicle.model.line', 'product_id', string='Vehicle Models')
    vin_code = fields.Char(string='VIN Code')
    manufacture_date = fields.Date(string='Manufacture Date')
    exterior_color_ids = fields.One2many('exterior.color.line', 'product_id', string='Exterior Colors')
    exterior_color_eng_ids = fields.One2many('exterior.color.eng.line', 'product_id', string='Exterior Colors (ENG)')
    engine_volume_ids = fields.One2many('engine.volume.line', 'product_id', string='Engine Volumes')

class VehicleModelLine(models.Model):
    _name = 'vehicle.model.line'
    _description = 'Vehicle Model Lines'

    product_id = fields.Many2one('product.template', string='Product')
    name = fields.Char(string='Vehicle Model')

class ExteriorColorLine(models.Model):
    _name = 'exterior.color.line'
    _description = 'Exterior Color Lines'

    product_id = fields.Many2one('product.template', string='Product')
    name = fields.Char(string='Exterior Color')

class ExteriorColorEngLine(models.Model):
    _name = 'exterior.color.eng.line'
    _description = 'Exterior Color English Lines'

    product_id = fields.Many2one('product.template', string='Product')
    name = fields.Char(string='Exterior Color (ENG)')

class EngineVolumeLine(models.Model):
    _name = 'engine.volume.line'
    _description = 'Engine Volume Lines'

    product_id = fields.Many2one('product.template', string='Product')
    volume = fields.Float(string='Engine Volume')