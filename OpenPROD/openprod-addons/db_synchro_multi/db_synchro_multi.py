# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import pooler, _
from openerp.addons.db_connection.db_connection import RPCProxy
import time
import types

MAX_SUB_DOMAIN = 3 

def _get_fields_type(self, cr, uid, context=None):
    # Avoid too many nested `if`s below, as RedHat's Python 2.6
    # break on it. See bug 939653.  
    return sorted([(k,k) for k,v in fields.__dict__.iteritems()
                      if type(v) == types.TypeType and \
                         issubclass(v, fields._column) and \
                         v != fields._column and \
                         not v._deprecated and \
                         not issubclass(v, fields.function)])
    
    
class db_synchro_category(osv.osv):
    _name = 'db.synchro.category'
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'description': fields.text('Description'),
        }
    
    
    
class db_synchro_synchro(osv.osv):
    _name = 'db.synchro.synchro'
    _columns = {
        'name': fields.char('Description', size=128, required=True),
        'sequence': fields.integer('Sequence', required=True),
        'model_id': fields.many2one('ir.model', 'Object', required=True, ondelete='restrict'),
        'category_id': fields.many2one('db.synchro.category', 'Category', ondelete='restrict'),
        'field_ids': fields.many2many('ir.model.fields', 'db_synchro_fields_rel', 'synchro_line_id', 'field_id', string='Fields'),
        'exclude_field_ids': fields.many2many('ir.model.fields', 'db_synchro_exclude_fields_rel', 'synchro_line_id', 'field_id', string='Exclude fields'),
        'constant_field_ids': fields.one2many('db.synchro.constant.fields', 'synchro_id', 'Constants'),
        'domain': fields.text('Domain', help='Specifying search criteria to select records in a table\n' \
                                             '[(\'field_name\', \'operator\', \'value\'), ...]\n\n' \
                                             'Operators:\n  =  !=   >  <  >=  <=  like  ilike  in  not in\n\n' \
                                             'Logical operators / Prefix operators:\n  | (OR)  & (AND) \n\n' \
                                             'Keywords:\n' \
                                             ' - "%domain": keyword will be replace by the result of another domain\n' \
                                             ' - "%2domain": keyword will be replace by the result of another domain\n' \
                                             ' - "%3domain": keyword will be replace by the result of another domain\n' \
                                             ' - "%xml_id": keyword will be replace by all ids who have an XML ID\n' \
                                             ' - "%user_id": keyword will be replace by the user id\n' \
                                             ' - "%company_id": keyword will be replace by the company\'s user id\n' \
                                             ' - "%last_sync_date": keyword will be replace by the last history synchronisation date for this database BE CAREFUL: date is a char, so you have to frame it with quotes\n\n' \
                                             'Example:\n' \
                                             'field_A is true OR field_B contains(case sensitive) bbb OR field_C contains (case insensitive) \'ccc\'\n' \
                                             '[\'|\', \'|\', (\'field_A\', \'=\', True), (\'field_B\', \'like\', \'bbb\'), (\'field_C\', \'ilike\', \'ccc\')]\n\n' \
                                             'NB:\n' \
                                             'By default, inactive records are sought after.'
                                             ),
        'base_line_ids': fields.one2many('db.synchro.synchro.base.line', 'synchro_id', 'Bases'),
        'record_ids': fields.one2many('db.synchro.synchro.record', 'synchro_id', 'Records'),
        'sync_m2o_ids': fields.one2many('db.synchro.synchro.m2o', 'synchro_id', 'M2O'),
        'history_ids': fields.one2many('db.synchro.synchro.history', 'synchro_id', 'History'),
        'conversion_mode': fields.selection(string='Conversion mode', selection=[('id', 'ID'),
                                                                                 ('src_id', 'Source ID'), 
                                                                                 ('xml_id', 'XML ID'), 
                                                                                 ('domain', 'Domain')], required=True),
        'sync_domain': fields.text('Domain', help='Specifying search criteria to select records in a database compared to another database\n' \
                                                  '[(\'db1_field_name\', \'operator\', \'db2_field_name\'), ...]\n\n' \
                                                  'Operators:\n  =  !=   >  <  >=  <=  like  ilike  in  not in\n\n' \
                                                  'Logical operators / Prefix operators:\n  | (OR)  & (AND) \n\n' \
                                                  'Example:\n' \
                                                  'db1_field_A = db2_field_A\n' \
                                                  '[(\'field_A\', \'=\', \'field_A\')]'),
        'is_create': fields.boolean('Create if not found'),
        'create_src_link': fields.boolean('Create SRC link'),
        'bypass_errors': fields.boolean('Bypass errors'),
        'is_sub_domain': fields.boolean('Sub domain'),
        'is_sub_domain2': fields.boolean('Sub domain 2'),
        'is_sub_domain3': fields.boolean('Sub domain 3'),
        'start_after_db_update': fields.boolean('Start after DB update'),
        'sub_domain': fields.text('Sub domain'),
        'sub_domain_field_id': fields.many2one('ir.model.fields', string='Sub domain field', ondelete='restrict'),
        'sub_domain_model_id': fields.many2one('ir.model', 'Sub domain object', ondelete='restrict'),
        'sub_domain2': fields.text('Sub domain 2'),
        'sub_domain2_field_id': fields.many2one('ir.model.fields', string='Sub domain 2 field', ondelete='restrict'),
        'sub_domain2_model_id': fields.many2one('ir.model', 'Sub domain 2 object', ondelete='restrict'),
        'sub_domain3': fields.text('Sub domain 3'),
        'sub_domain3_field_id': fields.many2one('ir.model.fields', string='Sub domain 3 field', ondelete='restrict'),
        'sub_domain3_model_id': fields.many2one('ir.model', 'Sub domain 3 object', ondelete='restrict'),
        
#         'cron_ids': fields.many2many('ir.cron','synchro_cron_rel','synchro_id','cron_id','Crons'),
                }


    def _get_sequence_max(self, cr, uid, context=None):
        max_ids = self.search(cr, uid, [], order='sequence desc', limit=1, context=context)
        if max_ids:
            res = self.read(cr, uid, max_ids[0], ['sequence'], context=context)['sequence'] + 1
        else:
            res = 0
        return res

    _order = 'sequence'
    _defaults = {
#         'sequence': _get_sequence_max,
#         'conversion_mode': 'id',
#         'create': False,
#         'bypass_errors': False,
#         'is_sub_domain': False,
#         'start_after_db_update': False,
#         'domain': '[]',
#         'sub_domain': '[]',
                 }
    
    _sql_constraints = [('unique_seq', 'unique(sequence)', 'Field "Sequence" must be unique')]

    
    def onchange_conversion_mode(self, cr, uid, ids, conversion_mode, context=None):
        v = {}
        res = {'value': v}
        if conversion_mode == 'xml_id':
            v['create'] = False
            
        return res 
    
    
    def onchange_domain(self, cr, uid, ids, domain, sub_domain, sub_domain2, sub_domain3, context=None):
        v = {}
        res = {'value': v}
        for i in range(1, MAX_SUB_DOMAIN + 1):
            if i == 1:
                i = ''
            if '%%%sdomain'%(i) in ' '.join([domain or '', sub_domain or '', sub_domain2 or '', sub_domain3 or '']):
                v['is_sub_domain%s'%(i)] = True
            else:
                v['is_sub_domain%s'%(i)] = False
            
        return res 

        
    def onchange_model_id(self, cr, uid, ids, context=None):
        return {'value': {'field_ids': [],
                          'record_ids': [],
                          'constant_field_ids': []}}

    
    def do_search(self, cr, uid, model, domain, context):
        try:
            try:
                res = self.pool.get(model).osv_search(cr, uid, domain and eval(domain) or [], context=context)
            except:
                res = self.pool.get(model).search(cr, uid, domain and eval(domain) or [], context=context)
                
        except:
            res = []
            
        return res

    
    def do_read(self, cr, uid, model, res_ids, field, context):
        try:
            res = self.pool.get(model).read(cr, uid, res_ids, [field], context=context)
            res = list(set([isinstance(x[field], tuple) and x[field][0] or x[field] for x in res]))
        except:
            res = []
            
        return res
    
    
    def xml_id_replace(self, cr, uid, model, domain, context=None):
        # Permet de remplacer la clé %xml_id entrée dans un domaine par tous les enregistrements du model ayant un XML ID
        data_obj = self.pool.get('ir.model.data')
        data_ids = data_obj.search(cr, uid, [('module', '!=', '__export__'), 
                                             ('res_id', '!=', False), 
                                             ('model', '=', model)], context=context)
        if data_ids:
            ids_with_xml_id = [x['res_id'] for x in data_obj.read(cr, uid, data_ids, ['res_id'], context=context)] 
        else:
            ids_with_xml_id = []
        
        domain = domain.replace('%xml_id', str(ids_with_xml_id))
        return domain
    
    
    def last_date_sync_replace(self, cr, uid, domain, synchro, base=False, context=None):
        # Permet de remplacer la clé %last_date_sync entrée dans un domaine par la derniere date d'execution de la base passée en paramètre
        if base:
            history_obj = self.pool.get('db.synchro.synchro.history')
            history_ids = history_obj.search(cr, uid, [('synchro_id', '=', synchro.id), 
                                                       ('base_id', '=', base.id), 
                                                       ('state', '=', 'done')], order='start_date desc', limit=1, context=context)
            if history_ids:
                res = history_obj.read(cr, uid, history_ids, ['start_date'], context=context)[0]['start_date']
            else:
                res = '2001-01-01 00:00:00'
                
        else:
            res = '2001-01-01 00:00:00'
        
        domain = domain.replace('%last_sync_date', res)
        return domain
    
    
    def records_vizualisation_button(self, cr, uid, ids, context=None):
        rec_obj = self.pool.get('db.synchro.synchro.record')
        for synchro in self.browse(cr, uid, ids, context=context):
            if synchro.record_ids:
                rec_obj.unlink(cr, uid, [r.id for r in synchro.record_ids], context=context)
                cr.commit()
            
        return self.records_vizualisation(cr, uid, ids, context=context)
        

    def compute_domain(self, cr, uid, user, synchro, i, context=None):
        if synchro['sub_domain%s_model_id'%(i)] and synchro['sub_domain%s'%(i)]:
            sub_domain = synchro['sub_domain%s'%(i)]
            if '%xml_id' in sub_domain:
                sub_domain = self.xml_id_replace(cr, uid, synchro.sub_domain_model_id.model, sub_domain, context=context)
                
            if '%user_id' in sub_domain:
                sub_domain = sub_domain.replace('%user_id', str(uid))
                
            if '%company_id' in sub_domain:
                sub_domain = sub_domain.replace('%company_id', str(user.company_id.id))
                
            # Gestion des sous domaines
            for j in range(1, MAX_SUB_DOMAIN + 1):
                if i == 1:
                    i = ''
                if '%%%sdomain'%(j) in sub_domain:
                    sub_record_ids = self.compute_domain(cr, uid, user, synchro, j, context=context)
                    sub_domain = sub_domain.replace('%%%sdomain'%(j), str(sub_record_ids))
                
            record_ids = self.do_search(cr, uid, synchro['sub_domain%s_model_id'%(i)].model, sub_domain, context=context)
            if synchro['sub_domain%s_field_id'%(i)] and record_ids:
                record_ids = self.do_read(cr, uid, synchro['sub_domain%s_model_id'%(i)].model, record_ids, synchro['sub_domain%s_field_id'%(i)].name, context=context)
                
        else:
            record_ids = []
            
        return record_ids


    def records_vizualisation(self, cr, uid, ids, base=False, context=None):
        rec_obj = self.pool.get('db.synchro.synchro.record')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        for synchro in self.browse(cr, uid, ids, context=context):
            domain = synchro.domain
            if synchro.model_id.model:
                if synchro.record_ids:
                    rec_obj.unlink(cr, uid, [r.id for r in synchro.record_ids], context=context)

                if '%last_sync_date' in domain:
                    domain = self.last_date_sync_replace(cr, uid, domain, synchro, base, context=context)

                if '%user_id' in domain:
                    domain = domain.replace('%user_id', str(uid))
                
                if '%company_id' in domain:
                    domain = domain.replace('%company_id', str(user.company_id.id))
                
                # Gestion des sous domaines
                for i in range(1, MAX_SUB_DOMAIN + 1):
                    if i == 1:
                        i = ''
                        
                    if '%%%sdomain'%(i) in domain:
                        sub_record_ids = self.compute_domain(cr, uid, user, synchro, i, context=context)
                        domain = domain.replace('%%%sdomain'%(i), str(sub_record_ids))
                    
                if '%xml_id' in domain:
                    domain = self.xml_id_replace(cr, uid, synchro.model_id.model, domain, context=context)
                
                record_ids = self.do_search(cr, uid, synchro.model_id.model, domain, context)
                for record in self.pool.get(synchro.model_id.model).read(cr, uid, record_ids, ['name'], context=context):
                    rec_obj.create(cr, uid, {'synchro_id': synchro.id,
                                             'record_id': record['id'], 
                                             'name': record.get('name', '/')}, context=context)
            
        return True
    
    
    def get_corresponding_id(self, cr, uid, child_obj, mode, record_dict={}, record_id=False, domain=False, model=False, model_obj=False, child_data_obj=False, base_id=False, bypass_errors=False, context=None):
        if context and isinstance(context, dict):
            context_without_lang = context.copy()
        else:
            context_without_lang = {}
        
        if 'lang' in context_without_lang:
            del context_without_lang['lang']

        res = []
        modified_domain = []
        # Flag qui évite de relire tous les champs en base plusieurs fois
        all_fields = False
        record_id = record_dict.get('id', record_id)
        if mode == 'id':
            modified_domain.append(('id', '=', record_id))
        elif mode == 'domain' and domain and (isinstance(domain, unicode) or isinstance(domain, str)):
            if record_id and not record_dict:
                record_dict = model_obj.read(cr, 1, record_id, [], context=context_without_lang)
                all_fields = True
                
            domain = eval(domain)
            for arg in domain:
                if isinstance(arg, str):
                    modified_domain.append(arg)
                # Gestion du domaine principale ou les champs relationnels sont directement remplacés pas les ids (laissé sous forme de liste jusqu'ici pour pouvoir faire la distinction)
                elif isinstance(arg, list):
                    modified_domain.append(tuple(arg))
                elif isinstance(arg, tuple):
                    arg = list(arg)
                    field = arg.pop(-1)
                    
                    # Si le champ n'est pas dans les champs à mettre à jour deja récupérés en base, on récupere tous les champs
                    if field not in record_dict:
                        if all_fields:
                            raise osv.except_osv(_('Error'), _('%s is not a field')%(field))
                        else:
                            record_dict = model_obj.read(cr, uid, record_id, [], context=context_without_lang)
                            all_fields = True
                            
                    if field in record_dict:
                        field_value = record_dict[field]
                        if isinstance(field_value, tuple):
                            raise osv.except_osv(_('Error'), _('Domain cannot contain relation field (%s)')%(field))
                        else:
                            arg.append(field_value)
                            modified_domain.append(tuple(arg))
                    
                    else:
                        raise osv.except_osv(_('Error'), _('%s is not a field')%(field))
                    
        elif mode == 'xml_id' and model and child_data_obj:
            # Recherche de l'xml id sur la base de référence
            data_obj = self.pool.get('ir.model.data')
            data_ids = data_obj.search(cr, uid, [('module', '!=', '__export__'), 
                                                 ('res_id', '=', record_id), 
                                                 ('model', '=', model)], order='id desc')
            for data_id in data_ids:
                try:
                    data_brw = data_obj.browse(cr, uid, data_id, context=context)
                    # Recherche de l'enregistrement sur la base à updater par rapport à l'xml id
                    ref = child_data_obj.get_object_reference(cr, uid, data_brw.module, data_brw.name)
                    if ref:
                        res = ref and [ref[-1]]
                        
                    break
                except:
                    pass
                    
            if not res:
                if bypass_errors:
                    pass
                else:
                    raise osv.except_osv(_('Error'), _('XML id not found (model: %s, id: %d)')%(model, record_id))
            
        elif mode == 'src_id':
            src_id_obj = self.pool.get('db.synchro.src.id')
            # Ids de la table de relation
            rel_id = src_id_obj.src_search(cr, uid, record_id, model, base_id, context=context)
            if rel_id:
                res = src_id_obj.src_get(cr, uid, rel_id, child_obj, context=context)
                
        if modified_domain:
            try:
                res = child_obj.osv_search(cr, uid, modified_domain)
            except:
                res = child_obj.search(cr, uid, modified_domain)
            
        return res
    
    def transform_domain(self, domain, update, m2o_to_read_name):
        res = []
        domain = eval(domain)
        for arg in domain:
            if isinstance(arg, str):
                res.append(arg)
            elif isinstance(arg, tuple):
                if arg[-1] in m2o_to_read_name:
                    arg = list(arg)
                    if arg[1] in ('!=', '<>', 'not in'):
                        arg[1] = 'not in'
                    else:
                        arg[1] = 'in'
                    
                    arg[2] = [update[arg[0]]]
                    res.append(arg)
                else:
                    res.append(arg)

        return str(res)
    
    def start_synchro(self, cr, uid, synchro, bases, context=None):
        if context and isinstance(context, dict):
            context_without_lang = context.copy()
        else:
            context_without_lang = {}
        
        if 'lang' in context_without_lang:
            del context_without_lang['lang']
        
        # Dictionnaire qui contiendra les données des enregistrements de base
        data = {}
        
        # Liste et données des enregistrements à modifier
        update_list = []

        # Dictionnaire et données des enregistrements à créer
        create_dic = {}
        
        # Champs simples à updater
        fields_to_update = ['id']
        
        # Champs M2O à updater
        m2o_to_read = []
        m2o_to_read_name = []
        model = synchro.model_id.model
        mode = synchro.conversion_mode
        child_data_obj = False
        
        base_obj = self.pool.get('db.synchro.base')
        history_obj = self.pool.get('db.synchro.synchro.history')
        record_obj = self.pool.get('db.synchro.synchro.record')
        model_obj = self.pool.get(model)
        src_id_obj = self.pool.get('db.synchro.src.id')

        obj = synchro.model_id.model
        
        # Liste des champs à exclure
        exclude_fields = [f.name for f in synchro.exclude_field_ids]
        
        # Dictionnaire des constantes
        constant_fields = {f.field_id.name: f.value_tree for f in synchro.constant_field_ids}
        
        for field in synchro.field_ids:
            if field.ttype in ('boolean', 'char', 'integer', 'float', 'text', 'selection', 'date', 'datetime', 'reference', 'binary'):
                fields_to_update.append(field.name)
            elif field.ttype in ('many2one', 'many2many'):
                m2o_to_read.append((field, self.pool.get(field.relation), field.ttype))#[field.id] = [field.name, field.relation]
                m2o_to_read_name.append(field.name)

        # Dictionnaire pour la conversion des M2O field_id: (conversion_mode, domain) 
        field_mode = {}
        for sync_m2o in synchro.sync_m2o_ids:
            # Gestion des vrais champs M2O
            if sync_m2o.field_type == 'many2one':
                field_mode[sync_m2o.field_id.id] = [sync_m2o.conversion_mode, sync_m2o.domain, sync_m2o.field_id.relation]
            # Gestion des integer comme des M2O
            elif sync_m2o.field_type == 'integer':
                field_mode[sync_m2o.field_id.id] = [sync_m2o.conversion_mode, sync_m2o.domain, sync_m2o.relation]
                if sync_m2o.field_id.name in fields_to_update:
                    fields_to_update.remove(sync_m2o.field_id.name)
                    m2o_to_read.append((sync_m2o.field_id, self.pool.get(sync_m2o.relation), 'integer'))
                    m2o_to_read_name.append(sync_m2o.field_id.name)
                    
            # Gestion des reference comme des M2O
            elif sync_m2o.field_type in ('reference', 'text'):
                field_mode[sync_m2o.field_id.id] = [sync_m2o.conversion_mode, sync_m2o.domain, False]
                if sync_m2o.field_id.name in fields_to_update:
                    fields_to_update.remove(sync_m2o.field_id.name)
                    m2o_to_read.append((sync_m2o.field_id, False, 'reference'))
                    m2o_to_read_name.append(sync_m2o.field_id.name)
            
            # Gestion des M2M
            elif sync_m2o.field_type == 'many2many':
                field_mode[sync_m2o.field_id.id] = [sync_m2o.conversion_mode, sync_m2o.domain, sync_m2o.field_id.relation, sync_m2o.m2m_domain]
                           
        base_record_dict = {}
        record_ids = []
        for base in bases:
            self.records_vizualisation(cr, uid, [synchro.id], base=base, context=context)
            cr.commit()
            synchro = synchro.browse(synchro.id)
            base_record_ids = [r.record_id for r in synchro.record_ids]
            record_ids.extend(base_record_ids)
            base_record_dict[base.id] = base_record_ids
            
        # Construction d'une liste de dictionnaires des champs à mettre à jour
        record_ids = list(set(record_ids))
        record_dict = {r.record_id: r.id for r in synchro.record_ids}
        if record_ids:
            data = model_obj.read(cr, uid, record_ids, [], context=context_without_lang)
            for d in data:
                update_dic_item = {}
                
                # Champs de base
                for field_name in fields_to_update:
                    if field_name in constant_fields:
                        update_dic_item[field_name] = constant_fields[field_name]
                    elif field_name in d:
                        update_dic_item[field_name] = d[field_name]
                
                # Champs M2O
                for field, m2o_pool, type in m2o_to_read:
                    if field.name in constant_fields:
                        update_dic_item[field.name] = constant_fields[field.name]
                    elif field.name in d:
                        if type == 'many2one':
                            if d[field.name] and isinstance(d[field.name], tuple):
                                # Si le champ est rempli: mise à jour du dictionnaire avec l'id pour faire la transformation pour chaque base
                                update_dic_item[field.name] = d[field.name][0]
                            else:
                                update_dic_item[field.name] = False
                                
                        elif type == 'integer':
                            update_dic_item[field.name] = d[field.name]
                        elif type == 'reference' and isinstance(d[field.name], str) or isinstance(d[field.name], unicode) and ',' in d[field.name]:
                            update_dic_item[field.name] = d[field.name]
                            update_dic_item['x_synchro_ref_model'], str_id = d[field.name].split(',')  
                            if str_id:
                                update_dic_item['x_synchro_ref_id'] = int(str_id)
                                
                        elif type == 'many2many':
                            # S'il y a un domaine pour filtrer le M2M, récupétation des ids communs entre le domaine et le M2M
                            if field_mode[field.id][-1]:
                                update_dic_item[field.name] = list(set(self.do_search(cr, uid, field_mode[field.id][2], field_mode[field.id][3], context=context)) & set(d[field.name]))
                            else:
                                update_dic_item[field.name] = d[field.name]
                                
                if update_dic_item:
                    update_list.append(update_dic_item)
                
                # Remplissage du dictionnaire de création
                if synchro.create:
                    create_dic[d['id']] = {}
                    for f_name, f_value in d.items():
                        if f_name != 'id' and f_name not in exclude_fields and not isinstance(f_value, tuple) and not isinstance(f_value, list):
                            create_dic[d['id']][f_name] = f_value
        
        
        cr2 = pooler.get_db(cr.dbname).cursor()
        for base in bases:
            record_ok = 0
            record_ko = 0
            history_id = history_obj.create(cr, uid, {
                                'synchro_id': synchro.id,
                                'start_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'base_id': base.id,
                                'state': 'error'
                                         }, context=context)
#             try:
            pool = RPCProxy(base)
            child_obj = pool.get(model)
            child_data_obj = pool.get('ir.model.data')
            for update in update_list:
                if update['id'] in base_record_dict[base.id]:
                    error = False
                    # Gestion des M2O
                    for m2o, m2o_pool, type in m2o_to_read:
                        if m2o.id in field_mode:
                            if m2o.name in update:
                                if update[m2o.name]:
                                    if type == 'many2one':
                                        m2o_ids = self.get_corresponding_id(cr, uid, pool.get(field_mode[m2o.id][2]), field_mode[m2o.id][0], record_id=update[m2o.name], domain=field_mode[m2o.id][1], model=field_mode[m2o.id][2], model_obj=m2o_pool, child_data_obj=child_data_obj, base_id=base.id, bypass_errors=synchro.bypass_errors, context=context)
                                    elif type == 'integer':
                                        m2o_ids = self.get_corresponding_id(cr, uid, pool.get(field_mode[m2o.id][2]), field_mode[m2o.id][0], record_id=update[m2o.name], domain=field_mode[m2o.id][1], model=field_mode[m2o.id][2], model_obj=m2o_pool, child_data_obj=child_data_obj, base_id=base.id, bypass_errors=synchro.bypass_errors, context=context)
                                    elif type == 'reference' and 'x_synchro_ref_model' in update and 'x_synchro_ref_id' in update:
                                        m2o_ids = self.get_corresponding_id(cr, uid, pool.get(update['x_synchro_ref_model']), field_mode[m2o.id][0], record_id=update['x_synchro_ref_id'], domain=field_mode[m2o.id][1], model=update['x_synchro_ref_model'], model_obj=self.pool.get(update['x_synchro_ref_model']), child_data_obj=child_data_obj, base_id=base.id, bypass_errors=synchro.bypass_errors, context=context)
                                    elif type == 'many2many':
                                        m2o_ids = []
                                        for r_id in update[m2o.name]:
                                            m2o_ids.extend(self.get_corresponding_id(cr, uid, pool.get(field_mode[m2o.id][2]), field_mode[m2o.id][0], record_id=r_id, domain=field_mode[m2o.id][1], model=field_mode[m2o.id][2], model_obj=m2o_pool, child_data_obj=child_data_obj, base_id=base.id, bypass_errors=synchro.bypass_errors, context=context))
                                            
                                    else:
                                        m2o_ids = False
                                        
                                    if m2o_ids:
                                        if type == 'reference':
                                            update[m2o.name] = '%s,%s'%(update['x_synchro_ref_model'], m2o_ids[0])
                                        elif type == 'many2many':
                                            update[m2o.name] = [(6, 0, m2o_ids)]
                                        else:
                                            update[m2o.name] = m2o_ids[0]
                                            
                                    else:
                                        if synchro.bypass_errors:
                                            del update[m2o.name]
                                            error = True
                                        else:
                                            raise osv.except_osv(_('Error'), _('Relation field "%s" Havn\'t result for base "%s" (record id: %d)')%(m2o.name, base.name_get()[0][-1], update['id']))
                                        
                                # Many2many vide
                                elif type == 'many2many':
                                    update[m2o.name] = [(6, 0, [])]
                                # Autre champ vide
                                else:
                                    update[m2o.name] = False
                                    
                        else:
                            if synchro.bypass_errors:
                                error = True
                            else:
                                raise osv.except_osv(_('Error'), _('Relation field "%s" is not referenced in "Fields conversions" for base "%s" (record id: %d)')%(m2o.name, base.name_get()[0][-1], update['id']))
    
                    # Gestion des champs relationnels dans le domaine de correspondance                    
                    if mode == 'domain':
                        sync_domain = self.transform_domain(synchro.sync_domain, update, m2o_to_read_name)
                    else:
                        sync_domain = synchro.sync_domain
                        
                    # Recuperation des ids correspondants
                    ids_to_update = self.get_corresponding_id(cr, uid, child_obj, mode, record_dict=update, record_id=update['id'], domain=sync_domain, model=model, model_obj=model_obj, child_data_obj=child_data_obj, base_id=base.id, bypass_errors=synchro.bypass_errors, context=context)
                    write_update = update.copy()
                    del write_update['id']
                    if ids_to_update:
                        child_obj.write(cr, uid, ids_to_update, write_update)
                        if synchro.create_src_link:
                            # Test que l'id source n'existe pas déjà pour ne pas le créé en double
                            src_id_id = src_id_obj.src_search(cr, uid, update['id'], model, base.id, context=context)
                            if src_id_id:
                                src_id_obj.write(cr, uid, [src_id_id], {'dest_id': ids_to_update[0]}, context=context)
                            else:
                                src_id_obj.create(cr, uid, {
                                             'src_id': update['id'],
                                             'model': model,
                                             'base_id': base.id,
                                             'dest_id': ids_to_update[0],
                                                 }, context=context)
                                
                    elif synchro.create:
                        create_dic[update['id']].update(write_update)
                        create_dic_keys = create_dic[update['id']].keys()
                        # Gestion des champs créés automatiquement dans les utilisateurs pour créer les groupes 
                        if model == 'res.users':
                            for k in create_dic_keys:
                                if k.startswith('in_group_') or k.startswith('sel_groups_'):
                                    del create_dic[update['id']][k]
    
                        new_id = child_obj.create(cr, uid, create_dic[update['id']])
                        # Si id source MAJ de la table
                        if mode == 'src_id':
                            src_id_obj.src_update(cr, uid, new_id, src_id=update['id'], model=model, base_id=base.id, context=context)
                    
                    if error:
                        record_ko += 1
                        if update['id'] in record_dict:
                            record_obj.write(cr2, uid, [record_dict[update['id']]], {'state': 'Error'}, context=context)
                            cr2.commit()
                    else:
                        record_ok += 1
                        if update['id'] in record_dict:
                            record_obj.write(cr2, uid, [record_dict[update['id']]], {'state': 'Done'}, context=context)
                            cr2.commit()
                        
            history_obj.write(cr, uid, [history_id], {'state': 'done',
                                                      'nb_record_ok': record_ok,
                                                      'nb_record_ko': record_ko,
                                                      'end_date': time.strftime('%Y-%m-%d %H:%M:%S'),}, context=context)
#             except Exception as e:
#                 error = ''
#                 if e and isinstance(e.args, tuple):
#                     for i in e.args:
#                         if error:
#                             error = '%s\n%s'%(error, i)
#                         else:
#                             error = i
#                       
#                     history_obj.write(cr, uid, [history_id], {'msg': error}, context=context)    
        cr2.commit()   
        return True

    
    def start_synchro_button(self, cr, uid, ids, context=None):
        for synchro in self.browse(cr, uid, ids, context=context):
            self.start_synchro(cr, uid, synchro, [b.base_id for b in synchro.base_line_ids], context=context)
            
        return True


    def copy(self, cr, uid, id, default=None, context=None):
        if 'sequence' in default:
            default['sequence'] += 1
        else:
            default['sequence'] = self._get_sequence_max(cr, uid, context=context)
            
        default['history_ids'] = []
        default['record_ids'] = []
        return super(db_synchro_synchro,self).copy(cr, uid, id, default=default, context=context)

    
    
class db_synchro_synchro_base_line(osv.osv):
    _name = 'db.synchro.synchro.base.line'
    _columns = {
        'synchro_id': fields.many2one('db.synchro.synchro', 'Synchro', required=True, ondelete='cascade'),
        'base_id': fields.many2one('db.synchro.base', 'Base', required=True, ondelete='restrict'),
                }
    
    _rec_name = 'base_id'
    
    
    def start_synchro_button(self, cr, uid, ids, context=None):
        sync_obj = self.pool.get('db.synchro.synchro')
        for base_line in self.browse(cr, uid, ids, context=context):
            sync_obj.start_synchro(cr, uid, base_line.synchro_id, [base_line.base_id], context=context)
    
        return True
    
    
            
class db_synchro_synchro_record(osv.osv):
    _name = 'db.synchro.synchro.record'
    _columns = {
        'synchro_id': fields.many2one('db.synchro.synchro', 'Synchro', required=True, ondelete='cascade'),
        'record_id': fields.integer(string='Record id', required=True),
        'name': fields.char(size=64, string='Name'),
        'state': fields.char(size=32, string='State'),
                }
    
            
class db_synchro_synchro_m2o(osv.osv):
    _name = 'db.synchro.synchro.m2o'
    _columns = {
        'synchro_id': fields.many2one('db.synchro.synchro', 'Synchro', required=True, ondelete='cascade'),
        'model_id': fields.related('synchro_id', 'model_id', type="many2one", relation="ir.model", string="Model", store=False, ondelete='restrict'),
        'field_id': fields.many2one('ir.model.fields', string='Field', ondelete='restrict'),
        'field_type': fields.related('field_id', 'ttype', type='selection', selection=_get_fields_type, string='Field Type', size=64),
        'relation': fields.char(size=128, string='Model name'),
        'domain': fields.text('Domain', help='Specifying search criteria to select records in a database compared to another database\n' \
                                             '[(\'db1_field_name\', \'operator\', \'db2_field_name\'), ...]\n\n' \
                                             'Operators:\n  =  !=   >  <  >=  <=  like  ilike  in  not in\n\n' \
                                             'Logical operators / Prefix operators:\n  | (OR)  & (AND) \n\n' \
                                             'Example:\n' \
                                             'db1_field_A = db2_field_A\n' \
                                             '[(\'field_A\', \'=\', \'field_A\')]'),
        'm2m_domain': fields.text('M2M Domain', help='Specifying search criteria to select records in a many2many field\n' \
                                                     '[(\'db1_field_name\', \'operator\', \'value\'), ...]\n\n' \
                                                     'Operators:\n  =  !=   >  <  >=  <=  like  ilike  in  not in\n\n' \
                                                     'Logical operators / Prefix operators:\n  | (OR)  & (AND) \n\n' \
                                                     'Example:\n' \
                                                     'db1_field_A = foo\n' \
                                                     '[(\'field_A\', \'=\', \'foo\')]'),
        'note': fields.text('Note'),
        'conversion_mode': fields.selection(string='Conversion mode', selection=[('id', 'ID'), 
                                                                                 ('src_id', 'Source ID'), 
                                                                                 ('xml_id', 'XML ID'), 
                                                                                 ('domain', 'Domain')], required=True),
                }
    
    _rec_name = 'field_id'
    _defaults = {
                 'domain': '[(\'name\', \'=\', \'name\')]',
                 'field_type': 'many2one',
                }
    
    def onchange_field_id(self, cr, uid, ids, field_id, context=None):
        if field_id:
            type = self.pool.get('ir.model.fields').browse(cr, uid, field_id, context=context).ttype
        else:
            type = 'many2one'
            
        return {'value': {'field_type': type}}
        
        
class db_synchro_synchro_history(osv.osv):
    _name = 'db.synchro.synchro.history'
    _order = 'id desc'
    _columns = {
        'synchro_id': fields.many2one('db.synchro.synchro', 'Synchro', required=True, ondelete='cascade', select=True),
        'start_date': fields.datetime(string='Start date'),
        'end_date': fields.datetime(string='End date'),
        'base_id': fields.many2one('db.synchro.base', 'Base', ondelete='set null', select=True),
        'msg': fields.text('Message'),
        'nb_record_ok': fields.integer('Number of records OK'),
        'nb_record_ko': fields.integer('Number of records KO'),
        'state': fields.selection(string='State', selection=[('new', 'New'), ('done', 'Done'), ('error', 'Error')])
                }
    
    _defaults = {
        'nb_record_ok': 0,
        'nb_record_ko': 0
                 }


class db_synchro_src_id(osv.osv):
    _name = 'db.synchro.src.id'
    _columns = {
        'src_id': fields.integer('Source ID'),
        'dest_id': fields.integer('Destination ID'),
        'model': fields.char(string='Model', size=256),
        'base_id': fields.many2one('db.synchro.base', 'Base', required=True, ondelete='cascade'),
                }
    
    
    def src_search(self, cr, uid, src_id, model, base_id, context=None):
        res = False
        src_id_ids = self.search(cr, uid, [('src_id', '=', src_id), 
                                           ('model', '=', model),
                                           ('base_id', '=', base_id)], limit=1, context=context)
        if src_id_ids:
            res = src_id_ids[0]
        
        return res
    
    
    def src_get(self, cr, uid, rel_id, child_obj, context=None):
        # Verifie si l'id de la base enfant existe toujours
        dest_id = self.read(cr, uid, [rel_id], ['dest_id'], context=context)[0]['dest_id']
        if dest_id:
            try:
                exist = child_obj.osv_search(cr, uid, [('id', '=', dest_id)])
            except:
                exist = child_obj.search(cr, uid, [('id', '=', dest_id)])
                
            if exist:
                res = [dest_id]
            else:
                res = []
                
        else:
            res = []
            
        return res
        
        
    def src_update(self, cr, uid, new_dest_id, id=False, src_id=False, model=False, base_id=False, context=None):
        # Permet de relié l'id source (src_id) à l'id de destination (new_dest_id) que l'enregistrement dans la table de relation existe ou pas
        
        # Force l'id de la table de relation
        if id:
            update_id = id
        elif src_id and model and base_id:
            update_id = self.src_search(cr, uid, src_id, model, base_id, context=context)
        else:
            update_id = False

        # Si enregistrement présent dans la table de relation: écriture            
        if update_id:
            res = self.write(cr, uid, [update_id], {'dest_id': new_dest_id}, context=context)
        # Sinon création
        elif src_id and model and base_id:
            res = self.create(cr, uid, {
                                 'src_id': src_id,
                                 'model': model,
                                 'base_id': base_id,
                                 'dest_id': new_dest_id,
                                     })
        else:
            res = False
            
        return res
    
           
    _sql_constraints = [('unique_model_base_src_id', 'unique(src_id, model, base_id)', 'The fields group "Source ID, Model, Base" must be unique')]


class db_synchro_constant_fields(osv.osv):
    _name = 'db.synchro.constant.fields'
    
    
    def _compute_value_tree(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for c in self.browse(cr, uid, ids, context=context):
            res[c.id] = ''
            if c.field_type == 'selection':
                res[c.id] = c.value_char
            elif c.field_type == 'many2one':
                res[c.id] = c.value_integer
            elif c.field_type in ('boolean', 'float', 'text', 'date', 'datetime', 'text', 'integer', 'char'):
                res[c.id] = c.__getitem__('value_%s'%c.field_type)
            
        return res
    
    
    def onchange_field_id(self, cr, uid, ids, field_id, context=None):
        v = {
            'value_char': False,
            'value_integer': False,
            'value_float': False,
            'value_text': False,
            'value_boolean': False,
            'value_date': False,
            'value_datetime': False,   
            'field_type': False,   
                 }
        
        res = {'value': v}
        if field_id:
            field = self.pool.get('ir.model.fields').browse(cr, uid, field_id, context=context)
            v['field_type'] = field.ttype
            
        return res
    
    
    _columns = {
        'synchro_id': fields.many2one('db.synchro.synchro', 'Synchro', required=True, ondelete='cascade'),
        'field_id': fields.many2one('ir.model.fields', string='Field', ondelete='restrict', required=True),
        'value_char': fields.char('Constant value', size=512),
        'value_integer': fields.integer('Constant value'),
        'value_float': fields.float('Constant value'),
        'value_text': fields.text('Constant value'),
        'value_boolean': fields.boolean('Constant value'),
        'value_date': fields.date('Constant value'),
        'value_datetime': fields.datetime('Constant value'),
        'value_tree': fields.function(_compute_value_tree, type="char", siez=512, string='Constant value'),
        'field_type': fields.related('field_id', 'ttype', type='selection', selection=_get_fields_type, string='Field Type', size=64),
                }
    
    _defaults = {
         'value_boolean': False,
                 }
    
    
    
class db_synchro_launching(osv.osv):
    _name = 'db.synchro.launching'
    _rec_name = 'date'
    _columns = {
        'synchro_ids': fields.many2many('db.synchro.synchro', 'db_synchro_launching_rel', 'synchro_id', 'launching_id', string='Synchronizations'),
        'base_ids': fields.many2many('db.synchro.base', 'db_synchro_base_launching_rel', 'synchro_id', 'base_id', string='Bases'),
        'last_synchro_id': fields.many2one('db.synchro.synchro', string='Last synchronization', ondelete='set null', readonly=True),
        'last_base_id': fields.many2one('db.synchro.base', string='Last base', ondelete='set null', readonly=True),
        'state': fields.selection(string='State', selection=[('new', 'New'), ('done', 'Done'), ('error', 'Error')], readonly=True),
        'log': fields.text('Log', readonly=True),
        'date': fields.datetime('Create date', readonly=True),
        'last_date': fields.datetime('Last execution date', readonly=True)
                }
    
    _defaults = {
        'state': 'new',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                 }
    
    
    def resume(self, cr, uid, ids, context=None):
        for launch in self.browse(cr, uid, ids, context=context):
            launch.run(start_base_id=launch.last_base_id and launch.last_base_id.id or False, start_synchro_id=launch.last_synchro_id and launch.last_synchro_id.id or False)
            
        return True
    
    
    def run(self, cr, uid, ids, context=None, start_base_id=False, start_synchro_id=False):
        base_line_obj = self.pool.get('db.synchro.synchro.base.line')
        err = False
            
        for launch in self.browse(cr, uid, ids, context=context):
            if not start_base_id and not start_synchro_id:
                start = True
            else:
                start = False
                
            log = 'Start: %s'%(time.strftime('%Y-%m-%d %H:%M:%S'))
            launch.write({'log': log, 'state': 'new', 'last_synchro_id': False, 'last_base_id': False, 'last_date': time.strftime('%Y-%m-%d %H:%M:%S')})
            cr.commit()
            for base in launch.base_ids:
                if not start and base.id != start_base_id:
                    continue
                    
                synchro_ids = [x.id for x in launch.synchro_ids]
                if synchro_ids:
                    cr.execute(""" SELECT 
                                     l.id 
                                   FROM 
                                     db_synchro_synchro_base_line l 
                                     JOIN db_synchro_synchro s ON l.synchro_id = s.id
                                   WHERE
                                     s.id in %s AND
                                     l.base_id = %s
                                   ORDER BY s.sequence ASC
                                     """,(tuple(synchro_ids), base.id))
                    line_ids = cr.dictfetchall()
                    if line_ids:
                        log = '%s\n\nBase %s:'%(log, base.name_get()[0][-1])
                        launch.write({'log': log})
                        cr.commit()
                        for line in base_line_obj.browse(cr, uid, [x['id'] for x in line_ids], context=context):
                            if not start:
                                if line.synchro_id.id == start_synchro_id:
                                    start = True
                                else:
                                    continue
                            
                            log = '%s\n    Synchro: [%d]%s'%(log, line.synchro_id.sequence, line.synchro_id.name)
                            launch.write({'log': log})
                            cr.commit()
                            try:
                                line.start_synchro_button()
                                log = '%s: OK'%(log)
                                launch.write({'log': log})
                                cr.commit()
                            except:
                                log = '%s: ERROR'%(launch.log)
                                launch.write({'log': log, 'state': 'error', 'last_synchro_id': line.synchro_id.id, 'last_base_id': base.id})
                                cr.commit()
                                raise osv.except_osv(_('Error'), '')
        
        return True
                            