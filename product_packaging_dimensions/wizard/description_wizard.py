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

    # ✅ FIXED (REMOVED WRONG DEFAULT)
    line_ids = fields.Many2many(
    "account.move.line",
    string="Select Products",
    domain="""
        [
            ('move_id', '=', context.get('active_id')),
            ('display_type', '=', False),
            ('tax_line_id', '=', False),
            ('product_id', '!=', False)
        ]
    """
)
    output_format = fields.Selection(
        [
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
        ],
        string="Report Format",
        default='pdf',
        required=True
    )

    # ==================================================
    # ITEM DESCRIPTION
    # ==================================================
    description_mode = fields.Selection(
        [
            ("export", "Exporter’s Custom"),
            ("buyer", "Buyer’s Custom"),
            ("foreign", "Foreign Language"),
        ],
        string="Item Description",
    )

    # ==================================================
    # PACKAGING
    # ==================================================
    packaging_id = fields.Many2one(
        "product.packaging",
        string="Packaging (Carton Type)",
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
    show_net_amount = fields.Boolean()
    show_net_cf = fields.Boolean()
    show_net_cif = fields.Boolean()

    # ==================================================
    # ✅ DEFAULT LINES (MAIN LOGIC)
    # ==================================================
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
    
        active_id = self.env.context.get("active_id")
        if active_id:
            invoice = self.env["account.move"].browse(active_id)
    
            # ✅ CORRECT FILTER
            lines = invoice.invoice_line_ids.filtered(
                lambda l: (
                    not l.display_type        # remove section/note
                    and l.product_id          # only product
                )
            )
    
            res["line_ids"] = [(6, 0, lines.ids)]
    
        return res
    # ==================================================
    # COMPUTE PACKAGING
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
            "show_net_amount": self.show_net_amount,
            "show_net_cf": self.show_net_cf,
            "show_net_cif": self.show_net_cif,
            "selected_line_ids": self.line_ids.ids
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
