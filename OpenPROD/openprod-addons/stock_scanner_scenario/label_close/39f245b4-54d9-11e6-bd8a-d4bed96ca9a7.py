'Use <m> or <message> to retrieve the data transmitted by the scanner.'
'Use <t> or <terminal> to retrieve the running terminal browse record.'
'Put the returned action code in <act>, as a single character.'
'Put the returned result or message in <res>, as a list of strings.'
'Put the returned value in <val>, as an integer'
label = model.search([('id', '=', int(message))])
t.tmp_val1 = label.id
act = 'C'
res = [u'Cloture étiquette ' + label.name, u'produit ' + label.product_id.name, u'qty = %s' % label.uom_qty]