# coding: utf-8

from sqlalchemy import create_engine, Column, Text, Boolean, Numeric, Integer, String, Date, DateTime, Float, ForeignKey, exc
from sqlalchemy.orm import sessionmaker, relationship, foreign, remote
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from collections import defaultdict
import openerp
import warnings

# classe qui gère un singleton de connexion à la bdd
# a aussi le MetaData
# idem sessionmaker
# a un defaultdict de mapping vers les tables/modèles
conf = openerp.tools.config
engine = create_engine(
                       'postgresql+psycopg2://{}:{}@{}:5432/{}?client_encoding=\'utf-8\''.format(
                                                                                                 conf['db_user'],
                                                                                                 conf['db_password'],
                                                                                                 conf['db_host'],
                                                                                                 conf['db_name']
                                                                                                ),
                       echo=True
                    )

type_map = {
            'integer':Integer,
            'char':String,
            'boolean':Boolean,
            'text':Text,
            'html':Text,
            'float':Float,
            'monetary':Numeric,
            'date':Date,
            'datetime':DateTime,
            'selection': String,
            }

def show_object(self):
    return " | ".join([c.name + " : " + unicode(getattr(self, c.name)) for c in self.__table__.columns])

simple_types = ['integer', 'char', 'boolean', 'text', 'html', 'float', 'monetary', 'date', 'datetime', 'selection']

class Orm(dict):
    def __init__(self, env):
        self.sessionmaker = sessionmaker()
        self.env = env
        self.Base = declarative_base(bind=engine)
        self.m2o = defaultdict(list)
        self.o2m = defaultdict(list)
        self.related = defaultdict(list)
        
        for name, model in env.registry.models.items():
            self.register_model(name, model)
        for parent, child_list in self.m2o.items():
            for child in child_list:
                self.register_m2o(parent, child)
#         for parent, child_list in self.related.items():
#             for child in child_list:
#                 self.register_related(parent, child)
        for parent, child_list in self.o2m.items():
            for child in child_list:
                self.register_o2m(parent, child)
    
    def register_m2o(self, parent, child_infos):
        child, col_name = child_infos
        child_name = col_name[:-3]
        child = self[child]
        f_key = getattr(self[parent], col_name)
        print("M2O {} {} {}".format(parent, child_name, f_key))
#         if type(f_key) != AssociationProxy:
#             setattr(self[parent], child_name, relationship(child, foreign_keys=[f_key], lazy="joined"))
#         else:
#             setattr(self[parent], child_name, relationship(child, primaryjoin="{}.{} == {}.id".format(self[parent].__tablename__, col_name, child.__tablename__), lazy="joined"))
        try:
#             setattr(self[parent], child_name, relationship(child, primaryjoin=(getattr(self[parent], col_name) ==  child.id), lazy="joined"))
            setattr(self[parent], child_name, relationship(child, primaryjoin=(foreign(f_key) ==  remote(child.id)), viewonly=True))

        except Exception as e:
            import sys;sys.path.append(r'/home/sylvain/.eclipse/org.eclipse.platform_3.8_155965261/plugins/org.python.pydev_4.1.0.201505270003/pysrc')
            import pydevd;pydevd.settrace()
            pass
#         setattr(self[parent], child_name, relationship(child, foreign_keys=[f_key]))
    
    def register_o2m(self, parent, child_infos):
        col_name, child, inverse = child_infos
        if inverse == 'create_uid':
            return
        print("Tentative O2M {} {} {}".format(col_name, child, inverse))
        # foreign_keys = [getattr(self[child], inverse)] if inverse and type(getattr(self[child], inverse)) != AssociationProxy else None
        # setattr(self[parent], col_name, relationship(self[child], foreign_keys=foreign_keys))
        fkey = getattr(self[child], inverse) if inverse and type(getattr(self[child], inverse)) != AssociationProxy else None
        if not fkey:
            return
        setattr(self[parent], col_name, relationship(self[child], primaryjoin=foreign(self[parent].id) == remote(fkey), viewonly=True))
    
    # register a model in metadata, and return a list of relationship
    def register_model(self, name, model):
        # the database model name
        table_name = model._table
        # same declarative base for all models
        bases = (self.Base,)
        descr = {
                 '__tablename__': table_name,
                 '__table_args__': {'extend_existing':True},
                 '__unicode__': show_object, # basic concatenation function of all columns
                 }
        for col_name, col_obj in model._fields.items():
            if col_name in ['create_uid', 'write_uid']:
                continue
            # special case to handle primary key
            if col_name == 'id':
                descr[col_name] = Column(Integer, primary_key=True)
                continue
            # __last_update is not in database
            if col_obj.company_dependent:
                continue
            # TODO computed fields
            if col_obj.related != None:
                if len(col_obj.related) > 2:
                    continue
                fkey, assoc = col_obj.related
                fkey = fkey[:-3]
                print("Related => sur {} m2o {} nouvel attribut {}".format(name, fkey, assoc))
                descr[col_obj.name] = association_proxy(fkey, assoc)
                continue
            if type(col_obj.column) == openerp.osv.fields.related:
                if len(col_obj.column.arg) != 2:
                    continue
                fkey, other = col_obj.column.arg
                descr[col_obj.name] = association_proxy(fkey, other)
                continue
            if type(col_obj.column) == openerp.osv.fields.function:
                continue
            if col_name == '__last_update' or (
                    col_obj.compute != None
                    and col_obj.store == False):
                continue
            # 'plain data' types, without relationships
            if col_obj.type in simple_types:
                descr[col_name] = Column(type_map[col_obj.type])
            if col_obj.type == 'many2one':
                # TODO check si la fonction de normalisation n'existe pas dans odoo
                #comodel_name = col_obj.comodel_name.replace('.', '_')
                comodel_key = self.env[col_obj.comodel_name]._table + ".id"
                descr[col_name] = Column(Integer, ForeignKey(comodel_key))
                self.m2o[name].append((col_obj.comodel_name, col_name))
            if col_obj.type == 'one2many':
                if type(col_obj.column) == openerp.osv.fields.function:
                    print("{}\nSkipped {}\n{}".format('='*50, col_obj, '='*50))
                    continue
                self.o2m[name].append((col_name, col_obj.comodel_name, col_obj.inverse_name))
#         for ih_class, ih_fkey in model._inherits.items():
#             assoc_lines = set(self.env[ih_class]._fields.keys()) - set(model._fields.keys())
#             for assoc in assoc_lines:
#                 descr[assoc] = association_proxy(ih_fkey, assoc)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error')
                self[name] = type(name, bases, descr)
        except Exception:
            import traceback; traceback.print_exc()
            import sys;sys.path.append(r'/home/sylvain/.eclipse/org.eclipse.platform_3.8_155965261/plugins/org.python.pydev_4.1.0.201505270003/pysrc')
            import pydevd;pydevd.settrace()
            pass

# construire toutes les classes sans relationship
# en construisant, stocker les relationship
# une fois que tout construit, ajouter les relationship
# utiliser des getattr partout
# algo pour merger les o2m et m2o?
# class Orm(defaultdict):
#     def __init__(self, env):
#         # self.metadata = MetaData()
#         self.sessionmaker = sessionmaker()
#         self.env = env
#         self.Base = declarative_base(bind=engine)
#         import sys;sys.path.append(r'/home/sylvain/.eclipse/org.eclipse.platform_3.8_155965261/plugins/org.python.pydev_4.1.0.201505270003/pysrc')
#         import pydevd;pydevd.settrace()
#     
#     def __missing__(self, key):
#         odoo_model = self.env[key]
#         table_name = odoo_model._table
#         cols = odoo_model._fields
#         bases = (self.Base,)
#         descr = {
#                  '__tablename__': table_name,
#                  '__unicode__': show_object
#                  }
#         for col_name, col_obj in cols.items():
#             if col_name == 'id':
#                 
#                 descr[col_name] = Column(Integer, primary_key=True)
#                 continue
#             if col_name == '__last_update' or col_obj.compute != None:
#                 continue
#             if col_obj.type in simple_types:
#                 descr[col_name] = Column(type_map[col_obj.type])
#             if col_obj.type == 'many2one':
#                 if col_obj.comodel_name not in ['product.product', 'mrp.manufacturingorder']:
#                     continue
#                 comodel_name = col_obj.comodel_name.replace('.', '_') + ".id"
#                 descr[col_name] = Column(Integer, ForeignKey(comodel_name))
#                 relation_name = col_name[:-3]
#                 descr[relation_name] = relationship(
#                                                     col_obj.comodel_name.replace('.', '_'),
#                                                     foreign_keys="[%s]" % (comodel_name),
#                                                     lazy='joined'
#                                                     )
#             if col_obj.type == 'one2many':
#                 if col_obj.comodel_name not in ['product.product', 'mrp.manufacturingorder']:
#                     continue
#                 relation_name = col_name[:-4] + 's'
#                 comodel_name = col_obj.comodel_name.replace('.', '_')
#                 #inverse_name
#                 inverse_name = col_obj.inverse_name[:-3]
#                 descr[relation_name] = relationship(col_obj.comodel_name.replace('.', '_'),
#                                                     back_populates=inverse_name,
#                                                     #primaryjoin="%s.%s == %s.id" % (comodel_name, col_obj.inverse_name, table_name)
#                                                     foreign_keys="[%s.%s]" % (comodel_name, col_obj.inverse_name)
#                                                     #remote_side=id
#                                                     )
#         new_model = type(table_name, bases, descr)
#         return new_model
