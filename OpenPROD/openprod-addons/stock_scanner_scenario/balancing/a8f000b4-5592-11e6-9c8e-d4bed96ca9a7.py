'Use <m> or <message> to retrieve the data transmitted by the scanner.'
'Use <t> or <terminal> to retrieve the running terminal browse record.'
'Put the returned action code in <act>, as a single character.'
'Put the returned result or message in <res>, as a list of strings.'
'Put the returned value in <val>, as an integer'
if type(message) == str:
    t.tmp_val1 = int(message)
act = 'T'
label = model.browse(int(t.tmp_val1))
res = [u'étiquette %s' % label.name, 'produit %s' % label.product_id.name, u'quantité actuelle : %s pce' % label.uom_qty, u'Nouvelle quantité?']
