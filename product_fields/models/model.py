from odoo import models, fields, api

class ManufactureYear(models.Model):
    _name = 'manufacture.year'
    _description = 'Manufacture Year'

    name = fields.Char(string='Year', required=True)

class VehicleModel(models.Model):
    _name = 'vehicle.model'
    _description = 'Vehicle Model'

    name = fields.Char(string='Vehicle Model', required=True)

class ExteriorColor(models.Model):
    _name = 'exterior.color'
    _description = 'Exterior Color'

    name = fields.Char(string='Exterior Color', required=True)

class ExteriorColorEng(models.Model):
    _name = 'exterior.color.eng'
    _description = 'Exterior Color English'

    name = fields.Char(string='Exterior Color (ENG)', required=True)

class EngineVolume(models.Model):
    _name = 'engine.volume'
    _description = 'Engine Volume'

    name = fields.Char(string='Engine Volume', required=True)

class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    vehicle_model_id = fields.Many2one('vehicle.model', string='Vehicle Model')
    vin_code = fields.Char(string='VIN Code')
    manufacture_year_id = fields.Many2one('manufacture.year', string='Manufacture Year')
    exterior_color_id = fields.Many2one('exterior.color', string='Exterior Color')
    exterior_color_eng_id = fields.Many2one('exterior.color.eng', string='Exterior Color (ENG)')
    engine_volume_id = fields.Many2one('engine.volume', string='Engine Volume')