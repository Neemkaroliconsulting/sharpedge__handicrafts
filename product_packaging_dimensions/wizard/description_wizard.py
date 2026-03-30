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
    line_ids = fields.Many2many(
        "account.move.line",
        string="Select Products",
        domain="[('id', 'in', allowed_line_ids)]"
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
    # ITEM DESCRIPTION (INVOICE ONLY)
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
    # PACKING OPTIONS
    # ==================================================
    packaging_id = fields.Many2one(
        "product.packaging",
        string="Packaging (Carton Type)",
        domain="[('id', 'in', allowed_packaging_ids)]",
        help="Print only selected packaging"
    )

    allowed_packaging_ids = fields.Many2many(
        "product.packaging",
        compute="_compute_allowed_packaging_ids",
        store=False
    )

    allowed_line_ids = fields.Many2many(
        "account.move.line",
        compute="_compute_allowed_lines",
        store=False
    )

    show_pcs_per_box = fields.Boolean("Show PCS / Box", default=True)
    show_total_qty = fields.Boolean("Show Total Qty (PCS × Boxes)", default=True)
    show_dimensions = fields.Boolean("Show Box Dimensions (L×W×H)", default=True)
    show_net_amount = fields.Boolean("Net Amount") 
    show_net_cf = fields.Boolean("Net C&F") 
    show_net_cif = fields.Boolean("Net CI&F")

    # ==================================================
    # COMPUTES
    # ==================================================
    @api.depends_context("active_ids")
    def _compute_allowed_lines(self):
        for wiz in self:
            active_ids = self.env.context.get("active_ids", [])
            invoices = self.env["account.move"].browse(active_ids)
            lines = invoices.mapped("invoice_line_ids").filtered(
                lambda l: l.product_id
                and not l.display_type
                and not l.tax_line_id
            )
            wiz.allowed_line_ids = lines

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
                pickings = self.env["stock.picking.batch"].browse(active_ids).mapped("picking_ids")
            elif active_model == "account.move":
                pickings = self.env["account.move"].browse(active_ids).mapped(
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

        # ================= PDF =================
        if self.report_type == "packing":
            if active_model == "stock.picking":
                pickings = self.env["stock.picking"].browse(active_ids)
                batches = pickings.mapped("batch_id").filtered(lambda b: b)
                if batches:
                    if len(batches) > 1:
                        raise UserError("Selected deliveries belong to multiple batches.")
                    return self.env.ref("export_docs.action_packing_list_batch").with_context(
                        wizard_data=wizard_data).report_action(batches)
                return self.env.ref("export_docs.action_packing_list_delivery").with_context(
                    wizard_data=wizard_data).report_action(pickings)

            if active_model == "stock.picking.batch":
                batches = self.env["stock.picking.batch"].browse(active_ids)
                return self.env.ref("export_docs.action_packing_list_batch").with_context(
                    wizard_data=wizard_data).report_action(batches)

            if active_model == "account.move":
                invoices = self.env["account.move"].browse(active_ids)
                pickings = invoices.mapped("invoice_line_ids.sale_line_ids.order_id.picking_ids").filtered(
                    lambda p: p.state == "done" and p.picking_type_id.code == "outgoing")
                if not pickings:
                    raise UserError("No completed delivery found for this invoice.")
                batches = pickings.mapped("batch_id").filtered(lambda b: b)
                if batches:
                    if len(batches) == 1:
                        return self.env.ref("export_docs.action_packing_list_batch").with_context(
                            wizard_data=wizard_data, invoice_id=invoices.id).report_action(batches)
                    raise UserError("Invoice contains deliveries from multiple batches.")
                if len(pickings) != 1:
                    raise UserError("Invoice has multiple deliveries. Print from Delivery or Batch.")
                return self.env.ref("export_docs.action_packing_list_delivery").with_context(
                    wizard_data=wizard_data, invoice_id=invoices.id).report_action(pickings)
            
            raise UserError("Packing List cannot be printed from this screen")

        # ================= EXPORT / TAX =================
        xml_id = "export_docs.action_export_invoice_report" if self.report_type == "export" else "export_docs.action_tax_invoice_report"
        return self.env.ref(xml_id).with_context(wizard_data=wizard_data).report_action(active_ids)
