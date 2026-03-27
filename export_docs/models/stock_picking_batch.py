from odoo import models, fields, api

class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"


    # batch_packing_line_ids = fields.One2many(
    #     "stock.picking.batch.packing.line",
    #     "batch_id",
    #     string="Batch Packing Lines"
    # )
    packaging_id = fields.Many2one(
    "product.packaging",
    string="Packaging"
)
    length = fields.Float()
    width = fields.Float()
    height = fields.Float()


    product_ids = fields.Many2many(
        "product.product",
        string="Products"
    )

    box_qty = fields.Integer("Total Boxes")
    total_units = fields.Float("Total Units")

    case_no_from = fields.Integer("Case No From")
    case_no_to = fields.Integer("Case No To")

    net_weight = fields.Float("Net Weight")
    gross_weight = fields.Float("Gross Weight")
    cbm = fields.Float("CBM")

    pcs_per_box = fields.Float(
        "PCS / Box",
        compute="_compute_pcs_per_box",
        store=True
    )
    @api.depends("total_units", "box_qty")
    def _compute_pcs_per_box(self):
        for line in self:
            if line.box_qty:
                line.pcs_per_box = line.total_units / line.box_qty
            else:
                line.pcs_per_box = 0.0


    # @api.depends("picking_ids.packing_line_ids")
    # def _compute_batch_packing(self):
    #     for batch in self:
    #         batch.batch_packing_line_ids.unlink()

    #         grouped = {}
    #         case_counter = 1

    #         for picking in batch.picking_ids:
    #             for line in picking.packing_line_ids:
    #                 key = line.packaging_id.id

    #                 if key not in grouped:
    #                     grouped[key] = {
    #                         "packaging": line.packaging_id,
    #                         "box_qty": 0,
    #                         "units": 0,
    #                         "net": 0,
    #                         "gross": 0,
    #                         "cbm": 0,
    #                         "products": set(),
    #                     }

    #                 g = grouped[key]
    #                 g["box_qty"] += line.box_qty
    #                 g["units"] += line.packed_qty
    #                 g["net"] += line.net_weight * line.box_qty
    #                 g["gross"] += line.gross_weight * line.box_qty
    #                 g["cbm"] += line.cbm * line.box_qty
    #                 g["products"].add(line.product_id.id)

    #         lines = []
    #         for g in grouped.values():
    #             start = case_counter
    #             end = case_counter + g["box_qty"] - 1

    #             lines.append((0, 0, {
    #                 "packaging_id": g["packaging"].id,
    #                 "case_no_from": start,
    #                 "case_no_to": end,
    #                 "box_qty": g["box_qty"],
    #                 "total_units": g["units"],
    #                 "net_weight": g["net"],
    #                 "gross_weight": g["gross"],
    #                 "cbm": g["cbm"],
    #                 "product_ids": [(6, 0, list(g["products"]))],
    #             }))

    #             case_counter = end + 1

    #         batch.batch_packing_line_ids = lines

    batch_packing_line_ids = fields.One2many(
    "stock.picking.batch.packing.line",
    "batch_id",
    string="Batch Packing Lines",
)

    # def action_confirm(self):
    #     res = super().action_confirm()

    #     for batch in self:
    #         batch.batch_packing_line_ids.unlink()

    #         case_counter = 1

    #         for picking in batch.picking_ids:
    #             for pl in picking.packing_line_ids:
    #                 start = case_counter
    #                 end = case_counter + (pl.box_qty or 0) - 1

    #                 self.env["stock.picking.batch.packing.line"].create({
    #                     "batch_id": batch.id,
    #                     "picking_id": picking.id,
    #                     "product_ids": [(6, 0, [pl.product_id.id])],
    #                     "packaging_id": pl.packaging_id.id,
    #                     "box_qty": pl.box_qty,
    #                     "packed_qty": pl.packed_qty,
    #                     "total_units": pl.total_units,
    #                     "case_no_from": start,
    #                     "case_no_to": end,
    #                     "net_weight": pl.net_weight,
    #                     "gross_weight": pl.gross_weight,
    #                     "cbm": pl.cbm,
    #                 })

    #                 case_counter = end + 1

    #     return res

    # def action_confirm(self):
    #     res = super().action_confirm()
    #     self._sync_batch_packing()
    #     return res

    
    def _sync_batch_packing(self):
        BatchLine = self.env["stock.picking.batch.packing.line"]

        for batch in self:
            batch.batch_packing_line_ids.unlink()
            case_counter = 1

            for picking in batch.picking_ids:
                # safety: ensure delivery packing exists
                if not picking.packing_line_ids:
                    picking._recompute_packing_from_qty(use_done_qty=False)

                for pl in picking.packing_line_ids:
                    start = case_counter
                    end = case_counter + (pl.box_qty or 0) - 1

                    pkg = pl.packaging_id
                    if not pkg:
                        continue

                    BatchLine.create({
                        "batch_id": batch.id,
                        "picking_id": picking.id,
                        "packaging_id": pkg.id,

                        # ✅ THIS WILL WORK (fields exist)
                        "length": pkg.x_box_length or 0,
                        "width": pkg.x_box_width or 0,
                        "height": pkg.x_box_height or 0,

                        "box_qty": pl.box_qty,
                        "total_units": pl.total_units,
                        "case_no_from": start,
                        "case_no_to": end,
                        "net_weight": pl.net_weight,
                        "gross_weight": pl.gross_weight,
                        "cbm": pl.cbm,
                        "product_ids": [(6, 0, [pl.product_id.id])],
                    })


                    case_counter = end + 1
    def action_print_packing_list(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Batch Packing List",
            "res_model": "description.select.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "stock.picking.batch",
                "active_ids": self.ids,
                "report_type": "packing",
            },
        }



#     @api.depends(
#     "picking_ids",
#     "picking_ids.packing_line_ids",
# )
#     def _compute_batch_packing(self):
#         for batch in self:
#             batch.batch_packing_line_ids = [(5, 0, 0)]

#             lines = []

#             for picking in batch.picking_ids:
#                 for pl in picking.packing_line_ids:
#                     lines.append((0, 0, {
#                         "batch_id": batch.id,
#                         "picking_id": picking.id,
#                         "product_ids": [(6, 0, [pl.product_id.id])],
#                         "packaging_id": pl.packaging_id.id,
#                         "box_qty": pl.box_qty,
#                         "packed_qty": pl.packed_qty,
#                         "total_units": pl.total_units,
#                         "net_weight": pl.net_weight,
#                         "gross_weight": pl.gross_weight,
#                         "cbm": pl.cbm,
#                     }))

#             batch.batch_packing_line_ids = lines


    


     # 🔥 MAIN METHOD
    # def _generate_batch_packing(self):
    #     for batch in self:
    #         # remove old lines safely
    #         batch.batch_packing_line_ids.unlink()

    #         grouped = {}
    #         case_counter = 1

    #         for picking in batch.picking_ids:
    #             for line in picking.packing_line_ids:
    #                 if not line.packaging_id:
    #                     continue

    #                 key = line.packaging_id.id

    #                 if key not in grouped:
    #                     grouped[key] = {
    #                         "packaging": line.packaging_id,
    #                         "products": set(),
    #                         "boxes": 0,
    #                         "units": 0,
    #                         "net": 0,
    #                         "gross": 0,
    #                         "cbm": 0,
    #                     }

    #                 g = grouped[key]
    #                 g["products"].add(line.product_id.id)
    #                 g["boxes"] += line.box_qty or 0
    #                 g["units"] += line.packed_qty or 0   # ✅ FIX
    #                 g["net"] += (line.net_weight or 0) * (line.box_qty or 0)
    #                 g["gross"] += (line.gross_weight or 0) * (line.box_qty or 0)
    #                 g["cbm"] += (line.cbm or 0) * (line.box_qty or 0)

    #         PackingLine = self.env["stock.picking.batch.packing.line"]

    #         for g in grouped.values():
    #             start = case_counter
    #             end = case_counter + g["boxes"] - 1

    #             PackingLine.create({
    #                 "batch_id": batch.id,
    #                 "packaging_id": g["packaging"].id,
    #                 "case_no_from": start,
    #                 "case_no_to": end,
    #                 "box_qty": g["boxes"],
    #                 "total_units": g["units"],
    #                 "net_weight": g["net"],
    #                 "gross_weight": g["gross"],
    #                 "cbm": g["cbm"],
    #                 "product_ids": [(6, 0, list(g["products"]))],
    #             })

    #             case_counter = end + 1


    # def write(self, vals):
    #     res = super().write(vals)

    #     if any(key.startswith("picking_ids") for key in vals):
    #         self._generate_batch_packing()

    #     return res  

    # @api.model
    # def create(self, vals):
    #     batch = super().create(vals)
    #     batch._generate_batch_packing()
    #     return batch


    # @api.model
    # def read(self, fields=None, load="_classic_read"):
    #     records = super().read(fields, load)
    #     self._generate_batch_packing()
    #     return records

    # def action_done(self):
    #     self._generate_batch_packing()
    #     return super().action_done()
    total_packages = fields.Integer(
        compute="_compute_batch_totals",
        store=True
    )
    net_weight = fields.Float(
        compute="_compute_batch_totals",
        store=True,
        digits=(16, 4)
    )
    gross_weight = fields.Float(
        compute="_compute_batch_totals",
        store=True,
        digits=(16, 4)
    )
    cbm_total = fields.Float(
        compute="_compute_batch_totals",
        store=True,
        digits=(16, 4)
    )

    buyer_order_no = fields.Text(
        compute="_compute_batch_buyer_order",
        store=True
    )

    @api.depends("picking_ids", "picking_ids.packing_line_ids")
    def _compute_batch_totals(self):
        for batch in self:
            pkgs = net = gross = cbm = 0.0

            for picking in batch.picking_ids:
                for line in picking.packing_line_ids:
                    qty = line.box_qty or 0
                    pkgs += qty
                    net += (line.net_weight or 0) * qty
                    gross += (line.gross_weight or 0) * qty
                    cbm += (line.cbm or 0) * qty

            batch.total_packages = int(pkgs)
            batch.net_weight = net
            batch.gross_weight = gross
            batch.cbm_total = cbm

    @api.depends("picking_ids.origin")
    def _compute_batch_buyer_order(self):
        for batch in self:
            result = []

            so_names = []
            for picking in batch.picking_ids:
                if picking.origin:
                    so_names += [x.strip() for x in picking.origin.split(",")]

            if so_names:
                sales = self.env["sale.order"].search([
                    ("name", "in", list(set(so_names)))
                ])

                for sale in sales:
                    if sale.buyer_order_no:
                        result.append(sale.buyer_order_no)

            batch.buyer_order_no = "\n".join(result) if result else False

