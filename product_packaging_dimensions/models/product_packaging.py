from odoo import models, fields, api


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    # =================================================
    # PACKAGING PRODUCT
    # =================================================
    packaging_product_id = fields.Many2one(
        'product.template',
        string="Packaging Product",
        help="Outer carton / box as a product"
    )
    pkgs_from = fields.Integer("Pkgs From")
    pkgs_to = fields.Integer("Pkgs To")
    product_uom_qty = fields.Many2one(
        "uom.uom",
        string="Product UoM",
        related="product_id.uom_id",
        store=True,
        readonly=True
    )
    per_pkg_qty = fields.Float(
        string="Contained Qty",
        digits=(16, 4)
    )

    # =================================================
    # DIMENSIONS
    # =================================================
    x_box_length = fields.Float(string="Length (cm)")
    x_box_width = fields.Float(string="Breadth (cm)")
    x_box_height = fields.Float(string="Height (cm)")

    # =================================================
    # WEIGHTS
    # =================================================
    x_manual_packaging_weight = fields.Float(
        string="Packaging Weight (kg)",
        digits=(16, 4)
    )

    x_net_weight = fields.Float(
        string="Net Weight (kg)",
        compute="_compute_net_weight",
        store=True,
        digits=(16, 4)
    )

    x_gross_weight = fields.Float(
        string="Gross Weight (kg)",
        compute="_compute_gross_weight",
        store=True,
        digits=(16, 4)
    )

    x_cbm = fields.Float(
    string="CBM",
    compute="_compute_volume",
    store=True,
    digits=(16, 4)   # 🔥 IMPORTANT
    )

    x_cft = fields.Float(
        string="CFT",
        compute="_compute_volume",
        store=True,
        digits=(16, 4)
    )


    # =================================================
    # NET = qty × PRODUCT NET WEIGHT
    # =================================================
    @api.depends(
        'qty',
        'product_id',
        'product_id.product_tmpl_id.x_product_net_weight'
    )
    def _compute_net_weight(self):
        for rec in self:
            if rec.product_id:
                product_weight = (
                    rec.product_id.product_tmpl_id.x_product_net_weight or 0.0
                )
            else:
                product_weight = 0.0

            rec.x_net_weight = (rec.qty or 0.0) * product_weight

    # =================================================
    # ONCHANGE: COPY PACKAGING WEIGHT
    # =================================================
    @api.onchange('packaging_product_id')
    def _onchange_packaging_product_id(self):
        if self.packaging_product_id:
            pkg_weight_g = self.packaging_product_id.x_product_net_weight or 0.0
            self.x_manual_packaging_weight = pkg_weight_g / 1000.0
        else:
            self.x_manual_packaging_weight = 0.0
    # =================================================
    # GROSS = NET + PACKAGING
    # =================================================
    @api.depends(
        'x_net_weight',
        'packaging_product_id.x_product_net_weight',
        'x_manual_packaging_weight'
    )
    def _compute_gross_weight(self):
        for rec in self:
            if rec.packaging_product_id:
                pkg_weight = (
                    (rec.packaging_product_id.x_product_net_weight or 0.0)/1000
                )
            else:
                pkg_weight = rec.x_manual_packaging_weight or 0.0

            rec.x_gross_weight = (rec.x_net_weight or 0.0) + pkg_weight

    # =================================================
    # VOLUME
    # =================================================
    @api.depends('x_box_length', 'x_box_width', 'x_box_height')
    def _compute_volume(self):
        for rec in self:
            if rec.x_box_length and rec.x_box_width and rec.x_box_height:
                cbm = (
                    rec.x_box_length *
                    rec.x_box_width *
                    rec.x_box_height
                ) / 1_000_000
                rec.x_cbm = cbm
                rec.x_cft = cbm * 35.3147
            else:
                rec.x_cbm = 0.0
                rec.x_cft = 0.0
