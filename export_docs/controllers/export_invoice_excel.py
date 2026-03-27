from odoo import http
from odoo.http import request
import base64
import io
from PIL import Image
import xlsxwriter


class ExportDocsExcelController(http.Controller):

    @http.route("/export_docs/excel", type="http", auth="user", csrf=False)
    def export_excel(self, wizard_id=None, **kw):

        # =========================
        # FETCH WIZARD + INVOICE
        # =========================
        wiz = request.env["description.select.wizard"].sudo().browse(int(wizard_id))

        active_ids = kw.get("active_ids")
        if not active_ids:
            return request.not_found()

        active_ids = [int(i) for i in active_ids.split(",")]
        invoices = request.env["account.move"].sudo().browse(active_ids)
        if not invoices:
            return request.not_found()

        inv = invoices[0]

        company = inv.company_id
        cur = inv.currency_id
        comp_cur = company.currency_id

        rate = cur._get_conversion_rate(
            cur, comp_cur, company, inv.invoice_date or inv.date
        ) or 1.0

        def odoo_image_to_png(image_base64):
            if not image_base64:
                return None
            try:
                image_bytes = base64.b64decode(image_base64)
                img = Image.open(io.BytesIO(image_bytes))
                png_buffer = io.BytesIO()
                img.convert("RGBA").save(png_buffer, format="PNG")
                png_buffer.seek(0)
                return png_buffer
            except Exception:
                return None

        # =========================
        # GROUP BUYER ORDERS
        # =========================
        grouped = {}
        for l in inv.invoice_line_ids:
            if l.product_id and l.product_id.type != "service":
                bo = (
                    l.sale_line_ids
                    and l.sale_line_ids[0].order_id.buyer_order_no
                    or "NO BUYER ORDER"
                )
                grouped.setdefault(bo, []).append(l)

        # =========================
        # TOTALS
        # =========================
        freight = sum(inv.invoice_line_ids.filtered(
            lambda l: l.product_id and "freight" in (l.product_id.name or "").lower()
        ).mapped("price_subtotal"))

        insurance = sum(inv.invoice_line_ids.filtered(
            lambda l: l.product_id and "insurance" in (l.product_id.name or "").lower()
        ).mapped("price_subtotal"))

        discount = sum(
            (l.quantity * l.price_unit * l.discount) / 100
            for l in inv.invoice_line_ids
            if l.product_id and l.product_id.type != "service"
        )

        hsn_map = {}

        for l in inv.invoice_line_ids:
            if l.product_id and l.product_id.type != "service":
                hsn = l.product_id.l10n_in_hsn_code or "NA"
                gst = l.tax_ids and l.tax_ids[0].amount or 0
                taxable = l.price_subtotal * rate

                hsn_map.setdefault(hsn, {
                    "taxable": 0.0,
                    "rate": gst,
                    "tax": 0.0
                })

                hsn_map[hsn]["taxable"] += taxable
                hsn_map[hsn]["tax"] += taxable * gst / 100

        # =========================
        # CREATE EXCEL
        # =========================
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output)
        ws = wb.add_worksheet("Invoice")

        # =========================
        # FORMATS
        # =========================
        title = wb.add_format({"bold": True, "font_size": 15, "align": "center"})
        bold = wb.add_format({"bold": True})
        head = wb.add_format({"bold": True, "border": 1, "align": "center"})
        cell = wb.add_format({"border": 1})
        amt = wb.add_format({"border": 1, "align": "right"})
        wrap_box = wb.add_format({
            "border": 1,
            "text_wrap": True,
            "valign": "top",
            "align": "left"
        })

        box = wb.add_format({
        "border": 1,
        "text_wrap": True,
        "valign": "top",
        "align": "left"
        })

        box_center = wb.add_format({
        "border": 1,
        "text_wrap": True,
        "valign": "middle",
        "align": "center"
        })

       
        r = 0

        # =========================
        # TITLE
        # =========================
        ws.merge_range(
            r, 0, r, 9,
            "TAX INVOICE" if wiz.report_type == "tax" else "EXPORT INVOICE",
            title
        )
        r += 2

        buyer_orders = inv.invoice_line_ids.sale_line_ids.order_id.mapped("buyer_order_no")
        buyer_orders = [bo for bo in buyer_orders if bo]

       # =========================
        # EXPORTER + LOGO (SINGLE BLOCK, CLEAN)
        # =========================
        block_height = 4

        # LOGO (A)
        ws.merge_range(
            r, 0, r + block_height - 1, 0,
            "",
            wrap_box
        )

        # EXPORTER TEXT (B–D)
        ws.merge_range(
            r, 1, r + block_height - 1, 3,
            "Exporter\n"
            f"{company.name}\n"
            f"{company.street or ''}\n"
            f"{company.city or ''}\n"
            f"GSTIN : {company.vat or ''}",
            wrap_box
        )

        # INVOICE DETAILS (E–J)
        ws.merge_range(
            r, 4, r + block_height - 1, 9,
            f"Invoice No : {inv.name}\n"
            f"Date : {inv.invoice_date}\n"
            f"Buyer Order No : {', '.join(set(buyer_orders))}",
            wrap_box
        )

        # ROW HEIGHT
        for i in range(block_height):
            ws.set_row(r + i, 34)

        # LOGO INSERT (INSIDE A)
        logo_img = odoo_image_to_png(company.logo)
        if logo_img:
            ws.insert_image(
                r, 0,
                "company_logo.png",
                {
                    "image_data": logo_img,
                    "x_offset": 8,
                    "y_offset": 8,
                    "x_scale": 0.10,
                    "y_scale": 0.10,
                    "object_position": 1
                }
            )

        r += block_height
        # =========================
        # HELPER FOR 2-COLUMN BLOCK
        # =========================
        def two_col_block(r, left, right, height=4):
            ws.merge_range(r, 0, r + height - 1, 3, left, wrap_box)
            ws.merge_range(r, 4, r + height - 1, 9, right, wrap_box)

            for i in range(height):
                ws.set_row(r + i, 22)

            return r + height

        # =========================
        # CONSIGNEE / BUYER
        # =========================
        r = two_col_block(
            r,
            f"Consignee\n"
            f"{inv.consignee_id.name or ''}\n"
            f"{inv.consignee_id.street or ''}\n"
            f"{inv.consignee_id.city or ''}",
            f"Buyer (if other than consignee)\n"
            f"{inv.buyer_id.name or ''}"
        )

        # =========================
        # COUNTRY
        # =========================
        r = two_col_block(
            r,
            f"Country of Origin\n{inv.country_origin_id.name or ''}",
            f"Final Destination\n{inv.country_destination_id.name or ''}"
        )

        # =========================
        # SHIPPING
        # =========================
        r = two_col_block(
            r,
            f"Pre-Carriage By\n{inv.pre_carriage_by or ''}",
            f"Place of Receipt\n{inv.place_of_receipt or ''}"
        )

        r = two_col_block(
            r,
            f"Port of Loading\n{inv.port_loading or ''}",
            f"Port of Discharge\n{inv.port_discharge or ''}"
        )

        # =========================
        # TERMS
        # =========================
        r = two_col_block(
            r,
            f"Terms of Delivery & Payment\n"
            f"{inv.terms_delivery or ''} / {inv.payment_terms_export or ''}",
            ""
        )

        r += 2

        # =========================
        # ITEM TABLE
        # =========================
        headers = [
            "Sr", "Item Ref", "Description", "HSN",
            "Qty", "Rate",
            f"Amount ({cur.name})",
            f"Taxable ({comp_cur.name})",
            "GST %",
            f"GST Amt ({comp_cur.name})"
        ]

        for c, h in enumerate(headers):
            ws.write(r, c, h, head)
        r += 1

        sr = 1
        total_taxable = total_gst = 0.0

        for bo, lines in grouped.items():
            ws.merge_range(r, 0, r, 9, f"Buyer Order No : {bo}", bold)
            r += 1

            for l in lines:
                gst = l.tax_ids and l.tax_ids[0].amount or 0
                taxable = l.price_subtotal * rate
                gst_amt = taxable * gst / 100

                ws.write_row(r, 0, [
                    sr,
                    l.product_id.default_code or "",
                    l.name,
                    l.product_id.l10n_in_hsn_code or "",
                    l.quantity,
                    l.price_unit,
                    l.price_subtotal,
                    taxable,
                    gst,
                    gst_amt
                ], cell)

                total_taxable += taxable
                total_gst += gst_amt
                sr += 1
                r += 1

        ROWS_PER_PAGE = 18
        filled_rows = sr - 1

        if filled_rows < ROWS_PER_PAGE:
            for i in range(ROWS_PER_PAGE - filled_rows):
                for col in range(10):
                    ws.write(r, col, "", cell)
                r += 1


        # net_amount = sum(
        # l.price_subtotal
        # for l in inv.invoice_line_ids
        # if l.product_id and l.product_id.type != "service"
        # )

        # amount_words = cur.amount_to_text(round(net_amount, 2))

        
        # r += 2
        # ws.merge_range(
        #     r, 0, r+2, 5,
        #     f"Amount Chargeable (In Words)\n{cur.name} {amount_words} Only",
        #     wrap_box
        # )

        # =========================
        # TOTALS
        # =========================
        # r += 1
        # ws.merge_range(r, 6, r, 8, "DISCOUNT", bold); ws.write(r, 9, discount, amt); r += 1
        # ws.merge_range(r, 6, r, 8, "FREIGHT", bold); ws.write(r, 9, freight, amt); r += 1
        # ws.merge_range(r, 6, r, 8, "INSURANCE", bold); ws.write(r, 9, insurance, amt); r += 1
        # ws.merge_range(r, 6, r, 8, "GST TOTAL", bold); ws.write(r, 9, total_gst, amt); r += 1
        # ws.merge_range(r, 6, r, 8, "GRAND TOTAL", bold)
        # ws.write(r, 9, total_taxable + total_gst + freight + insurance - discount, amt)

        r += 4
        ws.merge_range(r, 0, r, 3, "HSN SUMMARY", bold)
        r += 1

        ws.write_row(r, 0, ["HSN Code", "Taxable Value", "GST %", "Tax Amount"], head)
        r += 1

        hsn_taxable_total = hsn_tax_total = 0.0

        for hsn, vals in hsn_map.items():
            ws.write_row(r, 0, [
                hsn,
                round(vals["taxable"], 2),
                vals["rate"],
                round(vals["tax"], 2)
            ], cell)

            hsn_taxable_total += vals["taxable"]
            hsn_tax_total += vals["tax"]
            r += 1

        ws.write_row(
            r, 0,
            ["TOTAL", round(hsn_taxable_total, 2), "", round(hsn_tax_total, 2)],
            bold
        )
        # =============================
        # EXCHANGE RATE
        # =============================
        r += 1
        ws.merge_range(
            r, 0, r, 9,
            f"Exchange Rate : 1 {cur.name} = {round(rate,4)} {comp_cur.name}",
            box_center
        )
        r += 2

        # =============================
        # AMOUNT IN WORDS + TOTALS
        # =============================
        ws.merge_range(
            r, 0, r+2, 5,
            "Amount Chargeable (In Words)\n"
            f"{cur.name} {cur.amount_to_text(inv.amount_total)} Only",
            box
        )

        # ws.merge_range(
        #     r, 6, r+2, 9,
        #     f"DISCOUNT : {discount}\n"
        #     f"FREIGHT : {freight}\n"
        #     f"INSURANCE : {insurance}\n"
        #     f"GST TOTAL : {round(total_gst,2)}\n"
        #     f"GRAND TOTAL : {round(total_taxable + total_gst + freight + insurance - discount,2)}",
        #     box
        # )
        r += 4

        # =============================
        # DECLARATION + SIGNATURE
        # =============================
        ws.merge_range(
            r, 0, r+3, 6,
            "DECLARATION:\n"
            "We declare that this invoice shows the actual price of the goods "
            "described and that all particulars are true and correct.",
            box
        )

        ws.merge_range(
            r, 7, r+3, 9,
            f"For {company.name}\n\nAuthorised Signatory",
            box_center
        )

        # # =========================
        # # AUTHORISED SIGNATORY
        # # =========================
        # user = request.env.user
        # sign_img = odoo_image_to_png(user.image_1920)

        # if sign_img:
        #     ws.insert_image(
        #         r + 2, 7, "sign.png",
        #         {
        #             "image_data": sign_img,
        #             "x_scale": 0.4,
        #             "y_scale": 0.4,
        #             "object_position": 1
        #         }
        #     )

        # ws.write(r + 6, 7, f"For {company.name}", bold)
        # ws.write(r + 7, 7, "Authorised Signatory", bold)

        # =========================
        # DOWNLOAD
        # =========================
        wb.close()
        output.seek(0)

        return request.make_response(
            output.read(),
            headers=[
                ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("Content-Disposition", 'attachment; filename="Tax_Invoice.xlsx"')
            ]
        )