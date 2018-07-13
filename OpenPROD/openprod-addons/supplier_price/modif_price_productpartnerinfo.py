# coding: utf-8
from openerp import models, api, fields, _
from datetime import datetime, timedelta
from openerp.exceptions import ValidationError
from openerp import netsvc
from openerp import report
import base64
import csv
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


class modif_price_productpartnerinfo(models.Model):
    _name = 'modif.price.productpartnerinfo'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    date = fields.Date(string='Date search')
    purchase_partnerinfo_ids = fields.Many2many('pricelist.supplierinfo', 'purchase_pricelist_partnerinfo_modif_price_rel', 'modif_id', 'partnerinfo_id', string='Purchase Partnerinfo')
    report_export = fields.Binary(string='Report Export', help='Export csv file only')
    report_export_name = fields.Char(string='Name report export', size=256)
    report_import = fields.Binary(string='Report Import', help='Import csv file only')
    report_import_name = fields.Char(string='Name report import', size=256)
    purchase_delete_partnerinfo_ids = fields.Many2many('pricelist.supplierinfo', 'purchase_delete_pricelist_partnerinfo_modif_price_rel', 'modif_id', 'partnerinfo_id', string='Purchase Delete Partnerinfo')
    report_export_before_import = fields.Binary(string='Report Export before import', help='Export csv file only')
    report_export_before_import_name = fields.Char(string='Name report export before import', size=256)
    is_import = fields.Boolean(string='Import', default=False)
    is_export = fields.Boolean(string='Export', default=False)
    date_export = fields.Datetime(string='Date export')
    date_import = fields.Datetime(string='Date import')
    new_date = fields.Date(string='New start date price')
    
    
    @api.onchange('partner_id', 'date')
    def _onchange_partner(self):
        self.purchase_partnerinfo_ids = False
        if self.partner_id:
            supp_info_obj = self.env['product.supplierinfo']
            purchase_pricelist_obj = self.env['pricelist.supplierinfo']
            supp_rcs = supp_info_obj.search([('partner_id', '=', self.partner_id.id)])
            if self.date:
                purchase_pricelist_rcs = purchase_pricelist_obj.search( 
                                                            ['&', ('sinfo_id', 'in', supp_rcs.ids),
                                                            '|', '&',
                                                            ('date_start', '=', False),
                                                            ('date_stop', '=', False),
                                                            '|', '&',
                                                            ('date_start', '<=', self.date),
                                                            ('date_stop', '=', False),
                                                            '|', '&',
                                                            ('date_start', '=', False),
                                                            ('date_stop', '>=', self.date),
                                                            '&',
                                                            ('date_stop', '>=', self.date),
                                                            ('date_start', '<=', self.date)], order='min_qty asc')
            else:
                purchase_pricelist_rcs = purchase_pricelist_obj.search( 
                                                            [('sinfo_id', 'in', supp_rcs.ids),
                                                             ('date_start', '=', False), ('date_stop', '=', False)])
                
            self.purchase_partnerinfo_ids = purchase_pricelist_rcs.ids  

    
    def function_export_csv(self):
        purchase_pricelist_obj = self.env['pricelist.supplierinfo']
        wiz = self
        report_binary = False
        name_report = False
        #Partie achat pour trouver les pricelist.partnerinfo à supprimer
        purchase_dico_supp = {}
        product_partnerinfo_purchase_ids = []
        for x in wiz.purchase_partnerinfo_ids:
            product_partnerinfo_purchase_ids.append(x.id)
            if x.date_stop and x.sinfo_id:
                if not x.sinfo_id in purchase_dico_supp:
                    purchase_dico_supp[x.sinfo_id.id] = [x.min_qty]
                else:
                    purchase_dico_supp[x.sinfo_id].append(x.min_qty)
        
        #Remplir champs de suppressions des pricelists
        purchase_delete_old_ids = []
        for y in wiz.purchase_delete_partnerinfo_ids:
            purchase_delete_old_ids.append((2, y.id))
            
        wiz.write({'purchase_delete_partnerinfo_ids': purchase_delete_old_ids})
        purchase_delete_list_ids = []
        for list_dico in purchase_dico_supp:
            for list_qty in purchase_dico_supp[list_dico]:
                list_rcs = purchase_pricelist_obj.search([('sinfo_id', '=', list_dico), ('min_qty', '=', list_qty), ('date_start', '>', wiz.date)], order='min_qty asc')
                for list in list_rcs:
                    purchase_delete_list_ids.append((4, list.id))
                    
        #Création du report
        doc_jasper_rc = self.env['jasper.document'].search([('report_unit', '=', 'management_price_productpartnerinfo')])
        if doc_jasper_rc:
            (print_commands, format), model_report, report_binary, name_report = self.create_pdf(doc_jasper_rc[0], product_partnerinfo_purchase_ids, wiz)
            
        return doc_jasper_rc, report_binary, name_report, purchase_delete_list_ids
    
    
    @api.multi
    def export_csv(self):
        for wiz in self:
            doc_jasper_rc, report_binary, name_report, purchase_delete_list_ids = wiz.function_export_csv()
            if doc_jasper_rc:
                date_now = datetime.now()
                wiz.write({'report_export': report_binary, 'report_export_name': name_report, 'purchase_delete_partnerinfo_ids': purchase_delete_list_ids, 'is_export': True, 'date_export': date_now})
            else:
                raise ValidationError(_('Problem no report jasper \'management_price_productpartnerinfo\' declared.'))
            
        return True
    
    
    def create_pdf(self, doc_jasper_rc, res_id, wiz):
        today = fields.Datetime.now()
        xml_report_obj = self.env['ir.actions.report.xml']
        context = self.env.context.copy()
        if not context: 
            context = {}
            
        if doc_jasper_rc:
            xml_report_to_print_id = doc_jasper_rc.report_id or False
            if xml_report_to_print_id:
                report_data = xml_report_to_print_id.read(['model', 'report_name'])
                netsvc.LocalService('report.' + report_data[0]['report_name'])
                datas = {'ids': res_id, 'model': 'pricelist.supplierinfo'}
                if context and 'jasper' in context:
                    datas['jasper'] = context['jasper']
                
                (print_commands, format) = report.render_report(self.env.cr, self.env.user.id, res_id, report_data[0]['report_name'], datas, context=context)
                attachments = {}
                name_partner = wiz.partner_id and (wiz.partner_id.reference or wiz.partner_id.name) or doc_jasper_rc.name
                name_report = '%s_%s.%s'%(name_partner,today,format)
                attachments[name_report] = print_commands
                report_binary = False
                for fname, fcontent in attachments.iteritems():
                    report_binary = fcontent and fcontent.encode('base64')
                    
                return (print_commands, format),report_data[0]['report_name'],report_binary,name_report
            
        return (False, False), False, False, ''


    @api.multi
    def import_csv(self):
        pricelist_obj = self.env['pricelist.supplierinfo']
        for wiz in self:
            if wiz.report_import:    
                if not wiz.new_date:
                    raise ValidationError(_('Problem select new start date price.'))
                 
                if wiz.new_date < wiz.date: 
                    raise ValidationError(_('Problem new start date price < Date search.'))
                 
                doc_jasper_id_export, report_binary_export, name_report_export, purchase_delete_list_ids= wiz.function_export_csv() 
                date_stop = (datetime.strptime(wiz.new_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                if doc_jasper_id_export:
                    wiz.write({'report_export_before_import': report_binary_export, 'report_export_before_import_name': name_report_export})
                reader = csv.reader(StringIO(base64.decodestring(wiz.report_import)), delimiter=';')
                #Voir report management_price_productpartnerinfo, premiere colonne id et derniere nouveau prix
                for row in reader:
                    if row[0] != 'ID':
                        try:
                            pricelist_id = int(row[0])
                        except:
                            continue
                             
                        nb_column = len(row)
                        nb_column_qty = nb_column - 2
                        row_qty = row[nb_column_qty]
                        if row[-1]:
                            new_price_str = row[-1].replace(',', '.')
                            new_price = float(new_price_str)
                            if new_price > 0:
                                
                                dico_vals = {'date_stop': False, 'date_start': wiz.new_date, 'price': new_price}
                                pricelist = pricelist_obj.browse(pricelist_id)
                                #Si changement de quantité 
                                if row_qty:
                                    new_qty_str = row_qty.replace(',', '.')
                                    new_qty = float(new_qty_str)
                                    if pricelist_obj.search([('sinfo_id', '=', pricelist.sinfo_id.id), ('min_qty', '=', new_qty), '|', ('date_stop', '=', False), ('date_stop', '>=', wiz.new_date)]):
                                        raise ValidationError(_('A supplier price for product %s, quantity %s and date %s already exists.')%(pricelist.sinfo_id.product_id.name, new_qty, wiz.new_date))
            
                                    if new_qty > 0:                                            
                                        dico_vals.update({'min_qty':new_qty})
                                
                                pricelist.write({'date_stop':date_stop})
                                pricelist.copy(dico_vals)
                 
                #Supprimer les pricelists futurs
                purchase_delete_old_ids = []
                if wiz.purchase_delete_partnerinfo_ids:
                    delete_ids = [x.id for x in wiz.purchase_delete_partnerinfo_ids]
                    pricelist_obj.unlink(delete_ids)
                     
                date_now = datetime.now()
                wiz.write({'purchase_delete_partnerinfo_ids': purchase_delete_old_ids, 'is_import': True, 'date_import': date_now})
            else:
                raise ValidationError(_('Problem no file csv import declared.'))
             
        return {'type': 'ir.actions.act_window_close'}

    
    @api.multi
    def name_get(self):
        """
            Name get du partner [search_date]
        """
        result = []
        for wiz in self:              
            result.append((wiz.id, '%s [%s]'%(wiz.partner_id.name, wiz.date)))
            
        return result