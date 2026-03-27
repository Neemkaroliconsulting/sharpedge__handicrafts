from odoo import models, fields, api
from odoo.exceptions import ValidationError
import math


class StockPickingPackingLine(models.Model):
    _name = "stock.picking.packing.line"
    _description = "Delivery Packing Line"
   

    picking_id = fields.Many2one("stock.picking", ondelete="cascade")

    product_id = fields.Many2one(
    "product.product",
    required=True,
    domain="[('id', 'in', allowed_product_ids)]"
)
    
    allowed_product_ids = fields.Many2many(
    "product.product",
    compute="_compute_allowed_products",
    store=False
)
    @api.depends("picking_id")
    def _compute_allowed_products(self):
        for line in self:
            if line.picking_id:
                products = line.picking_id.move_ids_without_package.mapped("product_id")
                line.allowed_product_ids = products
            else:
                line.allowed_product_ids = False

    @api.constrains("product_id", "picking_id")
    def _check_product_allowed(self):
        for line in self:
            if line.product_id not in line.picking_id.move_ids_without_package.mapped("product_id"):
                raise ValidationError(
                    "You can only select products present in the Delivery Order."
                )

    packaging_id = fields.Many2one("product.packaging")

    pcs_per_box = fields.Float("PCS / Box")

    box_qty = fields.Integer(
        "Boxes", compute="_compute_boxes", inverse="_inverse_boxes", store=True
    )
    packed_qty = fields.Float(
    "Packed Qty",
    compute="_compute_packed_qty",
    store=True,
)

    total_units = fields.Float(
        "Total Units", compute="_compute_total_units", store=True
    )
    case_no_from = fields.Integer(
        string="Case No From"
    )
    case_no_to = fields.Integer(
        string="Case No To"
    )

    length = fields.Float()
    width = fields.Float()
    height = fields.Float()

    net_weight = fields.Float()
    gross_weight = fields.Float()
    cbm = fields.Float()

    @api.depends("box_qty", "pcs_per_box")
    def _compute_packed_qty(self):
        for line in self:
            packed = (line.box_qty or 0) * (line.pcs_per_box or 0)
            line.packed_qty = packed
            line.total_units = packed

    # -------------------------------
    # COMPUTE BOXES
    # -------------------------------
    @api.depends("total_units", "pcs_per_box")
    def _compute_boxes(self):
        for line in self:
            if line.pcs_per_box:
                line.box_qty = math.ceil(line.total_units / line.pcs_per_box)
            else:
                line.box_qty = 0

    # -------------------------------
    # INVERSE (ALLOW MANUAL EDIT)
    # -------------------------------
    def _inverse_boxes(self):
        for line in self:
            if line.box_qty and line.pcs_per_box:
                line.total_units = line.box_qty * line.pcs_per_box

    # -------------------------------
    # TOTAL UNITS
    # -------------------------------
    @api.depends("box_qty", "pcs_per_box")
    def _compute_total_units(self):
        for line in self:
            line.total_units = (line.box_qty or 0) * (line.pcs_per_box or 0)

    
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        for picking in lines.mapped("picking_id"):
            picking._assign_case_numbers()

        return lines
    
    @api.onchange('box_qty')
    def _onchange_box_qty_update_case(self):
        if self.picking_id:
            self.picking_id._assign_case_numbers()

    
    state = fields.Selection(
    related='picking_id.state',
    store=True,
    readonly=True
)



class StockPicking(models.Model):
    _inherit = "stock.picking"

    packing_line_ids = fields.One2many("stock.picking.packing.line", "picking_id")
    total_packed_qty = fields.Float(
        "Total Packed Qty", compute="_compute_packing_totals", store=True
    )
    picking_id = fields.Many2one("stock.picking", ondelete="cascade")

    product_id = fields.Many2one("product.product", required=True)
    packaging_id = fields.Many2one("product.packaging")

    pcs_per_box = fields.Float("PCS / Box")
    box_qty = fields.Integer("Boxes")

    length = fields.Float()
    width = fields.Float()
    height = fields.Float()

    net_weight = fields.Float()
    gross_weight = fields.Float()
    cbm = fields.Float()
    total_units = fields.Float()

    total_packages = fields.Integer(compute="_compute_packing_totals", store=True)
    net_weight = fields.Float(compute="_compute_packing_totals", store=True)
    gross_weight = fields.Float(compute="_compute_packing_totals", store=True)
    cbm_total = fields.Float(compute="_compute_packing_totals", store=True)


    exporter_reference = fields.Char("Exporter Reference")
    buyer_order_no = fields.Char("Buyer Order No")
    buyer_order_no = fields.Text(
    "Buyer Order No",
    compute="_compute_buyer_order_no",
    store=True,
    readonly=True
)
    other_reference = fields.Char("Other Reference")

    consignee_id = fields.Many2one("res.partner", string="Consignee")
    buyer_id = fields.Many2one("res.partner", string="Buyer (Other than Consignee)")
    notify_id = fields.Many2one("res.partner", string="Notify Party")

    country_origin_id = fields.Many2one(
        "res.country", string="Country of Origin of Goods"
    )
    country_destination_id = fields.Many2one(
        "res.country", string="Country of Final Destination"
    )
    final_destination = fields.Char("Final Destination / Place of Delivery")

    pre_carriage_by = fields.Char("Pre-Carriage By")
    place_of_receipt = fields.Char("Place of Receipt of Pre-Carrier")
    port_loading = fields.Char("Port of Loading")
    port_discharge = fields.Char("Port of Discharge")
    vessel_no = fields.Char("Vessel / Flight No.")

    terms_delivery = fields.Char("Terms of Delivery")
    payment_terms_export = fields.Char("Payment Term (Export)")

    incentive_scheme = fields.Selection(
        [
            ("dbk", "DBK"),
            ("adv_lic", "Advance Licence"),
            ("others", "Others"),
        ],
        string="Incentive Scheme",
    )

    dimension_uom = fields.Selection(
        [("inch", "Inch"), ("cm", "Centimeter")],
        default="cm",
    )
    item_rate_uom = fields.Selection(
        [("pcs", "PCS"), ("sqmt", "SQMT"), ("sqft", "SQFT")],
        default="pcs",
    )

    issued_warehouse_id = fields.Many2one("stock.warehouse")
    shipped = fields.Boolean("Shipped?")

    

   
    @api.depends(
    "packing_line_ids.box_qty",
    "packing_line_ids.packed_qty",
    "packing_line_ids.net_weight",
    "packing_line_ids.gross_weight",
    "packing_line_ids.cbm",
)
    def _compute_packing_totals(self):
        for picking in self:
            boxes = packed = net = gross = cbm = 0.0

            for line in picking.packing_line_ids:
                boxes += line.box_qty or 0
                packed += line.packed_qty or 0
                net += (line.net_weight or 0) * (line.box_qty or 0)
                gross += (line.gross_weight or 0) * (line.box_qty or 0)
                cbm += (line.cbm or 0) * (line.box_qty or 0)

            picking.total_packages = boxes
            picking.total_packed_qty = packed
            picking.net_weight = net
            picking.gross_weight = gross
            picking.cbm_total = cbm

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            sale = picking.sale_id
            if sale:
                picking.write({
                    "exporter_reference": sale.exporter_reference,
                    "buyer_order_no": sale.buyer_order_no,
                    "buyer_order_date": sale.buyer_order_date,
                    "other_reference": sale.other_reference,
                    "consignee_id": sale.consignee_id.id,
                    "buyer_id": sale.buyer_id.id,
                    "notify_id": sale.notify_id.id,
                    "country_origin_id": sale.country_origin_id.id,
                    "country_destination_id": sale.country_destination_id.id,
                    "final_destination": sale.final_destination,
                    "pre_carriage_by": sale.pre_carriage_by,
                    "place_of_receipt": sale.place_of_receipt,
                    "port_loading": sale.port_loading,
                    "port_discharge": sale.port_discharge,
                    "terms_delivery": sale.terms_delivery,
                    "payment_terms_export": sale.payment_terms_export,
                })
        return pickings
    

    invoice_id = fields.Many2one(
        'account.move',
        compute='_compute_invoice_id',
        store=False
    )

    def _compute_invoice_id(self):
        for picking in self:
            invoice = False
            sale = picking.sale_id
            if sale:
                invoice = self.env['account.move'].search([
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('invoice_line_ids.sale_line_ids.order_id', '=', sale.id)
                ], limit=1)
            picking.invoice_id = invoice


    # @api.onchange("move_ids_without_package")
    # def _onchange_copy_packaging(self):
    #     for picking in self:
    #         commands = [(5, 0, 0)]

    #         for move in picking.move_ids_without_package:
    #             delivery_qty = move.product_uom_qty
    #             product = move.product_id
    #             pkgs = product.packaging_ids

    #             remaining = delivery_qty

    #             for pkg in pkgs:
    #                 if not remaining:
    #                     break

    #                 pcs = pkg.qty or 1
    #                 boxes = math.floor(remaining / pcs)
    #                 packed = boxes * pcs

    #                 if packed == 0:
    #                     continue

    #                 commands.append((0, 0, {
    #                     "product_id": product.id,
    #                     "packaging_id": pkg.id,
    #                     "pcs_per_box": pcs,
    #                     "box_qty": boxes,
    #                     "packed_qty": boxes * pkg.qty, 
    #                     "length": pkg.x_box_length,
    #                     "width": pkg.x_box_width,
    #                     "height": pkg.x_box_height,
    #                     "net_weight": pkg.x_net_weight,
    #                     "gross_weight": pkg.x_gross_weight,
    #                     "cbm": pkg.x_cbm,
    #                 }))

    #                 remaining -= packed

    #         picking.packing_line_ids = commands

    
    # @api.model
    # def create(self, vals):
    #     picking = super().create(vals)
    #     picking._sync_packing_from_moves()
    #     return picking

    # def write(self, vals):
    #     res = super().write(vals)
    #     if "move_ids_without_package" in vals:
    #      self._sync_packing_from_moves()
    #     return res

    # def _create_packing_lines(self):
    #     for picking in self:
    #         if not picking.move_ids_without_package:
    #             continue

    #         picking.packing_line_ids.unlink()

    #         lines = []
    #         for move in picking.move_ids_without_package:
    #             qty = move.product_uom_qty
    #             product = move.product_id

    #             for pkg in product.packaging_ids:
    #                 boxes = math.ceil(qty / pkg.qty)

    #                 lines.append((0, 0, {
    #                     "product_id": product.id,
    #                     "packaging_id": pkg.id,
    #                     "pcs_per_box": pkg.qty,
    #                     "box_qty": boxes,
    #                     "length": pkg.x_box_length,
    #                     "width": pkg.x_box_width,
    #                     "height": pkg.x_box_height,
    #                     "net_weight": pkg.x_net_weight,
    #                     "gross_weight": pkg.x_gross_weight,
    #                     "cbm": pkg.x_cbm,
    #                 }))

    #         picking.packing_line_ids = lines


    # @api.model
    # def create(self, vals):
    #     picking = super().create(vals)
    #     picking._create_packing_lines()
    #     return picking

    # def write(self, vals):
    #     res = super().write(vals)
    #     if "move_ids_without_package" in vals:
    #         self._create_packing_lines()
    #     return res


    # def _sync_packing_from_moves(self):
    #     for picking in self:
    #         if picking.picking_type_id.code != "outgoing":
    #             continue

    #         picking.packing_line_ids.unlink()

    #         for move in picking.move_ids_without_package:
    #             delivered_qty = move.quantity_done
    #             if not delivered_qty:
    #                 continue

    #             product = move.product_id
    #             remaining = delivered_qty

    #             for pkg in product.packaging_ids:
    #                 if not remaining:
    #                     break

    #                 pcs = pkg.qty or 1
    #                 boxes = math.floor(remaining / pcs)
    #                 if not boxes:
    #                     continue

    #                 picking.packing_line_ids.create({
    #                     "picking_id": picking.id,
    #                     "product_id": product.id,
    #                     "packaging_id": pkg.id,
    #                     "pcs_per_box": pcs,
    #                     "box_qty": boxes,
    #                     "length": pkg.x_box_length,
    #                     "width": pkg.x_box_width,
    #                     "height": pkg.x_box_height,
    #                     "net_weight": pkg.x_net_weight,
    #                     "gross_weight": pkg.x_gross_weight,
    #                     "cbm": pkg.x_cbm,
    #                 })

    #                 remaining -= boxes * pcs


    # def button_validate(self):
    #     for picking in self:
    #         picking._sync_packing_from_moves()
    #     return super().button_validate()


    # def button_validate(self):
    #         for picking in self:

    #             # 🔥 ONLY FOR DELIVERY ORDERS
    #             if picking.picking_type_id.code != "outgoing":
    #                 continue

    #             for move in picking.move_ids_without_package:
    #                 delivered_qty = move.product_uom_qty

    #                 packed_qty = sum(
    #                     picking.packing_line_ids.filtered(
    #                         lambda l: l.product_id == move.product_id
    #                     ).mapped("packed_qty")
    #                 )

    #                 if not math.isclose(delivered_qty, packed_qty, rel_tol=0.0001):
    #                     raise ValidationError(
    #                         f"Packed Qty ({packed_qty}) does not match "
    #                         f"Delivery Qty ({delivered_qty}) "
    #                         f"for product {move.product_id.display_name}"
    #                     )

    #         return super().button_validate()


    def _recompute_packing_from_qty(self, use_done_qty=False):
        for picking in self:
            if picking.packing_line_ids:
                return

            lines = []

            for move in picking.move_ids_without_package:
                qty = move.product_uom_qty or 0
                if qty <= 0:
                    continue

                product = move.product_id

                packagings = product.product_tmpl_id.packaging_ids.sorted(
                    lambda p: p.qty or 0,
                    reverse=True
                )

                for pkg in packagings:
                    pcs = pkg.qty or 1

                    boxes = math.ceil(qty / pcs)
                    packed = boxes * pcs

                    lines.append((0, 0, {
                        "product_id": product.id,
                        "packaging_id": pkg.id,
                        "pcs_per_box": pcs,
                        "box_qty": boxes,
                        "packed_qty": packed,
                        "total_units": packed,
                        "length": pkg.x_box_length or 0.0,
                        "width": pkg.x_box_width or 0.0,
                        "height": pkg.x_box_height or 0.0,
                        "net_weight": pkg.x_net_weight or 0.0,
                        "gross_weight": pkg.x_gross_weight or 0.0,
                        "cbm": pkg.x_cbm or 0.0,
                    }))

            picking.packing_line_ids = lines



    def action_confirm(self):
        res = super().action_confirm()

        for picking in self:
            if (
                picking.picking_type_id.code == "outgoing"
                and not picking.packing_line_ids
            ):
                picking._recompute_packing_from_qty(use_done_qty=False)

        return res



    # @api.model_create_multi
    # def create(self, vals_list):
    #     pickings = super().create(vals_list)
    #     for picking in pickings:
    #         if picking.picking_type_id.code == "outgoing":
    #             picking._recompute_packing_from_qty(False)
    #     return pickings
    
    # def write(self, vals):
    #     res = super().write(vals)

    #     if "move_ids_without_package" in vals:
    #         for picking in self:
    #             if picking.picking_type_id.code == "outgoing":
    #                 picking._recompute_packing_from_qty()

    #     return res

    def button_validate(self):
        for picking in self:
            if picking.picking_type_id.code == "outgoing":
                picking._recompute_packing_from_qty(use_done_qty=True)

        return super().button_validate()


    # @api.model
    # def create(self, vals):
    #     picking = super().create(vals)
    #     picking._recompute_packing_from_moves()
    #     return picking
    
    # def write(self, vals):
    #     res = super().write(vals)
    #     if "move_ids_without_package" in vals:
    #         self._recompute_packing_from_moves()
    #     return res


    # @api.onchange("move_ids_without_package", "move_ids_without_package.product_uom_qty")
    # def _onchange_autofill_packing(self):
    #     for picking in self:
    #         if picking.picking_type_id.code != "outgoing":
    #             continue

    #         picking._recompute_packing_from_moves()


# class StockMove(models.Model):
#     _inherit = "stock.move"

#     def write(self, vals):
#         res = super().write(vals)

#         # 🔥 Jab system quantity set kare
#         if "product_uom_qty" in vals:
#             for move in self:
#                 picking = move.picking_id
#                 if (
#                     picking
#                     and picking.picking_type_id.code == "outgoing"
#                     and move.product_uom_qty > 0
#                 ):
#                     picking._recompute_packing_from_moves()

#         return res

    def write(self, vals):
        old_batches = self.mapped("batch_id")

        res = super().write(vals)

        # batch add OR remove
        if "batch_id" in vals:
            batches = (old_batches | self.mapped("batch_id")).filtered(lambda b: b)
            if batches:
                batches._sync_batch_packing()

        return res
    
    def _assign_case_numbers(self):
        for picking in self:
            case_no = 1

            for line in picking.packing_line_ids:
                if line.box_qty:
                    line.case_no_from = case_no
                    line.case_no_to = case_no + line.box_qty - 1
                    case_no = line.case_no_to + 1
                else:
                    line.case_no_from = 0
                    line.case_no_to = 0


    
    @api.depends("origin")
    def _compute_buyer_order_no(self):
        for picking in self:
            buyer_orders = []

            if picking.origin:
                
                so_names = [x.strip() for x in picking.origin.split(",")]

                sale_orders = self.env["sale.order"].search([
                    ("name", "in", so_names)
                ])

                for sale in sale_orders:
                    if sale.buyer_order_no:
                        buyer_orders.append(sale.buyer_order_no)

        
            picking.buyer_order_no = "\n".join(buyer_orders) if buyer_orders else False

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            sale = picking.sale_id
            if sale:
                picking.write({
                    "buyer_order_no": sale.buyer_order_no,
                })
        return pickings
  
