# -*- coding: utf-8 -*-


# from openerp.osv import osv
from openerp.osv import orm
from openerp.osv import fields
import base64


class LoadFile(orm.TransientModel):
    _name = 'load.jrxml.file'
    _description = 'Load file in the jasperdocument'

    _columns = {
        'datafile': fields.binary('File', required=True,
                                  help='Select file to transfert'),
    }

    def import_file(self, cr, uid, ids, context=None):
        print context
        this = self.browse(cr, uid, ids[0], context=context)
        content = base64.decodestring(this.datafile)
        self.pool['jasper.document'].parse_jrxml(
            cr, uid, context.get('active_ids'), content, context=context)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
