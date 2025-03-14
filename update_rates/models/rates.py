# -*- coding: utf-8 -*-
# models/nbg_currency.py
from odoo import models, fields, api, _
import requests
import datetime
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class NBGCurrencyUpdate(models.TransientModel):
    _name = "nbg.currency.update"
    _description = "Update Currency Rates from NBG"
    
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.today().replace(month=1, day=1)
    )
    
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.today
    )

    def action_update_rates(self):
        """Button action handler for wizard"""
        success_count, failed_dates = self.update_currency_rates(self.start_date, self.end_date)
        
        # Create user notification message
        message = _(f'Updated rates for {success_count} dates successfully.')
        if failed_dates:
            message += _('\nFailed to update rates for these dates: %s') % ', '.join(failed_dates[:10])
            if len(failed_dates) > 10:
                message += _(' and %d more...') % (len(failed_dates) - 10)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Currency Rates Update'),
                'message': message,
                'type': 'info',
                'sticky': False,
            }
        }

    @api.model
    def update_currency_rates(self, start_date=None, end_date=None):
        """Update currency rates for the given date range"""
        if not start_date:
            start_date = fields.Date.today()
        if not end_date:
            end_date = fields.Date.today()
        
        if start_date > end_date:
            start_date, end_date = end_date, start_date
            
        # Get all active currencies
        currencies = self.env['res.currency'].search([('active', '=', True)])
        
        success_count = 0
        failed_dates = []
        
        # Loop through dates
        current_date = start_date
        while current_date <= end_date:
            # Process all days including weekends
            try:
                if self._update_rates_for_date(current_date, currencies):
                    success_count += 1
                else:
                    failed_dates.append(current_date.strftime('%Y-%m-%d'))
            except Exception as e:
                _logger.error(f"Error updating rates for {current_date}: {e}")
                failed_dates.append(current_date.strftime('%Y-%m-%d'))
            
            current_date += datetime.timedelta(days=1)
        
        _logger.info(f"Updated rates for {success_count} dates successfully")
        if failed_dates:
            _logger.warning(f"Failed to update rates for dates: {', '.join(failed_dates[:10])}")
            if len(failed_dates) > 10:
                _logger.warning(f"...and {len(failed_dates) - 10} more")
        
        return success_count, failed_dates

    def _update_rates_for_date(self, date, currencies):
        """Update rates for all currencies for a specific date"""
        try:
            # Format date for API call
            date_str = date.strftime('%Y-%m-%d')
            api_url = f'https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/?date={date_str}'
            
            # Call the API
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            # Process the response
            data = response.json()
            if not data:
                _logger.warning(f'No data received from NBG API for date {date_str}')
                return False
            
            # The response is a list, get the first element
            data = data[0]
            currencies_data = data.get('currencies', [])
            
            if not currencies_data:
                _logger.warning(f'No currencies data found in NBG API response for date {date_str}')
                return False
            
            # Update each currency rate
            rate_model = self.env['res.currency.rate']
            for currency in currencies:
                # GEL is the base currency with rate 1.0
                if currency.name == 'GEL':
                    self._set_currency_rate(currency, date, 1.0)
                    continue
                
                # Find currency in API data
                for currency_data in currencies_data:
                    if currency_data.get('code') == currency.name:
                        rate = float(currency_data.get('rate', 0))
                        if rate > 0:
                            self._set_currency_rate(currency, date, rate)
                        break
            
            return True
            
        except requests.RequestException as e:
            _logger.error(f'Failed to fetch data from the API for {date_str}: {e}')
            return False
        except Exception as e:
            _logger.error(f'Error processing API data for {date_str}: {e}')
            return False
    
    def _set_currency_rate(self, currency, date, rate):
        """Set or update rate for a currency on a specific date"""
        rate_model = self.env['res.currency.rate']
        
        # Check if the rate already exists
        existing_rate = rate_model.search([
            ('currency_id', '=', currency.id),
            ('name', '=', date),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        rate_vals = {
            'currency_id': currency.id,
            'name': date,
            'rate': rate,
            'company_id': self.env.company.id
        }
        
        if existing_rate:
            existing_rate.write(rate_vals)
        else:
            rate_model.create(rate_vals)

    @api.model
    def update_today_rates(self):
        """Update rates for today (called by scheduled action)"""
        today = fields.Date.today()
        self.update_currency_rates(today, today)
        return True
        
    @api.model
    def update_year_rates(self):
        """Update all rates from beginning of year to today"""
        start_date = fields.Date.today().replace(month=1, day=1)
        end_date = fields.Date.today()
        self.update_currency_rates(start_date, end_date)
        return True


class Currency(models.Model):
    _inherit = "res.currency"
    
    def action_open_nbg_update(self):
        """Open the NBG currency update wizard"""
        return {
            'name': 'Update from NBG',
            'type': 'ir.actions.act_window',
            'res_model': 'nbg.currency.update',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_start_date': fields.Date.today(), 'default_end_date': fields.Date.today()},
        }