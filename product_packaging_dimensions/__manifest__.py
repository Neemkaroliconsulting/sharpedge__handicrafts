{
    'name': 'Product & Packaging Dimensions',
    'version': '18.0.1.0.0',
    'summary': 'Custom product customer SKU',
    'author': 'Neemkaroli Consulting',
    'website': 'https://neemkaroliconsulting.com',
    'license': 'LGPL-3',
    'depends': ['product','sale','uom',"stock",'stock_picking_batch', 'account'],
    'data': [
        'views/product_template_views.xml',
        'views/sale_order_view.xml',
        'views/product_packaging_views.xml',
        'wizard/description_select_wizard_view.xml',
        'wizard/description_select_wizard_action.xml',
        'security/ir.model.access.csv',
        # 'views/account_move_view.xml',
    
 
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
