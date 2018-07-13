# -*- coding: utf-8 -*-
__name__ = "Create id column for batch_scenario_rel if not exists"
from psycopg2 import ProgrammingError

def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    try:
        cr.execute("""SELECT column_name FROM information_schema.columns WHERE table_name = 'batch_scenario_rel' AND column_name = 'id';""")
        if not len(cr.fetchall()):
            cr.execute("""
    CREATE SEQUENCE batch_scenario_rel_id_seq
  INCREMENT 1
  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 1
  CACHE 1;
ALTER TABLE batch_scenario_rel_id_seq
  OWNER TO openerp;
ALTER TABLE batch_scenario_rel ADD COLUMN id integer;
ALTER TABLE batch_scenario_rel ALTER COLUMN id SET NOT NULL;
ALTER TABLE batch_scenario_rel ALTER COLUMN id SET DEFAULT nextval('batch_scenario_rel_id_seq'::regclass);
                """)
    except ProgrammingError:
        pass # column already exists