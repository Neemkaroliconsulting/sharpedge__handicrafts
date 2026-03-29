from odoo import models, fields, api
from odoo.exceptions import UserError


class DescriptionSelectWizard(models.TransientModel):
    _name = "description.select.wizard"
    _description = "Description & Print Options Wizard"

    # ==================================================
    # REPORT TYPE
    # ==================================================
    report_type = fields.Selection(
        [
            ("packing", "Packing List"),
            ("export", "Export Invoice for Buyer"),
            ("tax", "Export Invoice for Custom GST"),
        ],
        default="export",
        required=True,
    )

    # ==================================================
    # PRODUCTS (ONLY CURRENT INVOICE)
    # ==================================================
    line_ids = fields.Many2many(
        "account.move.line",
        string="Select Products",
        domain="[('move_id', '=', context.get('active_id')), ('tax_line_id', '=', False)]"
    )

    # ==================================================
    # OUTPUT
    # ==================================================
    output_format = fields.Selection(
        [
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
        ],
        string="Report Format",
        default='pdf',
        required=True
    )

    description_mode = fields.Selection(
        [
            ("export", "Exporter’s Custom"),
            ("buyer", "Buyer’s Custom"),
            ("foreign", "Foreign Language"),
        ],
        string="Item Description",
    )

    # ==================================================
    # OPTIONS
    # ==================================================
    show_pcs_per_box = fields.Boolean("Show PCS / Box", default=True)
    show_total_qty = fields.Boolean("Show Total Qty (PCS × Boxes)", default=True)
    show_dimensions = fields.Boolean("Show Box Dimensions (L×W×H)", default=True)

    show_net_amount = fields.Boolean("Net Amount")
    show_net_cf = fields.Boolean("Net C&F")
    show_net_cif = fields.Boolean("Net CI&F")

    # 👉 NEW (dynamic grouping future ready)
    group_by = fields.Selection(
        [
            ('none', 'No Grouping'),
            ('buyer_order', 'Buyer Order'),
        ],
        default='buyer_order',
        string="Grouping"
    )

    # ==================================================
    # DEFAULT LOAD (ONLY CURRENT INVOICE LINES)
    # ==================================================
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        active_id = self.env.context.get("active_id")

        if active_id:
            invoice = self.env["account.move"].browse(active_id)

            lines = invoice.invoice_line_ids.filtered(
                lambda l: l.product_id and not l.tax_line_id and not l.display_type
            )

            res["line_ids"] = [(6, 0, lines.ids)]

        return res

    # ==================================================
    # PRINT ACTION (🔥 FIXED - NO CONTEXT BUG)
    # ==================================================
       def action_print_report(self):
        return self.env.ref(
            "export_docs.action_export_invoice_report"
        ).report_action(
            self.env.context.get("active_ids"),
            data={
                "selected_line_ids": self.line_ids.ids,
                "description_mode": self.description_mode,
                "show_net_amount": self.show_net_amount,
                "show_net_cf": self.show_net_cf,
                "show_net_cif": self.show_net_cif,
                "group_by": self.group_by,
            }
        )
