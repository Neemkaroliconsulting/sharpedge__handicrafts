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
    # ✅ MAIN PRODUCT SELECTION (FINAL FIX)
    # ==================================================
#     line_ids = fields.Many2many(
#     "account.move.line",
#     "wizard_line_rel",
#     "wizard_id",
#     "line_id",
#     string="Select Products",
#     domain="[('move_id', '=', context.get('active_id'))]"
# )

    

    # ==================================================
    # OUTPUT FORMAT
    # ==================================================
    output_format = fields.Selection(
        [
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
        ],
        default='pdf',
        required=True
    )

    # ==================================================
    # DESCRIPTION MODE
    # ==================================================
    description_mode = fields.Selection(
        [
            ("export", "Exporter’s Custom"),
            ("buyer", "Buyer’s Custom"),
            ("foreign", "Foreign Language"),
        ],
    )

    # ==================================================
    # PACKAGING
    # ==================================================
    packaging_id = fields.Many2one(
        "product.packaging",
        string="Packaging",
        domain="[('id', 'in', allowed_packaging_ids)]",
    )

    allowed_packaging_ids = fields.Many2many(
        "product.packaging",
        compute="_compute_allowed_packaging_ids",
        store=False
    )

    show_pcs_per_box = fields.Boolean(default=True)
    show_total_qty = fields.Boolean(default=True)
    show_dimensions = fields.Boolean(default=True)
    # show_net_amount = fields.Boolean()
    # Radio buttons ke liye Selection field zaroori hai
    # show_net_cf = fields.Selection([
    #     ('yes', 'Yes'),
    #     ('no', 'No')
    # ], string="Show Net CF", default='no')
    
    # show_net_cif = fields.Selection([
    #     ('yes', 'Yes'),
    #     ('no', 'No')
    # ], string="Show Net CIF", default='no')
    amount_summary = fields.Selection([
        ('show_net_cf', 'Show Net C&F'),
        ('show_net_cif', 'Show Net CI&F'),
    ],)
        
        

    # ==================================================
    # ✅ FINAL CONTROL (MAIN LOGIC)
    # ==================================================
    # @api.model
    # def default_get(self, fields):
    #     res = super().default_get(fields)

    #     active_ids = self.env.context.get("active_ids")
    #     if not active_ids:
    #         return res

    #     invoice = self.env["account.move"].browse(active_ids[0])

    #     # 🔥 PERFECT FILTER
    #     lines = invoice.invoice_line_ids.filtered(
    #     lambda l: (
    #         not l.display_type and
    #         l.product_id and
    #         not l.tax_ids   # ❌ GST remove
    #     )
    # )

    #     res["line_ids"] = [(6, 0, lines.ids)]

    #     # ✅ SET BOTH (VERY IMPORTANT)
    #     res.update({
    #     "line_ids": [(6, 0, lines.ids)],
        
    # })

    #     return res

    # ==================================================
    # PACKAGING FILTER (UNCHANGED)
    # ==================================================
    @api.depends_context("active_model", "active_ids")
    def _compute_allowed_packaging_ids(self):
        for wiz in self:
            wiz.allowed_packaging_ids = False

            active_model = self.env.context.get("active_model")
            active_ids = self.env.context.get("active_ids")

            if not active_model or not active_ids:
                continue

            pickings = self.env["stock.picking"]

            if active_model == "stock.picking":
                pickings = self.env["stock.picking"].browse(active_ids)

            elif active_model == "stock.picking.batch":
                pickings = self.env["stock.picking.batch"].browse(
                    active_ids
                ).mapped("picking_ids")

            elif active_model == "account.move":
                pickings = self.env["account.move"].browse(
                    active_ids
                ).mapped(
                    "invoice_line_ids.sale_line_ids.order_id.picking_ids"
                )

            products = pickings.mapped("move_ids_without_package.product_id")

            wiz.allowed_packaging_ids = self.env["product.packaging"].search([
                ("product_id", "in", products.ids)
            ])

    # ==================================================
    # PRINT ACTION
    # ==================================================
    def action_print_report(self):
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")

        if not active_model or not active_ids:
            raise UserError("Nothing selected for printing")

        wizard_data = {
            "description_mode": self.description_mode,
            "packaging_id": self.packaging_id.id if self.packaging_id else False,
            "show_pcs_per_box": self.show_pcs_per_box,
            "show_total_qty": self.show_total_qty,
            "show_dimensions": self.show_dimensions,
            # "show_net_amount": self.show_net_amount,
            # "show_net_cf": self.show_net_cf,
            # "show_net_cif": self.show_net_cif,
            "amount_summary": self.amount_summary,
        }

        # ================= PDF =================
        if self.output_format == "pdf":

            if self.report_type == "export":
                return self.env.ref(
                    "export_docs.action_export_invoice_report"
                ).with_context(
                    wizard_data=wizard_data
                ).report_action(active_ids)

            if self.report_type == "tax":
                return self.env.ref(
                    "export_docs.action_tax_invoice_report"
                ).with_context(
                    wizard_data=wizard_data
                ).report_action(active_ids)

        # ================= EXCEL =================
        if self.output_format == "excel":
            return {
                "type": "ir.actions.act_url",
                "url": (
                    "/export_docs/excel"
                    f"?wizard_id={self.id}"
                    f"&active_ids={','.join(map(str, active_ids))}"
                ),
                "target": "self",
            }
