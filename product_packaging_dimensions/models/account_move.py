from odoo import models,fields, api

class AccountMove(models.Model):
    _inherit = "account.move"
    
   

    def action_print_invoice_cum_packing(self):
        return self.env.ref(
            "product_packaging_dimensions.action_invoice_cum_packing"
        ).report_action(self)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pkgs_from = fields.Integer()
    pkgs_to = fields.Integer()

    length = fields.Float()
    width = fields.Float()
    height = fields.Float()

    net_wt_per_pkg = fields.Float()
    gross_wt_per_pkg = fields.Float()
    cbm = fields.Float()

