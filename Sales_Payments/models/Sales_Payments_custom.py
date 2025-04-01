from odoo import models, fields, api, _
from odoo.exceptions import UserError
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
        
        # Get the sale order
        sale_order = self.env['sale.order'].search([
            ('invoice_ids', 'in', self.ids)
        ], limit=1)
        
        if not sale_order:
            raise UserError("No related sale order found for this invoice.")
        
        if self.state != 'draft':
            raise UserError("You can only modify draft invoices.")
        
        # Get payments from the sale order
        payments = sale_order.payments_cus_ids
        
        if not payments:
            raise UserError("No payments found for this sale order.")
        
        # Calculate total payment amount
        total_payment_amount = sum(p.amount_company_currency_signed for p in payments)
        if total_payment_amount <= 0:
            raise UserError("Total payment amount must be greater than zero.")
        
        # Required accounts
        receivable_account = self.partner_id.property_account_receivable_id
        advance_account = self.env['account.account'].search([('code', '=', '1410')], limit=1)
        income_account = self.env['account.account'].search([('code', '=', '3120')], limit=1)
        
        if not advance_account or not income_account:
            raise UserError("Could not find required accounts: 1410 (Advance) or 3120 (Income)")
        
        # Find all debit lines (product lines essentially)
        debit_lines = self.line_ids.filtered(lambda l: l.debit > 0)
        
        # Calculate total debit
        total_debit = sum(line.debit for line in debit_lines)
        
        # Calculate how much to reduce from each line proportionally
        for line in debit_lines:
            proportion = line.debit / total_debit
            amount_to_subtract = proportion * total_payment_amount
            
            # Update the line directly with SQL to avoid ORM recomputation
            self.env.cr.execute("""
                UPDATE account_move_line 
                SET debit = debit - %s, balance = balance - %s 
                WHERE id = %s
            """, (amount_to_subtract, amount_to_subtract, line.id))
        
        # Find credit lines (the receivable lines)
        credit_lines = self.line_ids.filtered(lambda l: l.credit > 0)
        
        # Calculate total credit
        total_credit = sum(line.credit for line in credit_lines)
        
        # Update credit lines proportionally
        for line in credit_lines:
            proportion = line.credit / total_credit
            amount_to_subtract = proportion * total_payment_amount
            
            # Update the line directly with SQL
            self.env.cr.execute("""
                UPDATE account_move_line 
                SET credit = credit - %s, balance = balance + %s 
                WHERE id = %s
            """, (amount_to_subtract, amount_to_subtract, line.id))
        
        # Create journal entries for each payment
        invoice_currency = self.currency_id
        company_currency = self.company_id.currency_id
        
        # Prepare narration text
        narration = f"""
    Invoice Amount Calculation with Advance Payments:
    - Total Advance Payments: {total_payment_amount:.2f} {company_currency.name}
    - Payments applied proportionally to all invoice lines
    - Journal entries created for accounts:
      * Debit 3120 (Income)
      * Credit 1410 (Advance)
    
    Payments applied:
    """
        
        for payment in payments:
            payment_amount = payment.amount_company_currency_signed
            payment_currency = payment.currency_id
            payment_date = payment.payment_date or fields.Date.today()
            
            # Add payment details to narration
            narration += f"- {payment.name}: {payment.amount:.2f} {payment_currency.name} ({payment_amount:.2f} {company_currency.name}) - {payment_date}\n"
            
            # Convert payment amount to invoice currency using the rate from payment date
            if payment_currency != invoice_currency:
                payment_amount_in_invoice_currency = payment_currency._convert(
                    payment.amount,
                    invoice_currency,
                    self.company_id,
                    payment_date
                )
            else:
                payment_amount_in_invoice_currency = payment.amount
                
            # Insert income line (3120 debit)
            self.env.cr.execute("""
                INSERT INTO account_move_line (
                    move_id, name, account_id, debit, credit, 
                    date, partner_id, currency_id, amount_currency, 
                    balance, company_id, display_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.id, 
                f'Income from advance payment {payment.name}',
                income_account.id,
                payment_amount,
                0.0,
                self.date,
                self.partner_id.id,
                invoice_currency.id,
                payment_amount_in_invoice_currency,
                payment_amount,
                self.company_id.id,
                False
            ))
            
            # Insert advance line (1410 credit)
            self.env.cr.execute("""
                INSERT INTO account_move_line (
                    move_id, name, account_id, debit, credit, 
                    date, partner_id, currency_id, amount_currency, 
                    balance, company_id, display_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.id, 
                f'Advance payment reconciliation {payment.name}',
                advance_account.id,
                0.0,
                payment_amount,
                self.date,
                self.partner_id.id,
                invoice_currency.id,
                -payment_amount_in_invoice_currency,
                -payment_amount,
                self.company_id.id,
                False
            ))
        
        # Update invoice narration
        if self.narration:
            self.narration += '\n\n' + narration
        else:
            self.narration = narration
        
        # Invalidate cache to ensure updated values are shown
        self.invalidate_recordset()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Advances Applied',
                'message': f'Advanced payments totaling {total_payment_amount} have been proportionally applied to reduce the invoice',
                'sticky': False,
            }
        }
        
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


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    def action_change_credit_account(self):
        """
        Button action to change account.move.line entries with credit 1410 to account 3120
        for this payment and its linked journal entries. Works on posted entries as well.
        """
        self.ensure_one()
        modified_count = 0
        
        # Find all linked journal entries
        linked_moves = self.env['account.move']
        
        # Add the payment's move
        if self.move_id:
            linked_moves |= self.move_id
        
        # Add reconciled moves (invoices, bills, etc. that this payment reconciles with)
        for line in self.move_id.line_ids:
            if line.full_reconcile_id:
                for reconciled_line in line.full_reconcile_id.reconciled_line_ids:
                    if reconciled_line.move_id and reconciled_line.move_id != self.move_id:
                        linked_moves |= reconciled_line.move_id
        
        # Get the target account
        target_account = self.env['account.account'].search([
            ('code', '=', '3120')
        ], limit=1)
        
        if not target_account:
            raise UserError(_("Account with code 3120 not found for this company!"))
        
        # Update all the moves
        posted_moves = self.env['account.move']
        
        for move in linked_moves:
            # Find all move lines with account_id 1410
            lines_to_change = move.line_ids.filtered(
                lambda line: line.account_id.code == '1410'
            )
            
            # Check if the move is posted
            if move.state == 'posted':
                posted_moves |= move
                # Unpost the move to make changes
                move.button_draft()
            
            # Update the lines
            for line in lines_to_change:
                line.account_id = target_account.id
                modified_count += 1
                
            # Re-post the move if it was posted
            if move in posted_moves:
                move.action_post()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Account Change"),
                'message': _(f"{modified_count} line(s) with account 1410 changed to account 3120 across {len(linked_moves)} journal entries."),
                'type': 'success',
                'sticky': False,
            }
        }