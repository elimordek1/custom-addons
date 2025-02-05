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
        for record in self:
            try:
                usn = record.rs_acc  # Use the rs_acc field of the record
                usp = record.rs_pass  # Use the rs_pass field of the record
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

                # Define the URL and headers
                url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_name_from_tin"
                }

                # Send the request
                response = requests.post(url, data=soap_request, headers=headers)

                # Check for a successful response
                if response.status_code != 200:
                    record.company_review = f"Failed to get response from service. Status code: {response.status_code}"
                    continue

                # Parse the XML response
                root = ET.fromstring(response.text)

                # Define the namespace (use the appropriate namespace for your SOAP response)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
                }

                # Find the `name` element in the response
                result_element = root.find('.//ns:get_name_from_tinResult', namespaces)

                # Check if the element was found and assign its text to the company_review field
                if result_element is not None:
                    record.name = result_element.text
                else:
                    record.name = response_element.text

            except Exception as e:
                record.company_review = f"An error occurred: {str(e)}"
