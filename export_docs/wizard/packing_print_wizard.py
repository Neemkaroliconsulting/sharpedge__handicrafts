from odoo import models, fields, api


class PackingPrintWizard(models.TransientModel):
    _name = "packing.print.wizard"
    _description = "Packing List Print Wizard"

    picking_id = fields.Many2one(
        "stock.picking",
        required=True,
        readonly=True
    )

    packaging_id = fields.Many2one(
        "product.packaging",
        string="Packaging (Carton Type)",
        domain="[('id', 'in', allowed_packaging_ids)]",
        help="Select which packaging to print"
    )

    allowed_packaging_ids = fields.Many2many(
        "product.packaging",
        compute="_compute_allowed_packaging_ids",
        store=False
    )

    show_pcs_per_box = fields.Boolean(
        "Show PCS / Box",
        default=True
    )

    show_total_qty = fields.Boolean(
        "Show Total Qty (PCS × Boxes)",
        default=True
    )

    show_dimensions = fields.Boolean(
        "Show Box Dimensions (L×W×H)",
        default=True
    )

    @api.depends("picking_id")
    def _compute_allowed_packaging_ids(self):
        """
        Allow only those packaging which are used
        in the picking's products
        """
        for wiz in self:
            if not wiz.picking_id:
                wiz.allowed_packaging_ids = False
                continue

            products = wiz.picking_id.move_ids_without_package.product_id

            wiz.allowed_packaging_ids = self.env["product.packaging"].search([
                ("product_id", "in", products.ids)
            ])

    def action_print(self):
        return self.env.ref(
            "export_docs.action_packing_list_report"
        ).with_context(
            wizard_data={
                "packaging_id": self.packaging_id.id if self.packaging_id else False,
                "show_pcs_per_box": self.show_pcs_per_box,
                "show_total_qty": self.show_total_qty,
                "show_dimensions": self.show_dimensions,
            }
        ).report_action(self.picking_id)
