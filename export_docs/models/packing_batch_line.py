from odoo import models, fields,api

class StockPickingBatchPackingLine(models.Model):
    _name = "stock.picking.batch.packing.line"
    _description = "Batch Packing Line"
    

    batch_id = fields.Many2one(
        "stock.picking.batch",
        ondelete="cascade",
        index=True,
        required=True,
    )
    pcs_per_box = fields.Float(
        "PCS / Box",
        compute="_compute_pcs_per_box",
        store=True
    )
    picking_id = fields.Many2one(
        "stock.picking",
        string="Delivery Order",
        required=True,
    )
    packed_qty = fields.Float("Packed Qty")  

    packaging_id = fields.Many2one("product.packaging", string="Packaging")
    product_ids = fields.Many2many("product.product", string="Products")

    case_no_from = fields.Integer("Case No From")
    case_no_to = fields.Integer("Case No To")

    box_qty = fields.Integer("Total Boxes")
    total_units = fields.Float("Total Units")

    net_weight = fields.Float("Net Weight")
    gross_weight = fields.Float("Gross Weight")
    cbm = fields.Float("CBM")
    length = fields.Float()
    width = fields.Float()
    height = fields.Float()


    @api.depends("total_units", "box_qty")
    def _compute_pcs_per_box(self):
        for line in self:
            if line.box_qty:
                line.pcs_per_box = line.total_units / line.box_qty
            else:
                line.pcs_per_box = 0.0