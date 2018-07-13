# Use <m> or <message> to retrieve the data transmitted by the scanner.
# Use <t> or <terminal> to retrieve the running terminal browse record.
# Put the returned action code in <act>, as a single character.
# Put the returned result or message in <res>, as a list of strings.
# Put the returned value in <val>, as an integer

terminal.write({'tmp_val2': message}, context=context)

product_id = model.search(cr, uid, [('default_code', '=', message)], context=context)[0]
product = model.browse(cr, uid, product_id, context=context)

act = 'Q'
res = [
    'Product : [%s] %s' % (product.default_code, product.name),
    'UoM : %s' % product.uom_id.name,
    '',
    'Select quantity',
]
