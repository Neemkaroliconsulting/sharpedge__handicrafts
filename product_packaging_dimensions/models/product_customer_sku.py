from odoo import models, fields

class ProductCustomerSKU(models.Model):
    _name = 'product.customer.sku'
    _description = 'Product Customer Wise SKU'
    _rec_name = 'customer_id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string="Product",
        ondelete='cascade',
        required=True
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

    _sql_constraints = [
        ('uniq_product_customer',
         'unique(product_tmpl_id, customer_id)',
         'Same customer SKU already exists for this product!')
    ]
