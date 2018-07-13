# coding: utf-8

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker, relationship, joinedload

#######
# nouveau controller (http)
# le controlleur fait un get_alchemy(model), un read, et retourne ça

engine = create_engine('postgresql+psycopg2://openerp:admin@localhost:5432/ope?client_encoding=\'utf-8\'', echo=True)
metadata = MetaData()

product_table = Table('product_product', metadata,
                      Column('id', primary_key=True),
                      Column('name'),
                      )

of_table = Table('mrp_manufacturingorder', metadata,
                      Column('id', Integer, primary_key=True),
                      Column('name'),
                      Column('quantity'),
                      Column('state'),
                      Column('product_id', Integer, ForeignKey('product_product.id'))
                      )


class mrp_manufacturingorder(object):
    def init(self, name, quantity, state):
        self.name = name
        self.quantity = quantity
        self.state = state
    
    def __unicode__(self):
        return str(u'%s, %s, %s' % (self.name, self.quantity, self.state))
    
mapper(mrp_manufacturingorder, of_table)
    
class Product(object):
    def init(self, name):
        self.name = name
    def __unicode__(self):
        return u'Product "%s" with MO [[ %s ]]' % (self.name, u" | ".join([unicode(x) for x in self.mo_ids]))

mapper(Product, product_table, properties={
                                           'mo_ids':relationship(mrp_manufacturingorder, backref='product', lazy='joined'),
                                           })

Session = sessionmaker(bind=engine)
session=Session()

for prod in session.query(Product).all():
    print unicode(prod)

