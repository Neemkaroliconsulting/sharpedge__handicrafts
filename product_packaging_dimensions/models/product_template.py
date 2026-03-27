from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    export_description = fields.Text(
        string="Item Export Description"
    )
    buyer_description = fields.Text(
            string="Item Buyer Description"
        )
    foreign_description = fields.Text(
            string="Item Foreign Description"
        )

    # DIMENSIONS
    x_product_length = fields.Float(string='Length')
    x_product_width = fields.Float(string='Width')
    x_product_height = fields.Float(string='Height')
    x_product_thickness = fields.Float(string='Thickness')

    x_dimension_uom_id = fields.Many2one(
        'uom.uom',
        string='Dimension UoM',
        domain=lambda self: [('category_id', '=', self.env.ref('uom.uom_categ_length').id)],
        default=lambda self: self.env.ref('uom.product_uom_cm', raise_if_not_found=False)
    )

    # WEIGHT
    x_product_net_weight = fields.Float(string="Net Weight")

    x_weight_uom_id = fields.Many2one(
        'uom.uom',
        string='Weight UoM',
        domain=lambda self: [('category_id', '=', self.env.ref('uom.product_uom_categ_kgm').id)],
        default=lambda self: self.env.ref('uom.product_uom_kgm', raise_if_not_found=False)
    )

    # # ADD THIS LINE - The missing field definition
    # x_net_weight_kg = fields.Float(
    #     string="Net Weight (kg)", 
    #     compute="_compute_weight_kg", 
    #     store=True
    # )


   

    x_buyer_sku = fields.Char(string="Buyer SKU")

    @api.depends('x_product_net_weight', 'x_weight_uom_id')
    def _compute_weight_kg(self):
        kg_uom = self.env.ref('uom.product_uom_kgm')
        for rec in self:
            if rec.x_weight_uom_id and rec.x_product_net_weight:
                rec.x_net_weight_kg = rec.x_weight_uom_id._compute_quantity(
                    rec.x_product_net_weight, kg_uom
                )
            else:
                rec.x_net_weight_kg = rec.x_product_net_weight

    customer_sku_ids = fields.One2many(
        'product.customer.sku',
        'product_tmpl_id',
        string="Customer Wise SKU"
    )

    customer_id = fields.Many2one(
        'res.partner',
        string="Customer",
        domain=[('customer_rank', '>', 0)],
        required=True
    )

    buyer_sku = fields.Char(
        string="Buyer SKU",
        required=True
    )

    customer_description = fields.Text(
        string="Customer Description"
    )
