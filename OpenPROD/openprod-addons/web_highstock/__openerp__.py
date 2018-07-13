{
    'name': 'HighStock Graph',
    'version': '0.0.1',
    'sequence': 150,
    'category': 'Custom',
    'description': """
    """,
    'author': 'Objectif-PI',
    'license': 'Open-prod license',
    'website': 'http://www.objectif-pi.fr',
    'depends': [
        'web',
    ],
    'data' : [
        'web_highstock.xml',
    ],
    'qweb' : [
        'static/src/xml/highstock.xml',
    ],
    'installable': True,
    'auto_install': True,
}
