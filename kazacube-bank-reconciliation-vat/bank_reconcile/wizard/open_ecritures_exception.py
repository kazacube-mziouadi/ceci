# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (http://tiny.be). All Rights Reserved
#    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
######################################################################

from openerp.osv import osv,fields
from openerp.tools.translate import _


class open_account_line_exception(osv.osv_memory):
    
    _name = 'open.account.line.exception'
    
    def action_open_move_line_excep(self,cr,uid,ids,context=None):
        
        move_line_ids = context.get('active_ids',False)
        #relation_obj=self.pool.get('move.statement.relation')
        move_line_obj=self.pool.get('account.move.line')
        #relation_ids = relation_obj.search(cr,uid,[('account_move_line_id','in',move_line_ids)])
        #relation_obj.unlink(cr,uid,relation_ids,context)
        move_line_obj.write(cr,uid,move_line_ids,{'exception':False,'rapprocher':False,'state1':'normal'})
        return True


open_account_line_exception()

