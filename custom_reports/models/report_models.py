from odoo import models, fields
import base64
import xlsxwriter
from io import BytesIO

class SaleOrderReport(models.AbstractModel):
    _name = 'report.custom_reports.sale_order_report'
    _description = 'Sale Order Custom Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        sale_order = self.env['sale.order'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'doc': sale_order,
        }




