# -*- coding: utf-8 -*-
from openerp import models, api, fields, _, http, tools
from openerp.tools import config
from openerp.exceptions import except_orm
import os, shutil, logging, errno

_logger = logging.getLogger(__name__)


def translate(to_translate, translate_to=u'_'):
    if type(to_translate) is not unicode:
        to_translate = unicode(to_translate)
    exclude_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    translate_table = dict((ord(char), translate_to) for char in exclude_chars)
    return to_translate.translate(translate_table)


class note_openprod(models.Model):
    """ 
        Note Openprod 
    """
    _name = 'note.openprod'
    _description = 'Note Openprod'
    
    @api.model
    def _type_get(self):
        return [
                ('intern_note', _('Intern Note')),
                ('external_note', _('External Note')),
                       ]
        
        
    @api.model
    def _confidentiality_get(self):
        return [
                ('user', _('User')),
                ('all', _('All')),
                ('responsible', _('Responsible')),
                       ]
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(note_openprod, self).default_get(fields_list=fields_list)
        # Partie qui permet de créer une note à partir d'un objet en appelant la vue des actions
        if self.env.context.get('reference_generat_auto'):
            res['button_save_visible'] = True
            if self.env.context.get('active_model') and self.env.context.get('active_id'):
                reference = '%s,%d'%(self.env.context['active_model'], self.env.context['active_id'])
                res['reference'] = reference
            
        return res
    
    # Rien à faire là, mais il faut bien le mettre quelque part
    def _auto_init(self, cr, context=None):
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
$$ LANGUAGE plpgsql;""")
        return models.Model._auto_init(self, cr, context=context)
    
    
    @api.model
    def create(self, vals):
        """
        """
        if not vals:
            vals = {}
        
        vals['button_save_visible'] = False
        return super(note_openprod, self).create(vals)
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, string='Subject')
    user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', default=lambda self: self.env.user.id)
    type = fields.Selection('_type_get', string='Type', default='intern_note')
    description = fields.Html(string='Description')
    date = fields.Date(string='Date', default=lambda self: fields.Date.today())
    button_save_visible = fields.Boolean(string='button_save_visible', default=False)
    confidentiality = fields.Selection('_confidentiality_get', string='Confidentiality')
    user_ids = fields.Many2many('res.users', 'note_user_rel', 'note_id', 'user_id', string='Authorized users')
    group_ids = fields.Many2many('res.groups', 'note_group_rel', 'note_id', 'group_id', string='Authorized groups')
    
    @api.multi
    def save_action(self):
        return {'type': 'ir.actions.act_window_close'}
    
    
    
class document_openprod(models.Model):
    """ 
        Documents Openprod 
    """
    _name = 'document.openprod'
    _description = 'Documents Openprod'
    
    
    @api.multi
    @api.depends('name')
    def name_get(self):
        """
            On affiche le nom sous la forme [version]nom
        """
        result = []
        for document in self:
            if document.version:
                name = '[%s] %s'%(document.version, document.name)
            else:    
                name = document.name
                 
            result.append((document.id, name))
             
        return result


    @api.model
    def default_get(self, fields_list):
        res = super(document_openprod, self).default_get(fields_list=fields_list)
        # par défaut, les documents vont dans le répertoire "A trier"
        if not res.get('directory_id'):
            data_pool = self.env['ir.model.data']
            res_model, res_id = data_pool.get_object_reference('base_openprod', 'default_document_directory')
            res['directory_id'] = res_id
        return res


    @api.model
    def create(self, vals):
        """
        """
        if not vals:
            vals = {}
        # crée le fichier associé
        if 'name' in vals:
            vals['name'] = translate(vals['name'])
        directory_id = self.env['document.directory'].browse(vals['directory_id'])
        ext = vals.get('extension', False) or (vals.get('fname', '') or '').split('.')
        if type(ext) != unicode:
            if len(ext) > -1:
                ext = ext[-1]
            else:
                ext = ''
        path = os.path.join(
                            directory_id.datadir,
                            directory_id.full_path,
                            self.get_path(vals['name'],
                                          vals.get('version', False),
                                          ext)
                            )
        if not os.path.exists(path):
            os.open(path, os.O_CREAT | os.O_EXCL, 0600) # create, but fail if already exists
        else:
            raise except_orm('Error', u'This filename already exists : {}'.format(path))
        
        vals['button_save_visible'] = False
        return super(document_openprod, self.with_context(create=True)).create(vals)
    
    
    @api.one
    def _get_document_attachment_binary_filesystem(self):
        directory_id = self.directory_id
        path = os.path.join(directory_id.datadir, directory_id.full_path, self.fname)
        if not os.path.exists(path):
            open(path, 'w+').close()
        if self.env.context.get('bin_size'):
            self['attachment'] = tools.human_size(os.path.getsize(path))
            return
        with open(path, 'r') as f:
            self['attachment'] = f.read().encode('base64')
    
    
    @api.one
    def _set_document_attachment_binary_filesystem(self):
        old_ext = self.extension
        directory_id = self.directory_id
        ext = (self.fname or '').split('.')
        if len(ext) > 1:
            ext = ext[-1]
        else:
            ext = False
        self.extension = ext
        dup = self.search([
                           ('directory_id', '=', self.directory_id.id),
                           ('extension', '=', ext),
                           ('name', '=', self.name),
                           ('version', '=', self.version),
                           ])
        if len(dup) > 1:
            raise except_orm('Error', 'Duplicate filename')
        self._compute_fname()
        path = os.path.join(directory_id.datadir, directory_id.full_path, self.fname)
        with open(path, 'w') as f:
            datas = (self.attachment or '').decode('base64')
            f.write(datas)
            self.env.cr._files_to_clean.append(path)
            file_type = self.env['ir.attachment']._compute_mimetype({
                'datas': self.attachment,
                'datas_fname': self.fname,
             })
            self.index_content = self.env['ir.attachment']._index(datas, self.fname, file_type)
        old_fname = self.get_path(self.name, self.version, old_ext)
        if self.fname != old_fname:
            old_path = os.path.join(directory_id.datadir, directory_id.full_path, old_fname)
            if os.path.exists(old_path):
                os.unlink(old_path)
        
    def get_path(self, name, version, extension):
        res = u'{}'
        args = [name]
        if version:
            res = res + u'-{}'
            args.append(version)
        if extension:
            res = res + u'.{}'
            args.append(extension)
        return res.format(*args)
            
    @api.one
    def _compute_fname(self):
        self.fname = self.get_path(self.name, self.version, self.extension)
    
    @api.one
    def _set_fname(self):
        ext = (self.fname or '').split('.')
        if len(ext) > 1:
            ext = ext[-1]
        else:
            ext = ''
        self.extension = ext
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validated', _('Validated')),
                ('obsolete', _('Obsolete')),
                       ]
    
    
    @api.model
    def _confidentiality_get(self):
        return [
                ('user', _('User')),
                ('all', _('All')),
                ('responsible', _('Responsible')),
                       ]
    
    
    @api.model
    def _month_get(self):
        return [
                ('00', _('Without month')), 
                ('01', _('January')), 
                ('02', _('February')), 
                ('03', _('March')), 
                ('04', _('April')), 
                ('05', _('May')), 
                ('06', _('June')), 
                ('07', _('July')), 
                ('08', _('August')), 
                ('09', _('September')), 
                ('10', _('October')), 
                ('11', _('November')), 
                ('12', _('December'))
           ]
        
    
    @api.one
    @api.depends('date')
    def _compute_date(self):
        """
            Fonction qui calcule le mois et l'année du document d'achat
        """
        date = False
        if self.date:
            date = fields.Date.from_string(self.date)
        else:
            self.month = '00'
            self.year = '0'
        
        if date:
            #On récupère le numéro de l'année
            isocal = date.isocalendar()
            self.year = str(isocal[0])
            #On récupère le mois
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
    
    
    @api.one
    def _compute_old_versions(self):
        self.version_ids = self.env['document.openprod'].search([('last_version_id', '=', self.id)]).ids
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, string='Subject')
    extension = fields.Char(string='Extension')
    fname = fields.Char(compute="_compute_fname", inverse="_set_fname", string="Filename")
    type_id = fields.Many2one('document.type.openprod', string='Type', required=False, ondelete='restrict')
    user_id = fields.Many2one('res.users', string='Responsible', required=False, ondelete='restrict', default=lambda self:self.env.user.id)
    date = fields.Date(string='Date', default=lambda self: fields.Date.today())
    description = fields.Text(string='Description')
    button_save_visible = fields.Boolean(string='button_save_visible', default=False)
    attachment = fields.Binary(string='Attachment', compute='_get_document_attachment_binary_filesystem', 
                               inverse='_set_document_attachment_binary_filesystem', help='help')
    version = fields.Char(string='Version', size=24, required=False)
    state = fields.Selection('_state_get', string='State', default="draft")
    confidentiality = fields.Selection('_confidentiality_get', string='Confidentiality')
    user_ids = fields.Many2many('res.users', 'document_user_rel', 'document_id', 'user_id', string='Authorized users')
    group_ids = fields.Many2many('res.groups', 'document_group_rel', 'document_id', 'group_id', string='Authorized groups')
    end_date = fields.Date(string='End date')
    last_version_id = fields.Many2one('document.openprod', string='Last version', required=False, ondelete='restrict')
    version_ids = fields.One2many('document.openprod', string='Old versions', compute='_compute_old_versions')
    directory_id = fields.Many2one('document.directory', string='Directory', required=True, ondelete='set null')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='set null', default=lambda self:self.env.user.company_id)
    
    # Champs pour le search
    year = fields.Char(string='Year', size=4, compute='_compute_date', store=True)
    month = fields.Selection('_month_get', string='Month', compute='_compute_date', store=True)
    index_content = fields.Text(string="", readonly=True, _prefetch=False)
    
    
    @api.multi
    def save_action(self):
        return {'type': 'ir.actions.act_window_close'}
    
    
    def update_link_objects(self, new_document_id=False, datas=False):
        """
            Fonction destinée à être surchargée, permet de saisir l'id de 
            la nouvelle version du document à la place de l'ancienne 
        """
        return True
    
    
    def create_new_document(self, datas=False, new_version=False):
        """
            Fonction permettant de créer un nouveau document 
        """
        new_document = False
        if new_version:
            today = today = fields.Date.today()
            new_document = self.copy({'version': new_version, 'date': today, 'end_date': False})
            #On met à jour les objets liés à ce document
            self.update_link_objects(new_document.id, datas)
            
        return new_document
    

    def create_new_version(self, new_version=False):
        """
            Fonction permettant de créer la nouvelle version d'un document 
        """
        new_document = False
        if new_version:
            today = today = fields.Date.today()
            new_document = self.with_context(new_version=True).copy({'version': new_version, 'date': today})
            #On récupère les éventuelles versions précédentes de l'objet pour indiquer
            #l'id de la nouvelle version
            old_version = self
            old_version += self.version_ids
            old_version.write({'last_version_id': new_document.id, 
                               'end_date': today, 
                               'state': 'obsolete'})
            #On met à jour les objets liés à ce document
            self.update_link_objects(new_document.id)
            
        return new_document
    
    
    @api.one
    def copy(self, default=None):
        """
            Gestion de la copie du champ binary et de la version
        """
        
        default['last_version_id'] = False
        if not self.env.context.get('new_version', False):
            default['name'] = self.name + ' (copy)'
        default['attachment'] = self.attachment
        res = super(document_openprod, self).copy(default=default)
        return res
    
    
    @api.multi
    def unlink(self):
        """
            Interdiction de supprimer un document s'il est lié à d'autres versions
        """
        to_unlink = []
        for document in self:
            if document.last_version_id:
                raise except_orm(_('Error'), _('You cannot delete this record because there is a new version linked to him'))
            old_path = os.path.join(document.directory_id.full_path, document.fname)
            old_path2 = os.path.join(document.directory_id.datadir, old_path)
            if os.path.exists(old_path2):
                to_unlink.append(old_path2)
            else:
                _logger.error("Deleting document_openprod with path %s but file doesn't exists", old_path2)
    
        res =  super(document_openprod, self).unlink()
        for path in to_unlink:
            os.unlink(path)
        return res
    
    @api.one
    def write(self, vals):
        """
            déplace le fichier ou modifie son contenu
        """
        if not self.env.context.get('create', False) and len({'name', 'version', 'extension', 'directory_id'}.intersection(set(vals))) > 0:
            parent = self.env['document.directory'].browse(vals['directory_id']) if 'directory_id' in vals else self.directory_id
            old_path = os.path.join(parent.datadir, self.directory_id.full_path, self.fname)
            
            if 'name' in vals:
                vals['name'] = translate(vals['name'])
            
            name = vals.get('name', False) or self.name
            version = vals.get('version', False) or self.version
            extension = vals.get('extension') if 'extension' in vals else self.extension
            new_fname = self.get_path(name, version, extension)
            new_path = os.path.join(parent.datadir, parent.full_path, new_fname)
            if self.env.context.get('new_version', False):
                pass
            elif not os.path.exists(new_path):
                shutil.move(old_path, new_path)
            else:
                raise except_orm('Error', u'Path already exists : {}'.format(new_path))

        return super(document_openprod, self.with_context(create=True)).write(vals)

    @api.onchange('attachment')
    def _onchange_attachment(self):
        if '.' in (self.fname or ''):
            splitted = self.fname.rsplit('.', 1)
            self.name = splitted[0]
            self.extension = splitted[1]
        else:
            self.name = self.fname
            self.extension = None

    @api.model
    def search(self, args=None, offset=0, limit=None, order=None, count=None):
        args = args or []
        for i, arg in enumerate(args):
            if isinstance(arg, basestring) and arg == 'orphans':
                orphan_ids = self._get_orphans()
                args[i] = ('id', 'in', orphan_ids)
        return super(document_openprod, self).search(
            args=args, offset=offset, limit=limit,
            order=order, count=count)

    @api.model
    def _get_orphans(self):
        field_m2o_ids = self.env['ir.model.fields'].search([
            ('relation', '=', 'document.openprod'),
            ('ttype', '=', 'many2one'),
        ])
        document_in_use_ids = []
        for field_id in field_m2o_ids:
            if field_id.model not in self.env:
                continue
            document_in_use_ids.extend([
                getattr(x, field_id.name).id for x in
                self.env[field_id.model].search([(field_id.name, '!=', None)])
                if getattr(x, field_id.name).id
            ])
        field_m2m_ids = self.env['ir.model.fields'].search([
            ('relation', '=', 'document.openprod'),
            ('ttype', '=', 'many2many'),
        ])
        for field_id in field_m2m_ids:
            if field_id.model not in self.env:
                continue
            document_in_use_ids.extend([
                y for x in
                self.env[field_id.model].search([(field_id.name, '!=', None)])
                for y in getattr(x, field_id.name).ids
            ])
        orphan_ids = self.search([('id', 'not in', document_in_use_ids)])
        return orphan_ids.ids


class document_type_openprod(models.Model):
    """
        Documents Type Openprod
    """
    _name = 'document.type.openprod'
    _description = 'Documents Openprod'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    
class document_directory(models.Model):
    """
        Structure des répertoires des document openprod
    """
    _name = "document.directory"

    parent_id = fields.Many2one('document.directory', string='Parent', required=False, ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    full_path = fields.Char(string="Full path", compute="_compute_full_path")
    owner_id = fields.Many2one('res.users', 'Owner')

    @property
    def datadir(self):
        cr = http.request.env.cr if 'cr' in http.request.env else self.env.cr
        dbname = cr.dbname
        path = os.path.join(config['data_dir'], 'documents', dbname)
        if not os.path.exists(path):
            os.mkdir(path)
            cr._files_to_clean.append(path)
        return path

    @api.one
    @api.depends('parent_id', 'name')
    def _compute_full_path(self):
        names = []
        p = self.parent_id
        while len(p):
            names.append(p.name)
            p = p.parent_id
        names.reverse()
        names.append(self.name)
        self.full_path = os.path.join(*names)

    @api.multi
    def unlink(self):
        data_pool = self.env['ir.model.data']
        res_model, res_id = data_pool.get_object_reference('base_openprod', 'default_document_directory')
        if res_id in self.ids:
            raise except_orm('Error', 'Can\'t delete default directory')
        for self2 in self:
            path = os.path.join(self2.datadir, self2.full_path)
            try:
                os.rmdir(path)
            except os.error as e:
                if errno.errorcode[e.errno] == 'ENOTEMPTY':
                    raise except_orm(_('Directory %s not empty, please move or delete %s') % (self2.full_path, ", ".join(os.listdir(path))))
                else:
                    _logger.info(u'Path already deleted : %s' % path)
        return super(document_directory, self).unlink()
    
    @api.model
    def create(self, vals):
        vals['name'] = translate(vals["name"])
        res =  super(document_directory, self).create(vals)
        path = os.path.join(self.datadir, res.full_path)
        if not os.path.exists(path):
            self.env.cr._files_to_clean.append(path)
            os.mkdir(path)
        else:
            ind = 1
            path2 = u"{}{}".format(path, ind)
            while os.path.exists(path2):
                ind = ind + 1
                path2 = u"{}{}".format(path, ind)
            self.env.cr._files_to_clean.append(path2)
            os.mkdir(path2)
            res.with_context(no_update_path=True).write({'name': u"{}{}".format(res.name, ind)})
        return res
    
    @api.multi
    def write(self, vals):
        for self2 in self:
            if 'parent_id' in vals:
                new_parent = self2.browse(vals['parent_id'])
                check_recurs = new_parent
                while len(check_recurs):
                    if check_recurs == self2:
                        raise Warning('Recursive move detected')
                    check_recurs = check_recurs.parent_id
                old_path = os.path.join(self2.parent_id.full_path or '', self.name)
                old_path2 = os.path.join(self2.datadir, old_path)
                new_path = os.path.join(new_parent.full_path or '', self.name)
                new_path2 = os.path.join(self2.datadir, new_path)
                if not os.path.exists(new_path2):
                    shutil.move(old_path2, new_path2)
                else:
                    raise except_orm('Error', 'Path already exists')
            if 'name' in vals and not self.env.context.get('no_update_path'):
                vals['name'] = translate(vals["name"])
                old_parent_path = self2.parent_id.full_path if self2.parent_id else ''
                old_path = os.path.join(old_parent_path, self.name)
                old_path2 = os.path.join(self2.datadir, old_path)
                new_path = os.path.join(old_parent_path, vals['name'])
                new_path2 = os.path.join(self2.datadir, new_path)
                if not os.path.exists(new_path2):
                    shutil.move(old_path2, new_path2)
                else:
                    raise except_orm('Error', 'Path already exists')
        res =  super(document_directory, self).write(vals)
        return res
    
    @api.multi
    def name_get(self):
        return [(x.id, x.full_path) for x in self]
    