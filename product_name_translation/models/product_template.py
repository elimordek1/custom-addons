from odoo import models, fields, api
import requests
import xml.etree.ElementTree as ET
import logging

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    rs_acc = fields.Char(string='RS.GE Account')
    rs_pass = fields.Char(string='RS.GE Password')

class ResPartner(models.Model):
    _inherit = 'res.partner'

    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    is_vat_payer = fields.Boolean(string='Is VAT Payer')

    @api.depends('user_id.rs_acc')
    def _compute_rs_acc(self):
        for record in self:
            user = self.env.user
            record.rs_acc = user.rs_acc

    @api.depends('user_id.rs_pass')
    def _compute_rs_pass(self):
        for record in self:
            user = self.env.user
            record.rs_pass = user.rs_pass

    def button_get_name_from_tin(self):
        self.ensure_one()
        try:
            _logger.info('Starting get_name_from_tin for VAT: %s', self.vat)
            usn = self.rs_acc
            usp = self.rs_pass
            tin = self.vat

            if not all([usn, usp, tin]):
                _logger.error('Missing required credentials. rs_acc: %s, vat: %s', usn, tin)
                return False

            soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_name_from_tin xmlns="http://tempuri.org/">
                  <su>{usn}</su>
                  <sp>{usp}</sp>
                  <tin>{tin}</tin>
                </get_name_from_tin>
              </soap:Body>
            </soap:Envelope>"""

            url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_name_from_tin"
            }

            response = requests.post(url, data=soap_request, headers=headers)
            
            _logger.info('Response status code: %s', response.status_code)
            _logger.debug('Response content: %s', response.text)

            if response.status_code == 200:
                root = ET.fromstring(response.text)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'ns': 'http://tempuri.org/'
                }
                result_element = root.find('.//ns:get_name_from_tinResult', namespaces)

                if result_element is not None:
                    _logger.info('Successfully got name from TIN: %s', result_element.text)
                    self.write({
                        'name': result_element.text,
                    })
                    self.env.cr.commit()
                    self.button_check_vat_payer()
                else:
                    _logger.warning('No result element found in response')

            return True

        except Exception as e:
            _logger.error('Error in get_name_from_tin: %s', str(e))
            self.env.cr.rollback()
            return False

    def button_check_vat_payer(self):
        self.ensure_one()
        try:
            _logger.info('Starting check_vat_payer for VAT: %s', self.vat)
            usn = self.rs_acc
            usp = self.rs_pass
            tin = self.vat

            if not all([usn, usp, tin]):
                _logger.error('Missing required credentials. rs_acc: %s, vat: %s', usn, tin)
                return False

            soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <is_vat_payer_tin xmlns="http://tempuri.org/">
                  <su>{usn}</su>
                  <sp>{usp}</sp>
                  <tin>{tin}</tin>
                </is_vat_payer_tin>
              </soap:Body>
            </soap:Envelope>"""

            url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/is_vat_payer_tin"
            }

            response = requests.post(url, data=soap_request, headers=headers)
            
            _logger.info('Response status code: %s', response.status_code)
            _logger.debug('Response content: %s', response.text)
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'ns': 'http://tempuri.org/'
                }
                result_element = root.find('.//ns:is_vat_payer_tinResult', namespaces)
                
                if result_element is not None:
                    is_vat_payer = result_element.text.lower() == 'true'
                    _logger.info('VAT payer status: %s', is_vat_payer)
                    self.write({'is_vat_payer': is_vat_payer})
                    self.env.cr.commit()
                else:
                    _logger.warning('No result element found in response')
                    
            return True

        except Exception as e:
            _logger.error('Error in check_vat_payer: %s', str(e))
            self.env.cr.rollback()
            return False

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    name_english = fields.Char(string="Product Name (English)")