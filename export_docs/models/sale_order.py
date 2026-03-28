from odoo import models, fields, api
from odoo.exceptions import UserError
import math


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # ---------------- EXPORT INFO ----------------
    exporter_reference = fields.Char("Exporter Reference")
    buyer_order_no = fields.Char("Buyer Order No")
    buyer_order_date = fields.Date("Buyer Order Date")
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

    # ---------------- PACKING SUMMARY ----------------
    total_packages = fields.Integer(
        compute="_compute_packing_summary",
        store=True,
    )
    net_weight = fields.Float(
        "Total Net Weight (Kg)",
        compute="_compute_packing_summary",
        store=True,
        digits=(16, 4),
    )
    gross_weight = fields.Float(
        "Total Gross Weight (Kg)",
        compute="_compute_packing_summary",
        store=True,
        digits=(16, 4),
    )
    cbm_total = fields.Float(
        "Total CBM",
        compute="_compute_packing_summary",
        store=True,
        digits=(16, 4),
    )

    packing_line_ids = fields.One2many(
        related="picking_ids.packing_line_ids", readonly=True
    )

    # 🔥 XML में USED FIELDS (MISSING BEFORE)
    packing_list_no = fields.Char("Packing List No.")
    packing_list_date = fields.Date("Packing List Date")
    marks_numbers = fields.Text("Marks & Numbers")
    package_type = fields.Char("Package Type")

    @api.depends("picking_ids", "picking_ids.state")
    def _compute_packing_summary(self):
        for order in self:
            total_pkgs = net = gross = cbm = 0.0

            pickings = order.picking_ids.filtered(
                lambda p: p.state == "done" and p.picking_type_id.code == "outgoing"
            )

            for picking in pickings:
                for line in picking.packing_line_ids:
                    qty = line.box_qty or 0
                    total_pkgs += qty
                    net += (line.net_weight or 0.0) * qty
                    gross += (line.gross_weight or 0.0) * qty
                    cbm += (line.cbm or 0.0) * qty

            order.total_packages = int(total_pkgs)
            order.net_weight = net
            order.gross_weight = gross
            order.cbm_total = cbm

    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super()._prepare_invoice()

        # ONLY logistics totals allowed here
        batch = self.picking_ids.mapped("batch_id")[:1]
        picking = self.picking_ids.filtered(
            lambda p: p.state == "done" and p.picking_type_id.code == "outgoing"
        )[:1]
        source = batch or picking

        invoice_vals.update({
            "exporter_reference": self.exporter_reference,
            "other_reference": self.other_reference,
            "consignee_id": self.consignee_id.id,
            "buyer_id": self.buyer_id.id,
            "notify_id": self.notify_id.id,
            "country_origin_id": self.country_origin_id.id,
            "country_destination_id": self.country_destination_id.id,
            "final_destination": self.final_destination,
            "pre_carriage_by": self.pre_carriage_by,
            "place_of_receipt": self.place_of_receipt,
            "port_loading": self.port_loading,
            "port_discharge": self.port_discharge,
            "vessel_no": self.vessel_no,
            "terms_delivery": self.terms_delivery,
            "payment_terms_export": self.payment_terms_export,
            "incentive_scheme": self.incentive_scheme,
            "dimension_uom": self.dimension_uom,
            "item_rate_uom": self.item_rate_uom,
            "issued_warehouse_id": self.issued_warehouse_id.id,
            "shipped": self.shipped,
            "marks_numbers": self.marks_numbers,
            "packing_list_no": self.packing_list_no,
            "packing_list_date": self.packing_list_date,
            "package_type": self.package_type,
        })

        if source:
            invoice_vals.update({
                "total_packages": source.total_packages,
                "net_weight": source.net_weight,
                "gross_weight": source.gross_weight,
                "cbm_total": source.cbm_total,
            })

        return invoice_vals


# =========================================================
# SALE ORDER LINE (PACKAGING DRIVEN – FIXED)
# =========================================================
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pkgs_from = fields.Integer("Pkgs From")
    pkgs_to = fields.Integer("Pkgs To")
    per_pkg_qty = fields.Float("Qty per Package")

    length = fields.Float("Length (cm)")
    width = fields.Float("Width (cm)")
    height = fields.Float("Height (cm)")

    empty_pkg_weight = fields.Float("Empty Package Weight (kg)", digits=(16, 4))

    net_wt_per_pkg = fields.Float(
        "Net Wt / Pkg (kg)", compute="_compute_weights", store=True, digits=(16, 4)
    )
    gross_wt_per_pkg = fields.Float(
        "Gross Wt / Pkg (kg)", compute="_compute_weights", store=True, digits=(16, 4)
    )

    item_weight = fields.Float(
        "Item Weight (kg)", compute="_compute_item_weight", store=True, digits=(16, 4)
    )

    cbm = fields.Float("CBM", compute="_compute_cbm", store=True, digits=(16, 4))
    show_in_invoice = fields.Boolean("Show in Invoice?", default=True)
    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({
            'show_in_invoice': self.show_in_invoice
        })
        return res

    # @api.onchange("product_id")
    # def _onchange_product_fill_from_packaging(self):
    #     if not self.product_id:
    #         return

    #     pkg = self.product_id.packaging_ids[:1]
    #     if not pkg:
    #         return

    #     self.per_pkg_qty = pkg.qty or 0.0
    #     self.length = pkg.x_box_length or 0.0
    #     self.width = pkg.x_box_width or 0.0
    #     self.height = pkg.x_box_height or 0.0

    #     self.net_wt_per_pkg = pkg.x_net_weight or 0.0
    #     self.gross_wt_per_pkg = pkg.x_gross_weight or 0.0
    #     self.cbm = pkg.x_cbm or 0.0

    # @api.onchange("product_uom_qty", "per_pkg_qty")
    # def _onchange_compute_package_range(self):
    #     for line in self:
    #         if line.product_uom_qty and line.per_pkg_qty:
    #             total_pkgs = math.ceil(
    #                 line.product_uom_qty / line.per_pkg_qty
    #             )
    #             line.pkgs_from = 1
    #             line.pkgs_to = total_pkgs
    #         else:
    #             line.pkgs_from = 0
    #             line.pkgs_to = 0

    # -------------------------------------------------
    # COPY FROM PRODUCT.PACKAGING
    # -------------------------------------------------
    # @api.onchange("product_packaging_id", "product_packaging_qty")
    # def _onchange_packaging(self):
    #     for line in self:
    #         pkg = line.product_packaging_id
    #         if not pkg:
    #             return

    #         line.length = pkg.x_box_length or 0.0
    #         line.width = pkg.x_box_width or 0.0
    #         line.height = pkg.x_box_height or 0.0
    #         line.per_pkg_qty = pkg.qty or 0.0

    #         if line.product_packaging_qty:
    #             line.pkgs_from = 1
    #             line.pkgs_to = int(line.product_packaging_qty)

    # -------------------------------------------------
    # NET & GROSS PER PACKAGE (FROM PACKAGING)
    # -------------------------------------------------
    @api.depends("product_packaging_id")
    def _compute_weights(self):
        for line in self:
            pkg = line.product_packaging_id
            if not pkg:
                line.net_wt_per_pkg = 0.0
                line.gross_wt_per_pkg = 0.0
                line.empty_pkg_weight = 0.0
                continue

            line.net_wt_per_pkg = pkg.x_net_weight or 0.0
            line.gross_wt_per_pkg = pkg.x_gross_weight or 0.0
            line.empty_pkg_weight = line.gross_wt_per_pkg - line.net_wt_per_pkg

    # -------------------------------------------------
    # ITEM WEIGHT = NET PER PKG × NO OF PACKAGES ✅
    # -------------------------------------------------
    @api.depends("net_wt_per_pkg", "pkgs_from", "pkgs_to")
    def _compute_item_weight(self):
        for line in self:
            count = 0
            if line.pkgs_from and line.pkgs_to:
                count = line.pkgs_to - line.pkgs_from + 1
            line.item_weight = (line.net_wt_per_pkg or 0.0) * count

    # -------------------------------------------------
    # CBM
    # -------------------------------------------------
    @api.depends("length", "width", "height", "pkgs_from", "pkgs_to")
    def _compute_cbm(self):
        for line in self:
            if (
                line.length
                and line.width
                and line.height
                and line.pkgs_from
                and line.pkgs_to
            ):
                count = line.pkgs_to - line.pkgs_from + 1
                per = (line.length * line.width * line.height) / 1_000_000
                line.cbm = per * count
            else:
                line.cbm = 0.0


# =========================================================
# ACCOUNT MOVE (INVOICE)
# =========================================================
class AccountMove(models.Model):
    _inherit = "account.move"

    exporter_reference = fields.Char("Exporter Reference", readonly=True)
    buyer_order_no = fields.Char("Buyer Order No", readonly=True)
    buyer_order_date = fields.Date("Buyer Order Date", readonly=True)
    other_reference = fields.Char("Other Reference", readonly=True)

    consignee_id = fields.Many2one("res.partner", string="Consignee", readonly=True)
    buyer_id = fields.Many2one(
        "res.partner", string="Buyer (Other than Consignee)", readonly=True
    )
    notify_id = fields.Many2one("res.partner", string="Notify Party", readonly=True)

    country_origin_id = fields.Many2one("res.country", readonly=True)
    country_destination_id = fields.Many2one("res.country", readonly=True)
    final_destination = fields.Char()

    pre_carriage_by = fields.Char(readonly=True)
    place_of_receipt = fields.Char(readonly=True)
    port_loading = fields.Char(readonly=True)
    port_discharge = fields.Char(readonly=True)
    vessel_no = fields.Char(readonly=True)

    terms_delivery = fields.Char(readonly=True)
    payment_terms_export = fields.Char(readonly=True)

    incentive_scheme = fields.Selection(
        [("dbk", "DBK"), ("adv_lic", "Advance Licence"), ("others", "Others")],
        readonly=True,
    )

    dimension_uom = fields.Selection(
        [("inch", "Inch"), ("cm", "Centimeter")], readonly=True
    )
    item_rate_uom = fields.Selection(
        [("pcs", "PCS"), ("sqmt", "SQMT"), ("sqft", "SQFT")], readonly=True
    )

    issued_warehouse_id = fields.Many2one("stock.warehouse", readonly=True)
    shipped = fields.Boolean()

    total_packages = fields.Integer(readonly=True)
    net_weight = fields.Float(digits=(16, 4), readonly=True)
    gross_weight = fields.Float(digits=(16, 4), readonly=True)
    cbm_total = fields.Float(digits=(16, 4), readonly=True)

    marks_numbers = fields.Text(readonly=True)
    packing_list_no = fields.Char(readonly=True)
    packing_list_date = fields.Date(readonly=True)
    package_type = fields.Char(readonly=True)

    freight_usd = fields.Monetary(
        string="Freight USD", currency_field="currency_id", default=0.0, readonly=True
    )

    insurance_usd = fields.Monetary(
        string="Insurance USD", currency_field="currency_id", default=0.0, readonly=True
    )

    discount_usd = fields.Monetary(
        string="Discount USD", currency_field="currency_id", default=0.0, readonly=True
    )

    def _post(self, soft=True):
        res = super()._post(soft)
    
        for move in self:
            for line in move.invoice_line_ids:
                if line.sale_line_ids:
                    line.show_in_invoice = line.sale_line_ids[0].show_in_invoice
    
        return res

    @api.model
    def create(self, vals):
        move = super(
            AccountMove,
            self.with_context(skip_export_lock=True)
        ).create(vals)

        if move.move_type == "out_invoice":
            sale_orders = move.invoice_line_ids.mapped(
                "sale_line_ids.order_id"
            )

            buyer_orders = [
                so.buyer_order_no
                for so in sale_orders
                if so.buyer_order_no
            ]

            if buyer_orders:
                move.with_context(skip_export_lock=True).write({
                    "buyer_order_no": " ".join(sorted(set(buyer_orders))),
                    "buyer_order_date": sale_orders[:1].buyer_order_date,
                })

        return move

    def action_print_tax_invoice(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Select Description",
            "res_model": "description.select.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "account.move",
                "active_ids": self.ids,
                "report_type": "tax",
            },
        }

    def action_print_export_invoice(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Select Description",
            "res_model": "description.select.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "account.move",
                "active_ids": self.ids,
                "report_type": "export",
            },
        }

    def action_print_packing_list(self):
        self.ensure_one()

        sales = self.invoice_line_ids.mapped("sale_line_ids.order_id")
        sale = sales[:1] if sales else False

        if not sale:
            raise UserError("This invoice is not linked to any Sales Order.")

        picking = sale.picking_ids.filtered(
            lambda p: p.state == "done" and p.picking_type_id.code == "outgoing"
        )[:1]

        if not picking:
            raise UserError("No completed delivery found for this Sales Order.")

        return self.env.ref("export_docs.action_packing_list").report_action(picking)

    def action_open_export_print_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Select Description",
            "res_model": "description.select.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "account.move",
                "active_ids": self.ids,
                "report_type": "export",
            },
        }

    def write(self, vals):
        protected_fields = {
            "exporter_reference",
            "buyer_order_no",
            "buyer_order_date",
            "other_reference",
            "consignee_id",
            "buyer_id",
            "notify_id",
            "country_origin_id",
            "country_destination_id",
            "final_destination",
            "pre_carriage_by",
            "place_of_receipt",
            "port_loading",
            "port_discharge",
            "vessel_no",
            "terms_delivery",
            "payment_terms_export",
            "incentive_scheme",
            "dimension_uom",
            "item_rate_uom",
            "issued_warehouse_id",
            "shipped",
            "total_packages",
            "net_weight",
            "gross_weight",
            "cbm_total",
            "marks_numbers",
            "packing_list_no",
            "packing_list_date",
            "package_type",
        }

        for move in self:
            from_sale = any(line.sale_line_ids for line in move.invoice_line_ids)

            # 🔥 allow system writes during invoice creation
            if self.env.context.get("skip_export_lock"):
                continue

            if (
                move.move_type == "out_invoice"
                and from_sale
                and move.state == "draft"
                and protected_fields.intersection(vals)
            ):
                raise UserError(
                    "This invoice was created from a Sale Order.\n"
                    "Export information cannot be modified."
                )

        return super().write(vals)

    def _group_lines_by_buyer_order(self, invoice):
        grouped = {}

        for line in invoice.invoice_line_ids.filtered(lambda l: not l.display_type):
            sale = line.sale_line_ids[:1].order_id if line.sale_line_ids else False
            buyer_no = sale.buyer_order_no if sale else "N/A"

            grouped.setdefault(buyer_no, [])
            grouped[buyer_no].append(line)

        return grouped
    
    def get_export_hsn_summary(self):
        summary = {}

        for line in self.invoice_line_ids:
            # ❌ SERVICE SKIP
            if not line.product_id or line.product_id.type == 'service':
                continue

            hsn = line.product_id.l10n_in_hsn_code or 'NA'
            rate = line.tax_ids[:1].amount if line.tax_ids else 0.0
            taxable = line.price_subtotal

            if hsn not in summary:
                summary[hsn] = {
                    'hsn': hsn,
                    'taxable': 0.0,
                    'rate': rate,
                    'tax': 0.0,
                }

            summary[hsn]['taxable'] += taxable
            summary[hsn]['tax'] += taxable * rate / 100

        return list(summary.values())



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    company_currency_id = fields.Many2one(related="company_id.currency_id", store=True)

    usd_amount = fields.Monetary(
        string="Amount USD",
        currency_field="currency_id",
        compute="_compute_usd_amount",
        store=True,
    )

    taxable_inr = fields.Monetary(
        string="Taxable INR",
        currency_field="company_currency_id",
        compute="_compute_taxable_inr",
        store=True,
    )

    freight_usd = fields.Monetary(string="Freight USD", currency_field="currency_id")

    insurance_usd = fields.Monetary(
        string="Insurance USD", currency_field="currency_id"
    )

    discount_usd = fields.Monetary(string="Discount USD", currency_field="currency_id")
    show_in_invoice= fields.Boolean("Show in Invoice Print?", default=True)

    


class ExportInvoiceReport(models.AbstractModel):
    _name = "report.export_docs.export_invoice_template"

    def _group_lines_by_buyer_order(self, invoice):
        grouped = {}
        for line in invoice.invoice_line_ids:
            if not line.product_id or line.product_id.type == 'service':
                continue

            bo = (
                line.sale_line_ids
                and line.sale_line_ids[0].order_id.buyer_order_no
                or 'NO BUYER ORDER'
            )

            grouped.setdefault(bo, []).append(line)

        return grouped


    def _get_report_values(self, docids, data=None):
        docs = self.env["account.move"].browse(docids)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'account.move',
            'docs': docs,
            'grouped_lines': {
                inv.id: self._group_lines_by_buyer_order(inv)
                for inv in docs
        }
}


class TaxInvoiceReport(models.AbstractModel):
    _name = "report.export_docs.tax_invoice_template"

    def _group_lines_by_buyer_order(self, invoice):
        grouped = {}
        for line in invoice.invoice_line_ids:
            if not line.product_id or line.product_id.type == 'service':
                continue

            bo = (
                line.sale_line_ids
                and line.sale_line_ids[0].order_id.buyer_order_no
                or 'NO BUYER ORDER'
            )

            grouped.setdefault(bo, []).append(line)

        return grouped


    def _get_report_values(self, docids, data=None):
        docs = self.env["account.move"].browse(docids)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'account.move',
            'docs': docs,
            'grouped_lines': {
                inv.id: self._group_lines_by_buyer_order(inv)
                for inv in docs
        }
}



class PackingListBatchReport(models.AbstractModel):
    _name = "report.export_docs.packing_list_batch_template"
    _description = "Batch Packing List Report"

    def _group_batch_lines_by_buyer_order(self, batch):
        grouped = {}

        for line in batch.batch_packing_line_ids:
            picking = line.picking_id
            move = picking.move_ids_without_package.filtered(
                lambda m: m.product_id in line.product_ids
            )[:1]

            sale = move.sale_line_id.order_id if move and move.sale_line_id else False
            buyer_no = sale.buyer_order_no if sale else "N/A"

            grouped.setdefault(buyer_no, [])
            grouped[buyer_no].append(line)

        return grouped


    def _get_report_values(self, docids, data=None):
        batches = self.env["stock.picking.batch"].browse(docids)

        return {
            "doc_ids": docids,
            "doc_model": "stock.picking.batch",
            "docs": batches,
            "grouped_batch_lines": {
                batch.id: self._group_batch_lines_by_buyer_order(batch)
                for batch in batches
            },
        }


    
