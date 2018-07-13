# -*- coding: utf-8 -*-
from osv import fields,osv
from tools.translate import _
import decimal_precision as dp



class wizard_modify_group_wo(osv.osv_memory):
    _name = 'wizard.modify.group.wo'
    
    
    _columns = {
            'wo_group_id': fields.many2one('mrp.group.wo', 'Group', help="help.wizard_modify_group_wo.wo_group_id"),
            }
    
    def go(self, cr, uid, ids, context=None):
        wo_obj = self.pool.get('mrp.production.workcenter.line')
        group_wo_obj = self.pool.get('mrp.group.wo')
        
        this = self.browse(cr, uid, ids[0], context=context)
        
        wo_ids = context.get('active_ids', False)
        if wo_ids:
            group_wo_obj.delete_wo_from_group(cr, uid, wo_ids, context=context)
                
            if this.wo_group_id:
                group_wo_obj.add_wo_to_group(cr, uid, this.wo_group_id.id, wo_ids, context=context)
                    
        
        return {'type': 'ir.actions.act_window_close'}