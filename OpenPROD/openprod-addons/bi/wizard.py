from openerp import models, fields, api

class Wizard(models.TransientModel):
    _name = 'bi.wizard'

    dashboard_name = fields.Char(required = True)
    dashboard_adress = fields.Char(required = True)

    @api.multi
    def save(self):
        #enregistrement du nom et de l'adresse du tableau de bord
        main_menu_bi = self.env['ir.ui.menu'].name_search(name='BI' , operator = '=')
        categ_menu_bi = self.env['ir.ui.menu'].name_search(name='Business Inteligence', operator = '=')


        id_categ_menu = categ_menu_bi[0][0]
        server_pentaho = self.env['bi.server'].search([('id', '=', 1)])
        adresse_pentaho = server_pentaho.pentaho_server_address
        view_obj = self.env['ir.ui.view']

        arch = """<?xml version="1.0"?><pentaho></pentaho>"""
        vals = {
                'model': 'bi.dashboard' ,
                'type': 'pentaho',
                'active': True,
                'name': self.dashboard_name,
                'arch_db': arch ,
                'is_override': False#,
        }
        view = view_obj.create(vals)
        view_obj.clear_caches()

        new_view = view_obj.name_search(name=self.dashboard_name, operator= '=')
        id_view = str(new_view[0][0])

        #ajout de l'adresse du dashboard
        vals = {
            'name' : self.dashboard_name,
            'dashboard_address' : self.dashboard_adress
        }
        self.env['bi.dashboard'].create(vals)

        vb = self.env['ir.actions.act_window'].create({ 'type' : 'ir.actions.act_window', 
                                                'res_model' : 'ir.ui.view', 
                                                'view_type' : 'form',
                                                'view_mode' : 'pentaho' ,
                                                'view_id' : id_view ,
                                                'target' : 'current' ,
                                                'filter' : False ,
                                                'multi' : False ,
                                                'name' : 'ir.actions.act_window',
                                                })
        id_action =  str(vb[0].id)
     
        #ajout du menu
        self.env['ir.ui.menu'].create({'parent_id' : id_categ_menu , 
                                        'action' : 'ir.actions.act_window,'+ id_action,
                                        'name' : self.dashboard_name
                                        }) 
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class BIDashboard(models.Model):
    _name = 'bi.dashboard'

    name = fields.Char()
    dashboard_address = fields.Char()

