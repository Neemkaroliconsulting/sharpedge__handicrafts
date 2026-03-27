from odoo import models, fields, api
import math

class SaleOrderPackingLine(models.Model):
    _name = "sale.order.packing.line"
    _description = "Sale Order Packing Line"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Delivery",
        ondelete="cascade"
    )

    order_id = fields.Many2one(
        "sale.order",
        ondelete="cascade"
    )

    product_id = fields.Many2one(
        "product.product",
        required=True
    )

    packaging_id = fields.Many2one(
        "product.packaging",
        required=True
    )

    # =========================
    # USER CONTROLLED
    # =========================
    box_qty = fields.Integer(
        string="Boxes",
        default=1
    )

    # =========================
    # 🔥 SNAPSHOT FROM INVENTORY
    # =========================
    units_per_box = fields.Float("PCS / Box")

    length = fields.Float("Length (cm)")
    width  = fields.Float("Breadth (cm)")
    height = fields.Float("Height (cm)")

    net_weight = fields.Float(
        "Net Weight (kg)",
        digits=(16, 4)
    )

    gross_weight = fields.Float(
        "Gross Weight (kg)",
        digits=(16, 4)
    )

    cbm = fields.Float(
        "CBM",
        digits=(16, 4)
    )
    total_units = fields.Float(
        "Total Units",
        compute="_compute_total_units",
        store=True
    )
    sequence = fields.Integer(
        "Sequence",
        default=10,
        help="Gives the sequence order when displaying a list of packing lines."
    )
    @api.depends("box_qty", "units_per_box")
    def _compute_total_units(self):
        for line in self:
            line.total_units = line.box_qty * line.units_per_box if line.box_qty and line.units_per_box else 0

    @api.onchange("units_per_box", "sequence")
    def _onchange_units_per_box(self):
        for line in self:
            if not line.order_id or not line.units_per_box:
                continue

            # sort all packagings of this product by level
            lines = line.order_id.packing_line_ids.filtered(
                lambda l: l.product_id == line.product_id
            ).sorted("sequence")

            base_qty = 0

            for idx, pkg_line in enumerate(lines):
                if idx == 0:
                    # 🔥 first level = sale order qty
                    base_qty = sum(
                        l.product_uom_qty
                        for l in line.order_id.order_line
                        if l.product_id == pkg_line.product_id
                    )
                else:
                    # 🔥 next level = previous boxes
                    base_qty = lines[idx - 1].box_qty

                if pkg_line.units_per_box:
                    pkg_line.box_qty = math.ceil(base_qty / pkg_line.units_per_box)
