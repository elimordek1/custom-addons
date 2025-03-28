from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payments_cus_ids = fields.One2many('sales.payments.custom.xo', 'sale_order_id', string="Sales Payments")
    total_amount_signed = fields.Float(string="Total Amount Signed", related='payments_cus_ids.total_amount_signed', store=True)

    def _compute_sales_line_sum(self):
        """Compute the sum of sales lines for this sale order"""
        for order in self:
            order.sales_line_sum = sum(line.price_total for line in order.order_line)

    sales_line_sum = fields.Monetary(string="Sales Line Total", compute="_compute_sales_line_sum")


class SalesPaymentsCustomXO(models.Model):
    _name = 'sales.payments.custom.xo'
    _description = 'Sales Payments Custom XO'

    name = fields.Char(string="Payment Reference", required=True)
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", required=True)
    total_amount_signed = fields.Float(
        string="Total Amount Signed",
        compute="_compute_totals",
        currency_field='currency_id',
        store=True
    )

    @api.depends('sale_order_id')
    def _compute_totals(self):
        """Compute the sum of amounts for all payments related to the same Sale Order"""
        for record in self:
            if record.sale_order_id.currency_id != record.sale_order_id.partner_id.property_product_pricelist.currency_id:
                payments = self.search([('sale_order_id', '=', record.sale_order_id.id)])
                record.total_amount_signed = sum(payment.amount_signed for payment in payments)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create_vendor_bill_from_sale(self, sale_order):
        """Create a vendor bill for a foreign sale order with calculated amounts"""
        if sale_order.currency_id != sale_order.partner_id.property_product_pricelist.currency_id:
            # If it's a foreign sale, proceed to calculate the total amount
            total_sales_amount = sum(line.price_total for line in sale_order.order_line)
            total_amount_signed = sale_order.total_amount_signed

            # Calculate the difference between sales line sum and total_amount_signed
            adjusted_amount = total_sales_amount - total_amount_signed

            # Get the current exchange rate from the sale order's currency to the company currency
            exchange_rate = sale_order.currency_id._get_rate(sale_order.company_id.currency_id)

            # Multiply the adjusted amount by the exchange rate to convert to the company currency
            converted_amount = adjusted_amount * exchange_rate

            # Get the amount to add to the vendor bill (considering company currency)
            total_amount_company_currency_signed = converted_amount + sale_order.total_amount_signed

            # Create vendor bill lines (you may modify this part based on how you want the bill lines to look)
            bill_lines = []
            for line in sale_order.order_line:
                bill_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'name': line.name,
                    'account_id': line.product_id.categ_id.property_account_income_categ.id,
                    'price_subtotal': line.price_subtotal,
                    'move_id': move.id
                }))

            # Create the vendor bill with the total amount in the company currency
            bill = self.create({
                'move_type': 'in_invoice',
                'partner_id': sale_order.partner_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': bill_lines,
                'amount_total': total_amount_company_currency_signed,  # Set the total amount in company currency
            })

            return bill
