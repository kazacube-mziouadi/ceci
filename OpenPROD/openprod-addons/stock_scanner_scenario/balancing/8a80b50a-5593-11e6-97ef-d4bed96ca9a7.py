'Use <m> or <message> to retrieve the data transmitted by the scanner.'
'Use <t> or <terminal> to retrieve the running terminal browse record.'
'Put the returned action code in <act>, as a single character.'
'Put the returned result or message in <res>, as a list of strings.'
'Put the returned value in <val>, as an integer'
label = model.browse(int(t.tmp_val1))
new_qty = int(message.replace('Q', ''))
t.tmp_val2 = new_qty
act = 'C'
res = [u'Etiquette: %s' % label.name, u'Produit %s' % label.product_id.name, u'Quantité nouvelle : %s pce' % new_qty]