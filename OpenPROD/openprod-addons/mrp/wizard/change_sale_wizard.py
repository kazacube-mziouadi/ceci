# -*- coding: utf-8 -*-
from openerp import models, fields, api

        
class change_note(models.TransientModel):
    """ 
        Wizard to change the note
    """
    _inherit = 'change.note'
    
    def modification_mrp(self, sale, work_note):
        """
            Fonction permettant de propager la modification de la note dans les OFs et OTs
        """
        sale_line_ids = [x.id for x in sale.order_line_ids]
        if sale_line_ids:
            mo_rcs = self.env['mrp.manufacturingorder'].search([('sale_line_id', 'in', sale_line_ids)])
            if mo_rcs:
                mo_rcs.write({'note_planned': work_note})
                wo_rcs = self.env['mrp.workorder'].search([('mo_id', 'in', mo_rcs.ids)])
                if wo_rcs:
                    wo_rcs.write({'note_planned': work_note})
        
        return True
