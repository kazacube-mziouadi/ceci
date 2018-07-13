# -*- coding: utf-8 -*-
__name__ = "Check end_state boolean for 'cancel' and 'done' action state"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""update 
                    action_state
                  set 
                      end_state = true 
                  where 
                      id in (4, 5)
                """)
