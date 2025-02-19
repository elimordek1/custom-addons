# models/stock_move.py
from odoo import fields, models, api, _ , tools
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = 'stock.move'
    
    # Fields
    barcode = fields.Char(related='product_id.barcode', string="Barcode", store=True, readonly=False)
    unit_price = fields.Float(string="Cost", compute='_compute_cost', store=True)
    cost_including_tax = fields.Float(string="Cost Including Tax", compute='_compute_cost_including_tax', store=True)

    # Compute Methods
    @api.depends('product_id', 'product_id.standard_price')
    def _compute_cost(self):
        for line in self:
            line.unit_price = line.product_id.standard_price if line.product_id else 0.0
    
    @api.depends('unit_price', 'product_uom_qty')
    def _compute_cost_including_tax(self):
        for line in self:
            line.cost_including_tax = line.unit_price * line.product_uom_qty if line.product_id else 0.0

# models/sale_order.py
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    # Fields
    car_id = fields.Many2one('fleet.vehicle', string='Car')
    has_service_created = fields.Boolean(string='Service Created', default=False)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)
    is_car_service = fields.Boolean(string='Car Service', default=False)  # Added new checkbox field
    connected_service_id = fields.Many2one('fleet.vehicle.log.services', string='Connected Service', 
                                         compute='_compute_connected_service')
    
    # Compute Methods
    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_total_cost(self):
        for order in self:
            order.total_cost = sum(order.order_line.mapped(lambda l: l.product_id.standard_price * l.product_uom_qty))
    
    @api.depends('name', 'has_service_created')
    def _compute_connected_service(self):
        for order in self:
            service = self.env['fleet.vehicle.log.services'].search([('order_id', '=', order.id)], limit=1)
            order.connected_service_id = service.id if service else False
    # Action Methods
    def action_create_car_service(self):
        self.ensure_one()
        if not self.car_id:
            raise UserError(_("Please select a car first!"))

        service_type = self.env['fleet.service.type'].search([('name', '=', 'Car Service')], limit=1)
        if not service_type:
            raise UserError(_("Service type 'Car Service' not found! Please create it first."))
            
        service_vals = {
            'vehicle_id': self.car_id.id,
            'amount': self.total_cost,
            'date': fields.Date.today(),
            'description': f'Service created from Sale Order {self.name}',
            'purchaser_id': self.partner_id.id,
            'vendor_id': self.company_id.partner_id.id,
            'inv_ref': self.name,
            'service_type_id': service_type.id,
            'order_id': self.id,
            'state': 'done'
        }

        service = self.env['fleet.vehicle.log.services'].create(service_vals)
        self.has_service_created = True
        if self.odometer:
           odometer = self.env['fleet.vehicle.odometer'].create({
               'vehicle_id': self.car_id.id,
               'value': self.odometer,
               'date': self.date_order,
               'name': f"Service Order: {self.name}"
           })
           self.odometer_id = odometer.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Service was successfully created.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
            }



    # Override Methods
    def write(self, vals):
        result = super().write(vals)
        if 'order_line' in vals and self.has_service_created:
            service = self.env['fleet.vehicle.log.services'].search([('order_id', '=', self.id)], limit=1)
            if service:
                service.amount = self.total_cost
        return result

    def action_confirm(self):
        for order in self:
            if order.is_car_service and not order.has_service_created:
                raise UserError(_("Please create a car service before confirming this order."))
        return super().action_confirm()


# models/fleet.py
class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'
    
    # Fields
    order_id = fields.Many2one('sale.order', string='Sale Order')
    invoice_id = fields.Many2one('account.move', string='Invoice', 
                                domain="[('move_type', 'in', ['out_invoice', 'in_invoice']), ('state', '=', 'posted')]")
    stock_picking_id = fields.Many2one(
        'stock.picking',
        string='ჩამოწერის ოპერაცია',
        domain="[('picking_type_id.name', '=', 'ჩამოწერა შიდა მოხმარებისთვის'), ('vehicle_id', '=', vehicle_id)]",
    )

    def action_create_stock_picking(self):
        picking_type = self.env['stock.picking.type'].search([
            ('name', '=', 'ჩამოწერა შიდა მოხმარებისთვის')
        ], limit=1)

        if not picking_type:
            raise UserError(_('ჩამოწერის ტიპი ვერ მოიძებნა!'))
            
        vals = {
            'picking_type_id': picking_type.id,
            'vehicle_id': self.vehicle_id.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
        }
        
        picking = self.env['stock.picking'].create(vals)
        self.stock_picking_id = picking.id
        
        return {
            'name': _('Created Stock Picking'),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    # Onchange Methods
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            return {
                'domain': {
                    'stock_picking_id': [
                        ('picking_type_id.name', '=', 'ჩამოწერა შიდა მოხმარებისთვის'),
                        ('vehicle_id', '=', self.vehicle_id.id),
                    ]
                },
                'context': {'default_vehicle_id': self.vehicle_id.id}
            }

    @api.onchange('stock_picking_id')
    def _onchange_stock_picking_id(self):
        if self.stock_picking_id:
            self.vehicle_id = self.stock_picking_id.vehicle_id.id
            self.amount = sum(self.stock_picking_id.move_ids.mapped(
                lambda m: m.product_id.standard_price * m.quantity_done
            ))

    @api.onchange('order_id')
    def _onchange_order_id(self):
        if self.order_id:
            if self.vehicle_id:
                self.order_id.car_id = self.vehicle_id.id
            self.amount = self.order_id.total_cost

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id:
            total_cost = sum(self.invoice_id.invoice_line_ids.mapped(
                lambda l: l.product_id.standard_price * l.quantity
            ))
            self.amount = total_cost
            
            if self.invoice_id.invoice_origin:
                sale_order = self.env['sale.order'].search([
                    ('name', '=', self.invoice_id.invoice_origin)
                ], limit=1)
                if sale_order:
                    self.order_id = sale_order.id
                    if sale_order.car_id:
                        self.vehicle_id = sale_order.car_id.id


# models/account_move.py
class AccountMove(models.Model):
    _inherit = 'account.move'

    # Fields
    connected_service_id = fields.Many2one(
        'fleet.vehicle.log.services', 
        string='Connected Service',
        compute='_compute_connected_service'
    )
    trigger_update = fields.Datetime(string='Trigger Update')

    # Compute Methods
    @api.depends('invoice_origin')
    def _compute_connected_service(self):
        for move in self:
            service = False
            if move.invoice_origin:
                sale_order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
                if sale_order:
                    service = self.env['fleet.vehicle.log.services'].search([
                        ('order_id', '=', sale_order.id)
                    ], limit=1)
            move.connected_service_id = service.id if service else False

    # Override Methods
    def write(self, vals):
        result = super().write(vals)
        if any(f not in ['trigger_update', 'write_date'] for f in vals):
            for move in self:
                if move.move_type in ['out_invoice', 'in_invoice'] and move.invoice_line_ids and move.invoice_origin:
                    sale_order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
                    if sale_order and sale_order.has_service_created:
                        service = self.env['fleet.vehicle.log.services'].search([
                            ('order_id', '=', sale_order.id)
                        ], limit=1)
                        if service:
                            total_cost = sum(move.invoice_line_ids.mapped('price_total'))
                            service.amount = total_cost
        return result


    def action_post(self):
        # Call the original post method
        res = super().action_post()
        
        # For each posted invoice
        for move in self:
            # Only process confirmed invoices with an origin
            if move.state == 'posted' and move.invoice_origin:
                # Find related sale order
                sale_order = self.env['sale.order'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)
                
                # If sale order exists and has service created
                if sale_order and sale_order.has_service_created:
                    # Find and update related service
                    service = self.env['fleet.vehicle.log.services'].search([
                        ('order_id', '=', sale_order.id)
                    ], limit=1)
                    if service:
                        service.state = 'done'
        
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def write(self, vals):
        result = super().write(vals)
        if any(field in vals for field in ['product_id', 'quantity', 'price_unit']) and not self.env.context.get('skip_trigger_update'):
            moves_to_update = self.mapped('move_id')
            for move in moves_to_update:
                move.with_context(skip_trigger_update=True).write({
                    'trigger_update': fields.Datetime.now()
                })
        return result



# models/stock_picking.py
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # Fields
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    connected_service_id = fields.Many2one(
        'fleet.vehicle.log.services', 
        string='Connected Service',
        compute='_compute_connected_service'
    )

    # Compute Methods
    @api.depends('sale_id')
    def _compute_connected_service(self):
        for picking in self:
            service = self.env['fleet.vehicle.log.services'].search([
                ('stock_picking_id', '=', picking.id)
            ], limit=1)
            if not service and picking.sale_id:
                service = self.env['fleet.vehicle.log.services'].search([
                    ('order_id', '=', picking.sale_id.id)
                ], limit=1)
            picking.connected_service_id = service.id if service else False

    def _calculate_total_cost(self):
        self.ensure_one()
        return sum(
            move.product_id.standard_price * move.product_uom_qty
            for move in self.move_ids_without_package
        )

    # Override Methods
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_vehicle_id'):
            res['vehicle_id'] = self.env.context['default_vehicle_id']
        return res

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ['move_ids_without_package', 'move_ids', 'move_lines']):
            for picking in self:
                if picking.connected_service_id:
                    picking.connected_service_id.amount = picking._calculate_total_cost()
        return res

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if picking.connected_service_id:
                picking.connected_service_id.amount = picking._calculate_total_cost()
        return res


# models/product.py
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    total_stock_value = fields.Float(
        string='Total Sales Price',
        compute='_compute_total_stock_value',
        store=False,
    )
    
    @api.depends('qty_available', 'list_price')
    def _compute_total_stock_value(self):
        for product in self:
            product.total_stock_value = product.qty_available * product.lst_price




class SaleReport(models.Model):
    _inherit = 'sale.report'

    difference_amount = fields.Float(
        string='დღგ',
        readonly=True
    )


    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['difference_amount'] = f"""
            CASE WHEN l.product_id IS NOT NULL THEN SUM(
                (l.price_total - l.price_subtotal)
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('account_currency_table.rate')}
            ) ELSE 0 END"""
        return res




class SaleOrderExtended(models.Model):
    _inherit = 'sale.order'

    odometer = fields.Float(string='Odometer')
    odometer_id = fields.Many2one('fleet.vehicle.odometer', string='Odometer Record', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('state', 'draft') == 'draft':
            sequence = self.env['ir.sequence'].next_by_code('sale.order')
            sequence = sequence-1
            if sequence and sequence.startswith('S'):
                vals['name'] = 'Q' + sequence[1:]  # All quotations start with Q
        return super(SaleOrder, self).create(vals)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.name.startswith('Q'):
                if order.is_car_service:
                    order.name = 'S' + order.name[1:]  # Car service orders get S
                else:
                    order.name = 'P' + order.name[1:]  # Regular orders get P
        return res
