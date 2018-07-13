# -*- coding: utf-8 -*-
__name__ = "Update get_translation to allow any module"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""CREATE OR REPLACE FUNCTION get_translation(plang varchar, pmodule varchar, psrc text, pname varchar, pres_id integer) RETURNS text AS $$
    DECLARE
        result text;
    BEGIN
        select into result value
        from ir_translation
        where lang = plang
        and module like pmodule
        and src = psrc
        and name = pname
        and res_id = pres_id
        limit 1;
        return coalesce(result, psrc);
    END;
$$ LANGUAGE plpgsql;
                """)
