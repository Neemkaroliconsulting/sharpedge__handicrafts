from odoo import models, fields, api
import math
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"


    @api.depends(
        'product_uom_qty',
        'product_packaging_id',
        'product_uom',
        'state',   # 🔥 THIS WAS MISSING
    )
    def _compute_product_packaging_qty(self):
        # pehle Odoo ka default
        super()._compute_product_packaging_qty()

        # phir rounding
        for line in self:
            if line.product_packaging_id:
                line.product_packaging_qty = math.ceil(
                    line.product_packaging_qty
                )
    pkgs_from = fields.Integer("Pkgs From")
    pkgs_to = fields.Integer("Pkgs To")

    length = fields.Float("Length (cm)")
    width = fields.Float("Breadth (cm)")
    height = fields.Float("Height (cm)")

    net_wt_per_pkg = fields.Float("Net Wt / Pkg")
    gross_wt_per_pkg = fields.Float("Gross Wt / Pkg")

    cbm = fields.Float("CBM", compute="_compute_cbm", store=True)

    # ---------------- CBM COMPUTE ----------------
    @api.depends("length", "width", "height", "pkgs_from", "pkgs_to")
    def _compute_cbm(self):
        for line in self:
            if (
                line.length
                and line.width
                and line.height
                and line.pkgs_from
                and line.pkgs_to
                and line.pkgs_to >= line.pkgs_from
            ):
                pkg_count = line.pkgs_to - line.pkgs_from + 1
                cbm_per_pkg = (line.length * line.width * line.height) / 1000000
                line.cbm = cbm_per_pkg * pkg_count
            else:
                line.cbm = 0.0

    # ---------------- ONCHANGE PRODUCT ----------------
    @api.onchange("product_id")
    def _onchange_product_packaging(self):
        if not self.product_id:
            return

        packaging = self.product_id.packaging_ids[:1]
        if not packaging:
            return

        # 👇 CORRECT FIELD NAMES
        self.length = packaging.x_box_length
        self.width = packaging.x_box_width
        self.height = packaging.x_box_height
        self.net_wt_per_pkg = packaging.x_net_weight
        self.gross_wt_per_pkg = packaging.x_gross_weight

    # ---------------- COPY TO INVOICE ----------------
    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)

        vals.update({
            "pkgs_from": self.pkgs_from,
            "pkgs_to": self.pkgs_to,
            "length": self.length,
            "width": self.width,
            "height": self.height,
            "net_wt_per_pkg": self.net_wt_per_pkg,
            "gross_wt_per_pkg": self.gross_wt_per_pkg,
            "cbm": self.cbm,
        })
        return vals
    

    buyer_sku = fields.Char(string="Buyer SKU")
    @api.onchange('product_id', 'order_id.partner_id')
    def _onchange_buyer_sku(self):
        for line in self:
            line.buyer_sku = False

            if not line.product_id or not line.order_id.partner_id:
                return

            product = line.product_id.product_tmpl_id
            customer = line.order_id.partner_id

            mapping = product.customer_sku_ids.filtered(
                lambda m: m.customer_id == customer
            )

            if mapping:
                line.buyer_sku = mapping[0].buyer_sku
    
   