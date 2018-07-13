# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import except_orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.base_openprod.common import hash_list
import locale

import time
from datetime import datetime, timedelta, date as datetime_date
from dateutil.relativedelta import relativedelta


class calendar_template(models.Model):
    """
    Calendar template
    """
    _name = 'calendar.template'
    _description = 'Calendar template'
    _sql_constraints = [
        ('check_calendar_dates', 'check(start_date < end_date)', 'Error ! Dates are not consistent.'),
        ('unique_name', 'unique(name)', 'Error: Calendar name must be unique.'),
    ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=64, required=True, default='%s %s'%(_('Year'), time.strftime('%Y')))
    start_date = fields.Date(required=True, default='%s-01-01'%(time.strftime('%Y')))
    end_date = fields.Date(required=True, default='%s-12-31'%(time.strftime('%Y')))
    calendar_template_line_ids = fields.One2many('calendar.template.line', 'calendar_template_id',  string='Calendar template lines')
    calendar_ids = fields.One2many('calendar', 'calendar_template_id',  string='Calendars attached to the template', readonly=True)
    

class calendar_template_line(models.Model):
    """
    Calendar template line
    """
    _name = 'calendar.template.line'
    _description = 'Calendar template line'
    _order = 'start_date asc, end_date asc'
    _rec_name = 'calendar_template_id'
    _sql_constraints = [
        ('check_line_dates', 'check(start_date < end_date)', _('Error ! Dates are not consistent.')),
    ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    calendar_template_id = fields.Many2one('calendar.template', string='Calendar template', required=True, ondelete='cascade', select=True)
    start_date = fields.Datetime(required=True)
    end_date = fields.Datetime(required=True)
    hour = fields.Float(required=True)

    @api.one
    @api.constrains('start_date', 'end_date')
    def _check_dates_overlap(self):
        """
            Test qu'il ne peut pas y avoir de chevauchement entre les modèles lignes
        """
        have_overlap = bool(self.search([
                                  '&', '&', 
                                  ('id','!=', self.id), 
                                  ('calendar_template_id','=', self.calendar_template_id.id), 
                                  '|', '&', 
                                  ('start_date','>=', self.start_date),
                                  ('start_date','<', self.end_date), 
                                  '&',('end_date','>', self.start_date),
                                  ('end_date','<=', self.end_date)]))
        
        if have_overlap:
            raise except_orm(_('Error'), _('Lines can not overlap.'))
        
        return True
    
    
    @api.model
    def create(self, vals):
        """
            Crée les templates de lignes du template de calendrier
        """
        res = super(calendar_template_line, self).create(vals)
        if vals and ('calendar_template_id' in vals):
            calendar_obj = self.env['calendar']
            calendar_line_obj = self.env['calendar.line']
            for calendar_id in calendar_obj.search([('calendar_template_id', '=', vals['calendar_template_id'])]):
                calendar_line_obj.create({
                              'calendar_id': calendar_id.id, 
                              'calendar_template_line_id': res.id,
                              'start_date_related': res.start_date,
                              'end_date_related': res.end_date,
                              'real_start_date': res.start_date,
                              'real_end_date': res.end_date,
                                        })
                
        return res
    
    
class calendar(models.Model):
    """ 
    Calendar 
    """
    _name = 'calendar'
    _description = 'Calendar'
    _inherits = {'calendar.template': 'calendar_template_id'}
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=64, required=False)
    calendar_template_id = fields.Many2one('calendar.template', string='Template', required=True, ondelete='restrict')
    calendar_line_ids = fields.One2many('calendar.line', 'calendar_id',  string='Calendar lines')


    @api.one
    @api.onchange('calendar_template_id')
    def onchange_name_calendar_template_id(self):
        self.name = self.calendar_template_id.name
    
    
    @api.one
    def import_lines(self):
        """
            Importe les templates de lignes du template de calendrier
            :type self: calendar
            :rtype: bool
        """
        calendar_line_obj = self.env['calendar.line']
        self.calendar_line_ids.unlink()
        for template_line in self.calendar_template_id.calendar_template_line_ids:
            calendar_line_obj.create({
                          'calendar_id': self.id, 
                          'calendar_template_line_id': template_line.id,
                          'start_date_related': template_line.start_date,
                          'end_date_related': template_line.end_date,
                          'real_start_date': template_line.start_date,
                          'real_end_date': template_line.end_date,
                                    })
        return True


    def get_lines_interval(self, date_from, date_to):
        """
            Renvoie les lignes comprises dans un intervalle de deux dates
            :type self: calendar
            :param date_from: Date de début
            :type date_from: char format datetime
            :param date_to: Date de fin
            :type date_to: char format datetime
            :return: Liste des lignes valides
            :rtype: recordset: calendar.line
        """
        if self.id:
            line_ids = self.env['calendar.line'].search([
                                     ('real_start_date', '>=', date_from), 
                                     ('real_start_date', '<=', date_to), 
                                     ('calendar_id', '=', self.id)
                                                    ])
        else:
            line_ids = []
        
        return line_ids


    # Utiliser plutot "get_all_lines_from_date"
    def get_all_lines_interval(self, date_from, date_to):
        """
            Renvoie les lignes comprises dans un intervalle de deux dates
            en prenant en compte les lignes qui commencent avant la date de début
            passée en paramètre (ne prend pas en compte les exceptions)
            :type self: calendar
            :param date_from: Date de début
            :type date_from: char format datetime
            :param date_to: Date de fin
            :type date_to: char format datetime
            :return: Liste des lignes valides
            :rtype: recordset: calendar.line
        """
        if self.id:
            line_ids = self.env['calendar.line'].search([
                                     '&', ('calendar_id', '=', self.id), '|',
                                     '&',
                                     ('real_start_date', '>=', date_from), 
                                     ('real_start_date', '<=', date_to), 
                                     '&',
                                     ('real_end_date', '>', date_from), 
                                     ('real_end_date', '<=', date_to), 
                                                    ])
        else:
            line_ids = []
        
        return line_ids


    def get_all_lines_from_date(self, date_from, date_to):
        """
            Renvoie les lignes comprises dans un intervalle de deux dates
            en prenant en compte les lignes qui commencent avant la date de début
            passée en paramètre et termine aprés la date de fin passée en paramètre
            (ne prend pas en compte les exceptions)
            :type self: calendar
            :param date_from: Date de début
            :type date_from: char format datetime
            :param date_to: Date de fin
            :type date_to: char format datetime
            :return: Liste des lignes valides
            :rtype: recordset: calendar.line
        """
        if self.id:
            line_ids = self.env['calendar.line'].search([
                ('calendar_id', '=', self.id),
                ('real_start_date', '<', date_to),
                ('real_end_date', '>', date_from)
            ])
        else:
            line_ids = []
        
        return line_ids
    
    
    def get_compute_hours_interval(self, date_from, date_to):
        """
            Renvoie les temps travailles des lignes comprises dans un intervalle de deux dates
            :type self: calendar
            :param date_from: Date de début
            :type date_from: char format datetime
            :param date_to: Date de fin
            :type date_to: char format datetime
            :return: Les temps de travail
            :rtype: float
        """
        hours = 0.0
        line_rcs = self.get_lines_interval(date_from, date_to)
        for line in line_rcs:
            hours += line.hour
        
        return hours
    
    
    def get_lines(self, date_start):
        """
            Renvoie les lignes valides pour une date de début donnée
            :type self: calendar
            :param date_start: Date de début
            :type date_start: char format datetime
            :return: Liste des lignes valides
            :rtype: recordset: calendar.line
        """
        if self.id:
            line_ids = self.env['calendar.line'].search([
                                     ('real_end_date', '>=', date_start), 
                                     ('calendar_id', '=', self.id)
                                                   ])
        else:
            line_ids = []
            
        return line_ids
    
    
    def get_lines_inverse(self, date_end):
        """
            Renvoie les lignes valides pour une date de fin donnée
            :type self: calendar
            :param date_end: Date de fin
            :type date_end: char format datetime
            :return: Liste des lignes valides
            :rtype: recordset: calendar.line
        """
        if self.id:
            line_ids = self.env['calendar.line'].search([
                                     ('real_start_date', '<=', date_end), 
                                     ('calendar_id', '=', self.id)
                                                   ], order='real_start_date desc, real_end_date desc')
        else:
            line_ids = []

        return line_ids
    
    
    def get_avg_hours(self):
        """
        Nombre d'heure travaillé en moyenne sur un calendrier
        """
        return 7
    
    
    def get_dates(self, date_start, time, dico_create_load=None, limit=False):
        """
            Renvoie la date de début et la date de fin en fonction d'une date de début souhaitée et d'un temps
            :type self: calendar
            :param date_start: Date de début
            :type date_start: char format datetime
            :param time: Temps en heure
            :type time: float
            :param dico_create_load: Si le dico est remplis on crée une ligne de charge pour chaque ligne de calendrier
            :type dico_create_load: Dico {}
            :param limit: Permet de ne pas prendre toutes les lignes en même temps mais n par n n étant le paramètre limit
            :type limit: integer
            :return: Date de début et de fin sous la forme {'start_date': ..., 'end_date': ...}
            :rtype: dict {char: char}
        """
        # Renvoie la date de début et la date de fin en fonction d'une date de début souhaitée et d'un temps
        if not limit:
            limit = int((time / (self.get_avg_hours() - 1) or 1)) or 1
        
        res = {'start_date': False, 'end_date': False}
        loading_obj = self.env['calendar.loading']
        cal_line_obj = self.env['calendar.line']
        calendar_lines = self.get_lines(date_start).ids
        final_line = False
        if calendar_lines:
            hashed_label_ids = hash_list(calendar_lines, limit)
            first = True
            for calendar_lines in hashed_label_ids:
                # Pour chaque ligne, on soustrait les heures de la journée aux heures à faire
                for line in cal_line_obj.browse(calendar_lines).read(['real_start_date', 'real_end_date', 'real_hour', 'start_date']):
                    time_before = time
                    if first:
                        res['start_date'] = max(date_start, line['real_start_date'])
                        time_temp = cal_line_obj._get_availability_start(res['start_date'], line['real_start_date'], line['real_end_date'], line['real_hour'])
                        time -= time_temp
                        # Intinialisation des valeurs, si l'on veut créer un enregistrement dans la table de charge
                        date_start_loading = res['start_date']
                        if time <= 0:
                            loading = time_before
                        else:
                            loading = time_temp
                        
                    else:
                        time -= line['real_hour']
                        # Intinialisation des valeurs, si l'on veut créer un enregistrement dans la table de charge
                        date_start_loading = line['start_date']
                        if time <= 0:
                            loading = time_before
                        else:
                            loading = line['real_hour']
                        
                    # Création de la ligne de charge si dico_create_load est rempli
                    if dico_create_load and isinstance(dico_create_load, dict):
                        date_start_loading_modif = '%s'%(date_start_loading[0:10])
                        date_start_loading_modif = datetime.strptime(date_start_loading_modif, '%Y-%m-%d')
                        isocal = date_start_loading_modif.isocalendar()
                        # Sur 2 caractères
                        if len(str(isocal[1])) == 1:
                            week_number_loading = '0%s'%(str(isocal[1]))
                        else:
                            week_number_loading = str(isocal[1])
                        
                        # Sur 2 caractères
                        if len(str(date_start_loading_modif.month)) == 1:
                            month_loading = '0%s'%(str(date_start_loading_modif.month))
                        else:
                            month_loading = str(date_start_loading_modif.month)
                            
                        year_loading = str(isocal[0])
                        dico_create_load.update({'start_date': date_start_loading, 'calendar_line_id': line['id'], 
                                                 'loading': loading, 'week_number': week_number_loading,
                                                 'month': month_loading, 'year': year_loading})
                        loading_obj.create(dico_create_load)
                      
                    # S'il n'y a plus d'heure, on sort de la boucle en indiquant la derniere ligne
                    if time <= 0:
                        final_line = line
                        break
                    
                    first = False
                
                if final_line:
                    break
                    
                
            if final_line:
                res['end_date'] = (datetime.strptime(first and res['start_date'] or final_line['real_start_date'], DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(hours = time_before or 0.0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            
        return res
    
    
    def get_dates_inverse(self, date_end, time, dico_create_load=None, limit=False):
        """
            Renvoie la date de début et la date de fin en fonction d'une date de fin souhaitée et d'un temps
            :type self: calendar
            :param date_end: Date de fin
            :type date_end: char format datetime
            :param time: Temps en heure
            :type time: float
            :param dico_create_load: Si le dico est remplis on crée une ligne de charge pour chaque ligne de calendrier
            :type dico_create_load: Dico {}
            :param limit: Permet de ne pas prendre toutes les lignes en même temps mais n par n n étant le paramètre limit
            :type limit: integer
            :return: Date de début et de fin sous la forme {'start_date': ..., 'end_date': ...}
            :rtype: dict {char: char}
        """
        # Renvoie la date de début et la date de fin en fonction d'une date de début souhaitée et d'un temps
        if not limit:
            limit = int((time / (self.get_avg_hours() - 1) or 1)) or 1

        res = {'start_date': False, 'end_date': False}
        loading_obj = self.env['calendar.loading']
        cal_line_obj = self.env['calendar.line']
        final_line = False
        first = True
        # Récupération des lignes de calendrier
        calendar_lines = self.get_lines_inverse(date_end).ids
        if calendar_lines:
            hashed_label_ids = hash_list(calendar_lines, limit)
            for calendar_lines in hashed_label_ids:
                # Pour chaque ligne, on soustrait les heures de la journée aux heures à faire
                for line in cal_line_obj.browse(calendar_lines).read(['real_end_date', 'real_start_date', 'real_hour', 'start_date']):
                    time_before = time
                    if first:
                        if line['real_start_date'] <= date_end <= line['real_end_date']:
                            res['end_date'] = date_end
                        else:
                            res['end_date'] = line['real_end_date']
                            
                        time_temp = cal_line_obj._get_availability_end(res['end_date'], line['real_end_date'], line['real_start_date'], line['real_hour'])
                        time -= time_temp
                        # Intinialisation des valeurs, si l'on veut créer un enregistrement dans la table de charge
                        if time <= 0:
                            loading = time_before
                            date_start_loading = (datetime.strptime(res['end_date'], DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(hours = time_before or 0.0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        else:
                            loading = time_temp
                            date_start_loading = line['start_date']
                    else:
                        time -= line['real_hour']
                        # Intinialisation des valeurs, si l'on veut créer un enregistrement dans la table de charge
                        if time <= 0:
                            loading = time_before
                            date_start_loading = (datetime.strptime(line['real_end_date'], DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(hours = time_before or 0.0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        else:
                            loading = line['real_hour']
                            date_start_loading = line['start_date']
                    
                    # Création de la ligne de charge si dico_create_load est rempli
                    if dico_create_load and isinstance(dico_create_load, dict):
                        date_start_loading_modif = '%s'%(date_start_loading[0:10])
                        date_start_loading_modif = datetime.strptime(date_start_loading_modif, '%Y-%m-%d')
                        isocal = date_start_loading_modif.isocalendar()
                        # Sur 2 caractères
                        if len(str(isocal[1])) == 1:
                            week_number_loading = '0%s'%(str(isocal[1]))
                        else:
                            week_number_loading = str(isocal[1])
                        
                        # Sur 2 caractères
                        if len(str(date_start_loading_modif.month)) == 1:
                            month_loading = '0%s'%(str(date_start_loading_modif.month))
                        else:
                            month_loading = str(date_start_loading_modif.month)
                            
                        year_loading = str(isocal[0])
                        
                        dico_create_load.update({'start_date': date_start_loading, 'calendar_line_id': line['id'], 
                                                 'loading': loading, 'week_number': week_number_loading,
                                                 'month': month_loading, 'year': year_loading})
                        loading_obj.create(dico_create_load)
                    
                    
                    # S'il n'y a plus d'heure, on sort de la boucle en indiquant la derniere ligne
                    if time <= 0:
                        final_line = line
                        break
                    
                    first = False
                        
                if final_line:
                    break
                
            if final_line:
                res['start_date'] = (datetime.strptime(first and res['end_date'] or final_line['real_end_date'], DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(hours = time_before or 0.0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
        return res
    
    
    def get_dates_inverse_old(self, date_end, time, dico_create_load=None):
        """
            Renvoie la date de début et la date de fin en fonction d'une date de fin souhaitée et d'un temps
            :type self: calendar
            :param date_end: Date de fin
            :type date_end: char format datetime
            :param time: Temps en heure
            :type time: float
            :param dico_create_load: Si le dico est remplis on crée une ligne de charge pour chaque ligne de calendrier
            :type dico_create_load: Dico {}
            :return: Date de début et de fin sous la forme {'start_date': ..., 'end_date': ...}
            :rtype: dict {char: char}
        """
        res = {'start_date': False, 'end_date': False}
        loading_obj = self.env['calendar.loading']
        final_line = False
        time_before = False
        first = True
        # Récupération des lignes de calendrier
        calendar_lines = self.get_lines_inverse(date_end)
        if calendar_lines:
            if calendar_lines[0].real_start_date <= date_end <= calendar_lines[0].real_end_date:
                res['end_date'] = date_end
            else:
                res['end_date'] = calendar_lines[0].real_end_date
            
            # Pour chaque ligne, on soustrait les heures de la journée aux heures à faire
            for line in calendar_lines:
                time_before = time
                if first:
                    time_temp = line.get_availability_end(res['end_date'])
                    time -= time_temp
                    # Intinialisation des valeurs, si l'on veut créer un enregistrement dans la table de charge
                    if time <= 0:
                        loading = time_before
                        date_start_loading = (datetime.strptime(res['end_date'], DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(hours = time_before or 0.0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    else:
                        loading = time_temp
                        date_start_loading = line.start_date
                else:
                    time -= line.real_hour
                    # Intinialisation des valeurs, si l'on veut créer un enregistrement dans la table de charge
                    if time <= 0:
                        loading = time_before
                        date_start_loading = (datetime.strptime(line.real_end_date, DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(hours = time_before or 0.0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    else:
                        loading = line.real_hour
                        date_start_loading = line.start_date
                
                # Création de la ligne de charge si dico_create_load est rempli
                if dico_create_load and isinstance(dico_create_load, dict):
                    date_start_loading_modif = '%s'%(date_start_loading[0:10])
                    date_start_loading_modif = datetime.strptime(date_start_loading_modif, '%Y-%m-%d')
                    isocal = date_start_loading_modif.isocalendar()
                    # Sur 2 caractères
                    if len(str(isocal[1])) == 1:
                        week_number_loading = '0%s'%(str(isocal[1]))
                    else:
                        week_number_loading = str(isocal[1])
                    
                    # Sur 2 caractères
                    if len(str(date_start_loading_modif.month)) == 1:
                        month_loading = '0%s'%(str(date_start_loading_modif.month))
                    else:
                        month_loading = str(date_start_loading_modif.month)
                        
                    year_loading = str(isocal[0])
                    
                    dico_create_load.update({'start_date':date_start_loading, 'calendar_line_id':line.id, 
                                             'loading':loading, 'week_number':week_number_loading,
                                             'month':month_loading, 'year':year_loading})
                    loading_obj.create(dico_create_load)
                
                
                # S'il n'y a plus d'heure, on sort de la boucle en indiquant la derniere ligne
                if time <= 0:
                    final_line = line
                    break
                
                first = False
                
            if final_line:
                res['start_date'] = (datetime.strptime(first and res['end_date'] or final_line.real_end_date, DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(hours = time_before or 0.0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
        return res
    
    
    def get_date(self, date_start, day_nb, hours=False):
        """
            Renvoie la date la date de fin en fonction d'une date de début souhaitée et d'un nombre de jours
            :type self: calendar
            :param date_start: Date de début
            :type date_start: char format datetime
            :param day_nb: Nombre de jours
            :type day_nb: int
            :param hours: Permet de retourner la date sous forme date heure
            :type hours: boolean
            :return: Date de fin
            :rtype: char format date ou datetime 
        """
        line_rs = self.env['calendar.line'].search([
                                 ('real_end_date', '>=', date_start), 
                                 ('calendar_id', '=', self.id)
                                               ], offset=day_nb, limit=1, order='real_start_date asc, real_end_date asc')
        if line_rs:
            res = line_rs.read(['real_start_date'])[0]['real_start_date']
        else:
            raise except_orm(_("Error"), _("You must have more calendar line."))
            
        return res and (hours and res or res[:10]) or False
    
    
    # Avec gestion de plusieurs ligne par jour et une ligne pour plusieurs jours
    def get_date_old(self, date_start, day_nb, hours=False):
        """
            Renvoie la date la date de fin en fonction d'une date de début souhaitée et d'un nombre de jours
            :type self: calendar
            :param date_start: Date de début
            :type date_start: char format datetime
            :param day_nb: Nombre de jours
            :type day_nb: int
            :param hours: Permet de retourner la date sous forme date heure
            :type hours: boolean
            :return: Date de fin
            :rtype: char format date ou datetime 
        """
        res = False
        lines = self.get_lines(date_start)
        if lines and day_nb:
            t = 0
            l = 1
            jump = 0
            res_date = False
            res_date_hours = False
            len_lines = len(lines)
            for i in reversed(range(int(day_nb))):
                # Permet de passer des jours si il y a des lignes sur plusieurs jours
                if jump:
                    jump -= 1
                    continue
                
                if l >= len_lines:
                    raise except_orm(_("Error"), _("You must have more calendar line."))
                
                # Si les lignes sont sur une journée
                if lines[t].real_start_date[:10] == lines[t].real_end_date[:10]:
                    # Permet de passer si plusieurs lignes sur une journée
                    while lines[t].real_start_date[:10] == lines[l].real_start_date[:10]:
                        if l >= len_lines:
                            raise except_orm(_("Error"), _("You must have more calendar line."))
                        
                        t = l
                        l +=1
                        
                    if lines[l].real_start_date[:10] == lines[l].real_end_date[:10]:
                        t = l
                        l +=1
                    else:
                        delta = (datetime.strptime(lines[l].real_end_date[:10], DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(lines[l].real_start_date[:10], DEFAULT_SERVER_DATE_FORMAT))
                        if i == delta.days:
                            res_date = lines[t].real_end_date[:10]
                            res_date_hours = lines[t].real_start_date
                            break
                        elif i <  delta.days:
                            date_date = datetime.strptime(lines[l].real_start_date[:10], DEFAULT_SERVER_DATE_FORMAT)
                            res_date = (date_date + timedelta(i)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                            date_date_hours = datetime.strptime(lines[l].real_start_date, DEFAULT_SERVER_DATETIME_FORMAT)
                            res_date_hours = (date_date_hours + timedelta(i)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            break
                        else:
                            jump = delta.days + 1
                            t = l + 1
                            l +=2
                            
                # Si les lignes sont sur plusieurs jours
                else:
                    delta = (datetime.strptime(lines[t].real_end_date[:10], DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(lines[t].real_start_date[:10], DEFAULT_SERVER_DATE_FORMAT))
                    if i == delta.days:
                        res_date = lines[t].real_end_date[:10]
                        res_date_hours = lines[t].real_start_date
                        break
                    elif i < delta.days:
                        date_date1 = datetime.strptime(lines[t].real_start_date[:10], DEFAULT_SERVER_DATE_FORMAT)
                        res_date = (date_date1 + timedelta(i)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                        date_date1_hours = datetime.strptime(lines[t].real_start_date, DEFAULT_SERVER_DATETIME_FORMAT)
                        res_date_hours = (date_date1_hours + timedelta(i)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        break
                    else: 
                        jump = delta.days + 1
                        t = l + 1 
                        l +=2
                        
            if res_date:
                res = res_date
            else:
                res = lines[t].real_end_date[:10]
            
            if hours:
                if res_date_hours:
                    res = res_date_hours
                else:
                    res = lines[t].real_start_date
                
        else:
            res = date_start
            
        return res
    

    def get_date_inverse(self, date_end, day_nb, hours=False):
        """
            Renvoie la date de début en fonction d'une date de fin souhaitée et d'un nombre de jours
            :type self: calendar
            :param date_end: Date de fin
            :type date_end: char format datetime
            :param day_nb: Nombre de jours
            :type day_nb: int
            :param hours: Permet de retourner la date sous forme date heure
            :type hours: boolean
            :return: Date de début
            :rtype: char format date ou datetime
        """
        line_rs = self.env['calendar.line'].search([
                         ('real_start_date', '<=', date_end), 
                         ('calendar_id', '=', self.id)
                                       ], offset=day_nb, limit=1, order='real_start_date desc, real_end_date desc')
        if line_rs:
            res = line_rs.read(['real_end_date'])[0]['real_end_date']
        else:
            raise except_orm(_("Error"), _("You must have more calendar line."))
            
        return res and (hours and res or res[:10]) or False
    
    
    def get_date_inverse_old(self, date_end, day_nb, hours=False):
        """
            Renvoie la date de début en fonction d'une date de fin souhaitée et d'un nombre de jours
            :type self: calendar
            :param date_end: Date de fin
            :type date_end: char format datetime
            :param day_nb: Nombre de jours
            :type day_nb: int
            :param hours: Permet de retourner la date sous forme date heure
            :type hours: boolean
            :return: Date de début
            :rtype: char format date ou datetime
        """
        res = False
        lines = self.get_lines_inverse(date_end)
        if lines and day_nb:
            t = 0
            l = 1
            jump = 0
            res_date = False
            res_date_hours = False
            len_lines = len(lines)
            for i in reversed(range(int(day_nb))):
                # Permet de passer des jours si il y a des lignes sur plusieurs jours
                if jump:
                    jump -= 1
                    continue
                
                if l >= len_lines:
                    raise except_orm(_("Error"), _("You must have more calendar line."))
                
                # Si les lignes sont sur une journée
                if lines[t].real_start_date[:10] == lines[t].real_end_date[:10]:
                    # Permet de passer si plusieurs lignes sur une journée
                    while lines[t].real_start_date[:10] == lines[l].real_start_date[:10]:
                        t = l
                        l +=1
                        if l >= len_lines:
                            raise except_orm(_("Error"), _("You must have more calendar line."))
                        
                    if lines[l].real_start_date[:10] == lines[l].real_end_date[:10]:
                        t = l
                        l +=1
                    else:
                        delta = (datetime.strptime(lines[l].real_end_date[:10], DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(lines[l].real_start_date[:10], DEFAULT_SERVER_DATE_FORMAT))
                        if i == delta.days:
                            res_date = lines[t].real_end_date[:10]
                            res_date_hours = lines[t].real_end_date
                            break
                        elif i <  delta.days:
                            date_date = datetime.strptime(lines[l].real_start_date[:10], DEFAULT_SERVER_DATE_FORMAT)
                            res_date = (date_date + timedelta(i)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                            
                            date_date_hours = datetime.strptime(lines[l].real_start_date, DEFAULT_SERVER_DATETIME_FORMAT)
                            res_date_hours = (date_date_hours + timedelta(i)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            
                            break
                        else: 
                            jump = delta.days + 1
                            t = l + 1
                            l +=2
                            
                # Si les lignes sont sur plusieurs jours          
                else:
                    delta = (datetime.strptime(lines[t].real_end_date[:10], DEFAULT_SERVER_DATE_FORMAT) - datetime.strptime(lines[t].real_start_date[:10], DEFAULT_SERVER_DATE_FORMAT))
                    if i == delta.days:
                        res_date = lines[t].real_end_date[:10]
                        res_date_hours = lines[t].real_end_date
                        break
                    elif i < delta.days:
                        date_date1 = datetime.strptime(lines[t].real_start_date[:10], DEFAULT_SERVER_DATE_FORMAT)
                        res_date = (date_date1 + timedelta(i)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                        
                        date_date1_hours = datetime.strptime(lines[t].real_start_date, DEFAULT_SERVER_DATETIME_FORMAT)
                        res_date_hours = (date_date1_hours + timedelta(i)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        break
                    else: 
                        jump = delta.days + 1
                        t = l + 1
                        l +=2
                        
            if res_date:
                res = res_date
            else:
                res = lines[t].real_end_date[:10]
            
            if hours:
                if res_date_hours:
                    res = res_date_hours
                else:
                    res = lines[t].real_end_date
                
        else:
            res = date_end[:10]
            if hours:
                res = date_end
            
        return res
    
    
    def get_all_days(self):
        # Passage en C.UTF-8 pour avoir les jours en anglais
        saved = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, 'C.UTF-8') 
        res = [datetime_date(2001, 1, i).strftime('%A').lower() for i in range(1, 8)]
        locale.setlocale(locale.LC_ALL, saved)
        return res
        
    
    def get_month_dates(self, month, year):
        # Renvoie la date de début et la date de fin d'un mois
        res = {'start_date': False, 'end_date': False}
        date_format = '%Y-%m-%d %H:%M:%S'
        res['start_date'] = '%04d-%02d-01 00:00:00'%(year, month)
        res['end_date'] = (datetime.strptime(res['start_date'], date_format) + relativedelta(months = 1)).strftime(date_format) 
        return res
    
        
    def get_days_of_month(self, str_date, compute_days):
        """
            Renvoie un dictionnaire sous la forme 
            {
                'monday': ['2017-03-06', '2017-03-13', '2017-03-20', '2017-03-27', ]
                'wednesday': ['2017-03-06', '2017-03-13', '2017-03-20', '2017-03-27', ]
                'thursday': ['2017-03-06', '2017-03-13', '2017-03-20', '2017-03-27', ]
            }
            en fonction du mois de la date passée en paramètre et des jours de calcul passés en paramètre
        """
        date_format = '%Y-%m-%d'
        datetime_format = '%Y-%m-%d %H:%M:%S'
        all_days = self.get_all_days()
        res = {key: [] for key in compute_days}
        date_date = datetime.strptime(str_date, date_format)
        dates = self.get_month_dates(date_date.month, date_date.year)
        line_rcs = self.get_lines_interval(dates['start_date'], dates['end_date'])
        for line_rc in line_rcs:
            start_date = datetime.strptime(line_rc.real_start_date, datetime_format)
            end_date = datetime.strptime(line_rc.real_end_date, datetime_format)
            # Gestion si plusieurs lignes par jours
            for date in [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]:
                if all_days[date.weekday()] in compute_days:
                    if all_days[date.weekday()] in res:
                        str_date = str(date)[:10]
                        if str_date not in res[all_days[date.weekday()]]:
                            res[all_days[date.weekday()]].append(str_date)
                            
                    else:
                        res[all_days[date.weekday()]] = [str(date)]

        return res
    
    
    def get_week_dates(self, date):
        # Renvoie la date de début et la date de fin d'un mois
        res = {'start_date': False, 'end_date': False}
        date_format = '%Y-%m-%d'
        datetime_format = '%Y-%m-%d %H:%M:%S'
        dt = datetime.strptime(date, date_format)
        start_date = dt - timedelta(days=dt.weekday())
        res['start_date'] = (start_date).strftime(datetime_format)
        res['end_date'] = (start_date + timedelta(days=6)).strftime(datetime_format)
        return res
    
        
    def get_days_of_week(self, str_date, compute_days):
        """
            Renvoie un dictionnaire sous la forme 
            {
                'monday': '2017-02-27'
                'wednesday': '2017-03-01'
                'thursday': '2017-03-02'
            }
            en fonction de la semaine de la date passée en paramètre et des jours de calcul passés en paramètre
        """
        datetime_format = '%Y-%m-%d %H:%M:%S'
        all_days = self.get_all_days()
        res = {key: '' for key in compute_days}
        dates = self.get_week_dates(str_date)
        line_rcs = self.get_lines_interval(dates['start_date'], dates['end_date'])
        for line_rc in line_rcs:
            start_date = datetime.strptime(line_rc.real_start_date, datetime_format)
            end_date = datetime.strptime(line_rc.real_end_date, datetime_format)
            # Gestion si plusieurs lignes par jours
            for date in [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]:
                if all_days[date.weekday()] in compute_days:
                    res[all_days[date.weekday()]] = str(date)

        return res



class calendar_line(models.Model):
    """ 
    Calendar line 
    """
    _name = 'calendar.line'
    _rec_name = 'calendar_id'
    _description = 'Calendar line'
    
    @api.one
    @api.depends('start_date_exception', 'end_date_exception', 'hour_exception', 'calendar_template_line_id.start_date', 'calendar_template_line_id.end_date', 'calendar_template_line_id.hour')
    def _real_fields_compute(self):
        """
        Réel = Exception ou Template
        """
        self.real_start_date = self.start_date_exception or self.start_date_related
        self.real_end_date = self.end_date_exception or self.end_date_related
        self.real_hour = self.hour_exception < 0 and self.hour_related or self.hour_exception
        
            

    #===========================================================================
    # COLUMNS
    #===========================================================================
    calendar_template_line_id = fields.Many2one('calendar.template.line', string='Calendar template line', required=False, ondelete='cascade', select=True)
    calendar_id = fields.Many2one('calendar', string='Calendar', required=False, ondelete='cascade', select=True)
    
    start_date_related = fields.Datetime(related='calendar_template_line_id.start_date', string='Start date', store=True, readonly=True)
    end_date_related = fields.Datetime(related='calendar_template_line_id.end_date', string='End date', store=True, readonly=True)
    hour_related = fields.Float(related='calendar_template_line_id.hour', string='Hour', required=False, readonly=True)
    
    start_date_exception = fields.Datetime()
    end_date_exception = fields.Datetime()
    hour_exception = fields.Float(default=-1, required=False, help='To disable exception, give it a negative value')
    
    real_start_date = fields.Datetime(compute='_real_fields_compute', store=True, select=True)
    real_end_date = fields.Datetime(compute='_real_fields_compute', store=True, select=True)
    real_hour = fields.Float(compute='_real_fields_compute', store=True, select=True)
    
    start_date = fields.Datetime(related='calendar_template_line_id.start_date', required=False, readonly=True)
    end_date = fields.Datetime(related='calendar_template_line_id.end_date', required=False, readonly=True)
    hour = fields.Float(related='calendar_template_line_id.hour', required=False, readonly=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super(calendar_line, self).default_get(fields_list)
        res['start_date_exception'] = self.env.context.get('default_real_start_date')
        res['end_date_exception'] = self.env.context.get('default_real_end_date')
        res['start_date'] = self.env.context.get('default_real_start_date')
        res['end_date'] = self.env.context.get('default_real_end_date')
        res['hour'] = self.env.context.get('default_real_hour')
        return res
    
    
    def _get_line_time(self, start_date, end_date=False):
        """
            Renvoie le temps pris sur chaque ligne en fonction d'un temps d'une date de début et d'une date de fin
            :type self: calendar.line
            :param start_date: Date de début
            :type start_date: char format datetime
            :param end_date: Date de fin
            :type end_date: char format datetime
            :return: Dictionnaire sous forme {id_ligne: temps}
            :rtype: dict {int: float}
        """
        res = {}.fromkeys(self.ids, 0.0)
        for line in self:
            cal_start_date = line.real_start_date
            cal_end_date = line.real_end_date
            
#            Légende:
#                x     = date
#            |-------| = ligne de calendrier
            
            if not end_date or start_date == end_date:
                res[line.id] = 0.0
                
            # x |-------| x
            # Si les dates couvrent toute la ligne
            if start_date <= cal_start_date and end_date >= cal_end_date:
                res[line.id] = line.real_hour
                
            # |-x---x-|
            # Si les dates sont toute les deux comprises dans la ligne
            elif cal_start_date < start_date and cal_end_date > end_date:
                res[line.id] = line.get_availability_start_end(start_date, end_date)

            # |-------| x x OU x x |-------|
            # Si aucune des dates n'est comprises dans la ligne
            elif cal_end_date <= start_date or cal_start_date >= end_date:
                res[line.id] = 0.0
                
            # x |---x---|
            elif start_date <= cal_start_date:
                res[line.id] = line.get_availability_end(end_date)
                
            # |---x---| x
            elif end_date >= cal_end_date:
                res[line.id] = line.get_availability_start(start_date)
                
            else:
                res[line.id] = 0.0
                
        return res
    
    
    def _get_availability_start(self, start_date, real_start_date, real_end_date, real_hour):
        """
            get_availability_start adaptée pour les read
        """
        max_date_start = max(start_date, real_start_date)
        delta = datetime.strptime(real_end_date, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(max_date_start, DEFAULT_SERVER_DATETIME_FORMAT)
        delta_hour = delta.seconds / 3600.0
        return min(delta_hour, real_hour)
    
    
    def get_availability_start(self, start_date):
        """
            Retourne le minimum entre les heures entrées dans la ligne de calendrier et le temps restant
            :type self: calendar.line
            :param start_date: Date de début
            :type start_date: char format datetime
            :return: Min entre les heures entrées dans la ligne de calendrier et le temps restant
            :rtype: float
        """
        return self._get_availability_start(start_date, self.real_start_date, self.real_end_date, self.real_hour)

    
    def _get_availability_end(self, end_date, real_end_date, real_start_date, real_hour):
        """
            get_availability_end adaptée pour les read
        """
        min_end_date = min(end_date, real_end_date)
        delta = datetime.strptime(min_end_date, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(real_start_date, DEFAULT_SERVER_DATETIME_FORMAT)
        delta_hour = delta.seconds / 3600.0
        return min(delta_hour, real_hour)
    
    
    def get_availability_end(self, end_date):
        """
            Retourne le minimum entre les heures entrées dans la ligne de calendrier et le temps restant
            :type self: calendar.line
            :param end_date: Date de fin
            :type end_date: char format datetime
            :return: Min entre les heures entrées dans la ligne de calendrier et le temps restant
            :rtype: float
        """
        return self._get_availability_end(end_date, self.real_end_date, self.real_start_date, self.real_hour)
    
    
    def get_availability_start_end(self, start_date, end_date):
        """
            Retourne le minimum entre les heures entrées dans la ligne et la différence entre les deux dates passées en parametre
            :type self: calendar.line
            :param start_date: Date de début
            :type start_date: char format datetime
            :param end_date: Date de fin
            :type end_date: char format datetime
            :return: Min entre les heures entrées dans la ligne et la différence entre les deux dates passées en parametre
            :rtype: float
        """
        delta = datetime.strptime(end_date, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(start_date, DEFAULT_SERVER_DATETIME_FORMAT)
        delta_hour = delta.seconds / 3600.0
        return min(delta_hour, self.real_hour)



class calendar_loading(models.Model):
    """ 
        Calendar Loading 
    """
    _name = 'calendar.loading'
    _description = 'Calendar Loading'
    _rec_name = 'start_date'
    _order = 'start_date asc'
    
    @api.model
    def _month_get(self):
        return [('00', _('Without month')), 
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
                ('12', _('December'))]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    start_date = fields.Datetime(string='Start Date')
    loading = fields.Float(string='Loading', default=0.0, required=False)
    calendar_line_id = fields.Many2one('calendar.line', string='Calendar Line', required=False, ondelete='cascade')
    month = fields.Selection('_month_get', string='Month')
    week_number = fields.Char(string='Week number', size=2) 
    year = fields.Char(string='Year', size=4)
    is_forecast = fields.Boolean(string='Forecast', default=False)
    