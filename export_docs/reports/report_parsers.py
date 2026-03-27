from odoo import api, models
class ExportInvoiceReport(models.AbstractModel):
    # Must match: report.[module_name].[template_xml_id]
    _name = 'report.export_docs.export_invoice_template' 
    _description = 'Export Invoice Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Explicitly browse the moves using the passed IDs
        docs = self.env['account.move'].browse(docids)
        
        # This dictionary is what your QWeb template will access
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'data': data, # Contains your wizard's boolean selections
        }


