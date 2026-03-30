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
        domain="[('display_type','=',False),('tax_line_id','=',False)]"
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
    # PACKING OPTIONS (MERGED FROM packing.print.wizard)
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

    show_pcs_per_box = fields.Boolean("Show PCS / Box", default=True)
    show_total_qty = fields.Boolean("Show Total Qty (PCS × Boxes)", default=True)
    show_dimensions = fields.Boolean("Show Box Dimensions (L×W×H)", default=True)
    show_net_amount = fields.Boolean("Net Amount") 
    show_net_cf = fields.Boolean("Net C&F") 
    show_net_cif = fields.Boolean("Net CI&F")
    # ==================================================
    # COMPUTE ALLOWED PACKAGING
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

            if self.report_type == "packing":
                # existing packing logic (same as yours)
                pass

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
            active_ids = self.env.context.get("active_ids", [])
            return {
                "type": "ir.actions.act_url",
                "url": (
                    "/export_docs/excel"
                    f"?wizard_id={self.id}"
                    f"&active_ids={','.join(map(str, active_ids))}"
                ),
                "target": "self",
            }

        # ==================================================
        # 📦 PACKING LIST
        # ==================================================
        if self.report_type == "packing":

            # DELIVERY SCREEN
            if active_model == "stock.picking":
                pickings = self.env["stock.picking"].browse(active_ids)
                batches = pickings.mapped("batch_id").filtered(lambda b: b)

                # 🔹 Delivery belongs to batch → print batch packing list
                if batches:
                    if len(batches) > 1:
                        raise UserError(
                            "Selected deliveries belong to multiple batches.\n"
                            "Please print Packing List from Batch."
                        )

                    return self.env.ref(
                        "export_docs.action_packing_list_batch"
                    ).with_context(
                        wizard_data=wizard_data
                    ).report_action(batches)

                # 🔹 NO batch → delivery packing list
                return self.env.ref(
                    "export_docs.action_packing_list_delivery"
                ).with_context(
                    wizard_data=wizard_data
                ).report_action(pickings)

            # BATCH SCREEN
            if active_model == "stock.picking.batch":
                batches = self.env["stock.picking.batch"].browse(active_ids)

                return self.env.ref(
                    "export_docs.action_packing_list_batch"
                ).with_context(
                    wizard_data=wizard_data
                ).report_action(batches)

            # INVOICE SCREEN
            if active_model == "account.move":
                invoices = self.env["account.move"].browse(active_ids)

                # 1️⃣ Invoice → Sale → Picking (DONE outgoing only)
                pickings = invoices.mapped(
                    "invoice_line_ids.sale_line_ids.order_id.picking_ids"
                ).filtered(lambda p: p.state == "done" and p.picking_type_id.code == "outgoing")

                if not pickings:
                    raise UserError(
                        "No completed delivery found for this invoice."
                    )

                # 2️⃣ Check Batch
                batches = pickings.mapped("batch_id").filtered(lambda b: b)

                # ✅ Case A: Single Batch
                if batches:
                    if len(batches) == 1:
                        return self.env.ref(
                            "export_docs.action_packing_list_batch"
                        ).with_context(
                            wizard_data=wizard_data,
                            invoice_id=invoices.id   # 👈 invoice reference only
                        ).report_action(batches)

                    # ❌ Multiple batches
                    raise UserError(
                        "Invoice contains deliveries from multiple batches.\n"
                        "Please print Packing List from Batch."
                    )

                # 3️⃣ No Batch → Single Delivery only
                if len(pickings) != 1:
                    raise UserError(
                        "Invoice has multiple deliveries.\n"
                        "Please print Packing List from Delivery or Batch."
                    )

                # ✅ Case B: Single Delivery, no batch
                return self.env.ref(
                    "export_docs.action_packing_list_delivery"
                ).with_context(
                    wizard_data=wizard_data,
                    invoice_id=invoices.id   # 👈 invoice sirf context me
                ).report_action(pickings)







            raise UserError("Packing List cannot be printed from this screen")

        # ==================================================
        # 📄 EXPORT / TAX INVOICE
        # ==================================================
        if self.report_type == "export":
            xml_id = "export_docs.action_export_invoice_report"
        else:
            xml_id = "export_docs.action_tax_invoice_report"

        return self.env.ref(xml_id).with_context(
            wizard_data=wizard_data
        ).report_action(active_ids)
    
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
    
        active_ids = self.env.context.get("active_ids", [])
        active_model = self.env.context.get("active_model")
    
        if active_model == "account.move" and active_ids:
            invoices = self.env["account.move"].browse(active_ids)
    
            lines = invoices.mapped("invoice_line_ids")
    
            # ✅ FIXED FILTER (correct indent)
            lines = lines.filtered(
                lambda l: l.product_id 
                and not l.display_type 
                and not l.tax_line_id 
                and l.move_id.id in active_ids
            )
    
            res["line_ids"] = [(6, 0, lines.ids)]
    
        return res
