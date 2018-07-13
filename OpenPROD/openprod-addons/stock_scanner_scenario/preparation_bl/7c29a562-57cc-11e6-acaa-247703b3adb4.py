'Use <m> or <message> to retrieve the data transmitted by the scanner.'
'Use <t> or <terminal> to retrieve the running terminal browse record.'
'Put the returned action code in <act>, as a single character.'
'Put the returned result or message in <res>, as a list of strings.'
'Put the returned value in <val>, as an integer'
if not t.tmp_val1:
    t.tmp_val1 = int(message)
    first_time = True
else:
    first_time = False
move = model.env['stock.move'].browse(int(t.tmp_val1))

#import sys;sys.path.append(r'/home/sylvain/.eclipse/org.eclipse.platform_3.8_155965261/plugins/org.python.pydev_4.1.0.201505270003/pysrc')
#import pydevd;pydevd.settrace()
ids_to_add = [] if not len(t.tmp_val2) else t.tmp_val2.split('|')
if not first_time and message != terminal.scenario_id.ack_code and int(message) not in [x.label_id.id for x in move.move_label_ids] and message not in ids_to_add:
    # add label
    ids_to_add.append(message)
    t.tmp_val2 = "|".join(ids_to_add)

act = 'N'
res = [
    u'BL : %s' % move.name,
    u'Qté demandée: %s' % move.initial_uom_qty,
    u'Produit : %s' % move.product_id.name,
    u'Client : %s' % move.picking_id.partner_id.name,
    u'Nombre d\'étiquette %s' % (len(move.move_label_ids) + len(ids_to_add)),
    u'Qté préparée: %s' % move.uom_qty,
    u'Scan étiquette %s ?' % (len(move.move_label_ids) + len(ids_to_add) + 1),
]