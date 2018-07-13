# encoding: utf-8

import openerp

def apply_rights_modify_view(actions):
    ret_actions = []
    for action in actions:
        if action[2].get('res_model', action[2].get('model_name')) == 'mass.editing.wizard':
            env = openerp.http.request.env
            if env.uid == 1:
                ret_actions.append(action)
            mass_id = env['mass.object'].search([
                ('ref_ir_act_window', '=', action[2]['id'])])
            if env.uid not in mass_id.auth_user_ids.ids:
                group_ids = mass_id.auth_group_ids.ids
                if len(group_ids):
                    env.cr.execute(
                        '''select *
                        from res_groups_users_rel
                        where uid=%s
                        and gid not in %s''',
                        (env.uid, tuple(group_ids)))
                    if env.cr.rowcount == 0:
                        pass
                    else:
                        ret_actions.append(action)
                else:
                    pass
            else:
                ret_actions.append(action)
        else:
            ret_actions.append(action)
            
    return ret_actions

openerp.models.apply_rights_modify_view = apply_rights_modify_view
