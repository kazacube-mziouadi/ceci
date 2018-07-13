'Use <m> or <message> to retrieve the data transmitted by the scanner.'
'Use <t> or <terminal> to retrieve the running terminal browse record.'
'Put the returned action code in <act>, as a single character.'
'Put the returned result or message in <res>, as a list of strings.'
'Put the returned value in <val>, as an integer'

if type(message) == bool and message and t.tmp_val1 and t.tmp_val2:
    move = model.env['stock.move'].browse(int(t.tmp_val1))
    ids_to_add = [int(x) for x in ([] if not len(t.tmp_val2) else t.tmp_val2.split('|'))]
    move.assign_label(model.browse(ids_to_add), with_write=True)
else:
    t.tmp_val1 = ''
    t.tmp_val2 = ''

act = 'N'
res = [u'Bon de préparation', u'Scan ligne de BL?']