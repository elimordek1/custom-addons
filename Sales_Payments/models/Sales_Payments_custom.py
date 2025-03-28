from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

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

    amount_currency = fields.Float(string="Amount in Currency", compute='_compute_amount_currency', store=True)

    amount_company_currency_signed = fields.Float(
        string="Amount in GEL",
        compute='_compute_amount_company_currency_signed',
        store=True
    )

    company_currency_id = fields.Many2one(
        'res.currency',
        string="Company Currency",
        related='sale_order_id.company_id.currency_id',
        currency_field='currency_id',
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


    @api.depends('sale_order_id')
    def _compute_used_payments(self):
        """Fetch IDs of already used payments in sales.payments.custom.xo"""
        for record in self:
            used_payments = self.search([('sale_order_id.partner_id', '=', record.partner_id.id)]).mapped('accountpaymentid.id')
            record.used_payment_ids = [(6, 0, used_payments)]


    @api.depends('accountpaymentid')
    def _compute_amount_company_currency_signed(self):
        for record in self:
            # Assuming 'accountpaymentid' is the field linking to the 'account.payment' model
            record.amount_company_currency_signed = record.accountpaymentid.amount_company_currency_signed


    @api.depends('accountpaymentid', 'sale_order_id')
    def _compute_amount_currency(self):
        """Compute amount_currency by converting the payment amount into the sales order currency"""
        for record in self:
            # Get the amount in payment's currency
            amount = record.amount or 0.0

            # If the payment currency is different from the sales order's currency, convert it
            if record.currency_id != record.sale_order_id.currency_id:
                rate_date = record.payment_date or fields.Date.today()
                converted_amount = record.currency_id._convert(
                    amount,
                    record.sale_order_id.currency_id,
                    record.sale_order_id.company_id,
                    rate_date
                )
            else:
                # If the currencies are the same, no conversion needed
                converted_amount = amount

            record.amount_currency = converted_amount


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payments_cus_ids = fields.One2many('sales.payments.custom.xo', 'sale_order_id', string="Sales Payments")

    company_currency_id = fields.Many2one(
        'res.currency',
        string="Company Currency",
        related='company_id.currency_id',
        store=True
    )

    total_amount_company_currency_signed = fields.Monetary(
        string="Amount in GEL",
        compute="_compute_totals",
        currency_field='company_currency_id',
        store=True
    )

    total_amount_currency = fields.Monetary(
        string="Amount in Payment Currency",
        compute="_compute_totals_amount_currency",
        store=True
    )


    @api.depends('payments_cus_ids')
    def _compute_totals(self):
        for order in self:
            # Sum the totals of related payments
            total_signed_company_currency = sum(
                payment.amount_company_currency_signed or 0.0 for payment in order.payments_cus_ids)
            order.total_amount_company_currency_signed = total_signed_company_currency



    @api.depends('payments_cus_ids')
    def _compute_totals_amount_currency(self):
        for order in self:
            # Sum the totals of related payments in the payment currency
            total_amount_currency = sum(
                payment.amount_currency or 0.0 for payment in order.payments_cus_ids)
            order.total_amount_currency = total_amount_currency



class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def recalculate_advances(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            raise UserError("This function only applies to customer invoices.")
        
        sale_order = self.env['sale.order'].search([
            ('invoice_ids', 'in', self.ids)
        ], limit=1)
        
        if not sale_order:
            raise UserError("No related sale order found for this invoice.")
        
        if self.state != 'draft':
            raise UserError("You can only modify draft invoices.")
        
        # Get currency information
        company_currency = sale_order.company_id.currency_id  # GEL
        so_currency = sale_order.currency_id  # USD (Pricelist currency)
        
        # Get payments from the sale order
        payments = sale_order.payments_cus_ids
        
        if not payments:
            raise UserError("No payments found for this sale order.")
        
        # Get total sale order amount in SO currency
        total_so_amount = sale_order.amount_total  # e.g., 1000 USD
        
        # Calculate total payments in SO currency (all converted to SO currency at payment date)
        total_paid_so_currency = sum(p.amount_currency for p in payments)
        
        # Calculate remaining amount to be paid in SO currency
        remaining_so_currency = total_so_amount - total_paid_so_currency
        
        # Get invoice date rate (SO currency to company currency)
        invoice_date_rate = so_currency._get_conversion_rate(
            so_currency, company_currency, sale_order.company_id, self.date or fields.Date.today())
        
        # Convert remaining SO currency to company currency at invoice date rate
        remaining_company_currency = remaining_so_currency * invoice_date_rate
        
        # Add the original GEL payments (no conversion needed, already in company currency)
        gel_payments = payments.filtered(lambda p: p.currency_id == company_currency)
        gel_payment_total = sum(p.amount_company_currency_signed for p in gel_payments)
        
        # Add the USD payments converted to GEL at their respective payment dates
        usd_payments = payments.filtered(lambda p: p.currency_id == so_currency)
        usd_payment_in_gel = sum(p.amount_company_currency_signed for p in usd_payments)
        
        # Calculate final invoice amount in company currency
        invoice_amount_in_company_currency = gel_payment_total + usd_payment_in_gel + remaining_company_currency
        
        # Keep the total in SO currency unchanged
        invoice_amount_in_so_currency = total_so_amount
        
        # Prepare narration text with calculation details
        narration = f"""
Invoice Amount Calculation:
- Total Sale Order: {total_so_amount:.2f} {so_currency.name}
- Payments in {company_currency.name}: {gel_payment_total:.2f}
- Payments in {so_currency.name} (converted to {company_currency.name}): {usd_payment_in_gel:.2f}
- Remaining amount in {so_currency.name}: {remaining_so_currency:.2f}
- Remaining amount in {company_currency.name} (at rate {invoice_date_rate:.4f}): {remaining_company_currency:.2f}
- Total invoice amount in {company_currency.name}: {invoice_amount_in_company_currency:.2f}
"""
        
        # Update the invoice narration
        self.write({
            'narration': narration
        })
        
        move_id = self.id
        
        # SQL part unchanged
        # Correct handling for receivable line (credit)
        self.env.cr.execute("""
            UPDATE account_move_line 
            SET credit = %s, debit = 0.0, amount_currency = %s, balance = %s
            WHERE move_id = %s AND account_id = %s
        """, (
            invoice_amount_in_company_currency,
            -abs(invoice_amount_in_so_currency) if so_currency != company_currency else -invoice_amount_in_company_currency,
            -invoice_amount_in_company_currency,  # Balance should be negative for credit
            move_id,
            self.partner_id.property_account_receivable_id.id
        ))
        
        # Correct handling for income line (debit)
        self.env.cr.execute("""
            UPDATE account_move_line 
            SET debit = %s, credit = 0.0, amount_currency = %s, balance = %s
            WHERE move_id = %s AND account_id = %s
        """, (
            invoice_amount_in_company_currency,
            abs(invoice_amount_in_so_currency) if so_currency != company_currency else invoice_amount_in_company_currency,
            invoice_amount_in_company_currency,  # Balance should be positive for debit
            move_id,
            sale_order.order_line[0].product_id.categ_id.property_account_income_categ_id.id
        ))
        
        # Commit changes
        self.env.cr.commit()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Invoice Updated',
                'message': f'Invoice set to {invoice_amount_in_so_currency:.2f} {so_currency.name} ({invoice_amount_in_company_currency:.2f} {company_currency.name})',
                'sticky': False,
            }
        }


from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'


    amount_company_currency_signed = fields.Monetary(
        string="Amount in Company Currency",
        currency_field='company_currency_id',
        store=True,
        readonly=False,  # Make it editable
    )

    @api.onchange('amount')
    def _onchange_amount(self):
        """Update amount_company_currency_signed when amount changes"""
        if self.currency_id and self.company_id.currency_id:
            if self.currency_id != self.company_id.currency_id:
                company_amount = self.currency_id._convert(
                    self.amount,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date or fields.Date.context_today(self),
                )
                self.amount_company_currency_signed = company_amount
    
    @api.onchange('amount_company_currency_signed')
    def _onchange_amount_company_currency_signed(self):
        """Update amount when amount_company_currency_signed changes"""
        if self.currency_id and self.company_id.currency_id:
            if self.currency_id != self.company_id.currency_id:
                amount = self.company_id.currency_id._convert(
                    self.amount_company_currency_signed,
                    self.currency_id,
                    self.company_id,
                    self.date or fields.Date.context_today(self),
                )
                self.amount = amount
