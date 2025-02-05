import requests
from odoo import models, fields, api, _
import logging
from datetime import datetime
import pandas as pd

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    name_english = fields.Char(string="Product Name (English)")



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


def button_check_vat_payer(self):
   for record in self:
       try:
           usn = record.rs_acc
           usp = record.rs_pass
           tin = record.vat

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

           if response.status_code != 200:
               record.company_review = f"Failed to get response from service. Status code: {response.status_code}"
               return

           root = ET.fromstring(response.text)

           namespaces = {
               'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
               'ns': 'http://tempuri.org/'
           }

           result_element = root.find('.//ns:is_vat_payer_tinResult', namespaces)

           if result_element is not None:
               is_vat_payer = result_element.text.lower() == 'true'
               record.is_vat_payer = is_vat_payer
           else:
               record.company_review = "Could not find VAT payer status in response"

       except Exception as e:
           record.company_review = f"An error occurred: {str(e)}"

def button_get_name_from_tin(self):
   for record in self:
       try:
           usn = record.rs_acc
           usp = record.rs_pass
           tin = record.vat

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

           if response.status_code != 200:
               record.company_review = f"Failed to get response from service. Status code: {response.status_code}"
               return

           root = ET.fromstring(response.text)

           namespaces = {
               'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
               'ns': 'http://tempuri.org/'
           }

           result_element = root.find('.//ns:get_name_from_tinResult', namespaces)

           if result_element is not None:
               record.name = result_element.text
               self.button_check_vat_payer()  # Call VAT check after setting name
           else:
               record.name = response_element.text

       except Exception as e:
           record.company_review = f"An error occurred: {str(e)}"
