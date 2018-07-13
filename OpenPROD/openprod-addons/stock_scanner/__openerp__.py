# -*- coding: utf-8 -*-


{
    'name': 'Stock Scanner',
    'version': '1.0',
    'category': 'Generic Modules/Inventory Control',
    'license': 'LGPL',
    'description': """Allows managing barcode readers with simple scenarios
- You can define a workfow for each object (stock picking, inventory, sale, etc)
- Works with all scanner hardware model (just SSH client required)

The "sentinel" specific ncurses client, available in the "hardware" directory, requires the "openobject-library" python module, available from pip :
    $ sudo pip install openobject-library

Some demo/tutorial scenarios are available in the "demo" directory of the module.
To import these scenarios, you can use the import script located in the "scripts" directory.
""",
    'author': 'objectif-pi',
    'website': 'http://www.objectif-pi.com/',
    'images': [],
    'depends': [
        'stock',
    ],

    'data': [
        'security/ir.model.access.csv',
        'stock_scanner_view.xml',
    ],

    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
