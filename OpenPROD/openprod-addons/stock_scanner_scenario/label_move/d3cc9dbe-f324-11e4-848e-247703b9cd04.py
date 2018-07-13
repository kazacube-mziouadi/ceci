import gettext

# tmp_val1: Navigation
# tmp_val2: Values: {'location': {'name': ..., 'id: ...}, 'label': {'name': ..., 'id': ...}
# tmp_val3: Messages
# tmp_val4: Gestion erreur
# tmp_val5: /

# Si entré dans le programme: demande de l'emplacement
c = True
while c:
    if t.tmp_val4:
        t.write({'tmp_val4': ''})
    values = t.tmp_val2 and eval(t.tmp_val2) or {}
    if not t.tmp_val1:
        res = []
        if t.tmp_val3:
            res = ['----------------------------------------',
                   t.tmp_val3,
                   '----------------------------------------']
        act = 'T'
        res.append(_('Location?'))
        c = False
        t.write({'tmp_val1': '1'})
            
    elif t.tmp_val1 == '1':
        error = False
        if not values.get('location'):
            location_rs = pool['stock.location'].search([('barcode', '=', message)])
            if location_rs:
                t.write({'tmp_val2': str({'location': {'id': location_rs.id, 
                                                       'name': location_rs.name}})})
            else:
                act = 'E'
                res = [_('No location found with the given barcode'), '', message]
                c = False
                t.write({'tmp_val1': '', 'tmp_val4': '1'})
                error = True

        if not error:
            act = 'T'
            res = [_('Label number?')]
            t.write({'tmp_val1':'2'})
            c = False
        
    # Si étiquette entrée, verification de l'étiquette et mouvement
    elif t.tmp_val1 == '2':
        label_obj = model
        label_rs = label_obj.search([('name', '=', message)])
        if label_rs:
            location_datas = values['location']
            label_rs.move(location_id=location_datas['id'])
            t.write({'tmp_val1': '',
                     'tmp_val2': '',
                     'tmp_val3':_('INFO: Label %s was be moved on location %s')%(message, location_datas['name'])})
            
            
        else:
            t.write({'tmp_val1': '1', 'tmp_val4': '1'})
            act = 'E'
            res = [_('No label found with the given number'), '', message]
            c = False