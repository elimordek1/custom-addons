from odoo import models, fields, api


class SalesPaymentsCustomXO(models.Model):
    _name = 'sales.payments.custom.xo'
    _description = 'Sales Payments Custom XO'

    name = fields.Char(string="Payment Reference", required=True)
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", related='sale_order_id.partner_id', store=True)

    accountpaymentid = fields.Many2one(
        'account.payment',
        string="Payment",
        required=True,
        domain="[('partner_id', '=', partner_id), ('state', '!=', 'draft'), ('id', 'not in', used_payment_ids)]"
    )

    payment_date = fields.Date(string="Payment Date", related='accountpaymentid.date', store=True)
    memo = fields.Char(string="Memo", related='accountpaymentid.memo', store=True)
    amount_signed = fields.Monetary(string="Amount Signed", related='accountpaymentid.amount_signed', store=True)

    company_currency_id = fields.Many2one(
        'res.currency',
        string="Company Currency",
        related='sale_order_id.company_id.currency_id',
        store=True
    )

    amount_company_currency_signed = fields.Monetary(
        string="Amount in GEL",
        compute='_compute_amount_company_currency_signed',
        currency_field='company_currency_id',
        store=True
    )

    currency_id = fields.Many2one('res.currency', related='accountpaymentid.currency_id', store=True)

    amount = fields.Monetary(
        string="Payment Amount",
        related='accountpaymentid.amount',
        currency_field='currency_id',
        store=True
    )

    used_payment_ids = fields.Many2many(
        'account.payment',
        string="Used Payments",
        compute='_compute_used_payments',
        store=False
    )

    total_amount_signed = fields.Float(
        string="Total Amount Signed",
        compute="_compute_totals",
        store=True
    )

    total_amount_company_currency_signed = fields.Monetary(
        string="Amount in GEL",
        compute="_compute_totals",
        currency_field='company_currency_id',
        store=True
    )

    total_amount = fields.Monetary(
        string="Total Payment Amount",
        compute="_compute_totals",
        currency_field='currency_id',
        store=True
    )

    @api.depends('sale_order_id')
    def _compute_used_payments(self):
        """Fetch IDs of already used payments in sales.payments.custom.xo"""
        for record in self:
            used_payments = self.search([('sale_order_id.partner_id', '=', record.partner_id.id)]).mapped('accountpaymentid.id')
            record.used_payment_ids = [(6, 0, used_payments)]

    @api.depends('accountpaymentid.amount_signed', 'accountpaymentid.amount_company_currency_signed', 'accountpaymentid.amount')
    def _compute_totals(self):
        """Compute the sum of amounts for all payments related to the same Sale Order"""
        for record in self:
            payments = self.search([('sale_order_id', '=', record.sale_order_id.id)])

            # Sum the amounts and assign to the totals
            record.total_amount_signed = sum(payment.amount_signed or 0.0 for payment in payments)
            record.total_amount_company_currency_signed = sum(payment.amount_company_currency_signed or 0.0 for payment in payments)
            record.total_amount = sum(payment.amount or 0.0 for payment in payments)

    @api.depends('amount_signed', 'currency_id', 'company_currency_id')
    def _compute_amount_company_currency_signed(self):
        """Convert amount_signed to company currency"""
        for record in self:
            if record.currency_id and record.company_currency_id:
                record.amount_company_currency_signed = record.currency_id._convert(
                    record.amount_signed, record.company_currency_id, record.sale_order_id.company_id,
                    fields.Date.today()
                )
            else:
                record.amount_company_currency_signed = record.amount_signed


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payments_cus_ids = fields.One2many('sales.payments.custom.xo', 'sale_order_id', string="Sales Payments")

    company_currency_id = fields.Many2one(
        'res.currency',
        string="Company Currency",
        related='company_id.currency_id',
        store=True
    )

    total_amount_signed = fields.Float(
        string="Total Amount Signed",
        compute="_compute_totals",
        store=True
    )

    total_amount_company_currency_signed = fields.Monetary(
        string="Amount in GEL",
        compute="_compute_totals",
        currency_field='company_currency_id',
        store=True
    )

    total_amount = fields.Monetary(
        string="Total Amount",
        compute="_compute_totals",
        currency_field='currency_id',
        store=True
    )

    @api.depends('payments_cus_ids')
    def _compute_totals(self):
        for order in self:
            # Sum the totals of related payments
            total_signed = sum(payment.amount_signed or 0.0 for payment in order.payments_cus_ids)
            total_signed_company_currency = sum(payment.amount_company_currency_signed or 0.0 for payment in order.payments_cus_ids)
            total = sum(payment.amount or 0.0 for payment in order.payments_cus_ids)

            # Assign computed values
            order.total_amount_signed = total_signed
            order.total_amount_company_currency_signed = total_signed_company_currency
            order.total_amount = total
