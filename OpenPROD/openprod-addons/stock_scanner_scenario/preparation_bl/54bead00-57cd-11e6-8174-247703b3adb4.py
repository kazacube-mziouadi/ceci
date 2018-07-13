'Use <m> or <message> to retrieve the data transmitted by the scanner.'
'Use <t> or <terminal> to retrieve the running terminal browse record.'
'Put the returned action code in <act>, as a single character.'
'Put the returned result or message in <res>, as a list of strings.'
'Put the returned value in <val>, as an integer'

act = 'C'

move = model.env['stock.move'].browse(int(t.tmp_val1))
ids_to_add = [] if not len(t.tmp_val2) else t.tmp_val2.split('|')

res = [
    u'BL : %s' % move.name,
    u'Qté demandée: %s' % move.initial_uom_qty,
    u'Produit : %s' % move.product_id.name,
    u'Client : %s' % move.picking_id.partner_id.name,
    u'Nombre d\'étiquette %s' % (len(move.move_label_ids) + len(ids_to_add)),
    u'Qté préparée: %s' % move.uom_qty,
    u'Valider la préparation?',
]