'Use <m> or <message> to retrieve the data transmitted by the scanner.'
'Use <t> or <terminal> to retrieve the running terminal browse record.'
'Put the returned action code in <act>, as a single character.'
'Put the returned result or message in <res>, as a list of strings.'
'Put the returned value in <val>, as an integer'

def format_output(location_id):
    location = ""
    
    if location_id:
        location_brw = pool.get('stock.location').browse(cr, uid, location_id, context=context)
        if location_brw and location_brw.location_id:
            location = (location_brw.location_id.barcode or '') + " / " + (location_brw.barcode or '')
        else:
            location = location_brw.barcode or ''
    return location


product_obj = pool['product.product']
location_obj = pool['stock.location']

if t.tmp_val1 == '':
    act = 'T'
    res = ['Product ?']
    terminal.write({'tmp_val1':'1'})
    
elif t.tmp_val1 == '1':
    # product has been scanned
    # check it
    if t.tmp_val5:
        act = 'T'
        res = ['Qty ?']
        terminal.write({'tmp_val1':'2'})
        
    else:
        product_rs = product_obj.search([('code', '=', message)])
        if product_rs:
            terminal.write({'tmp_val1':'2', 'tmp_val5': str(product_rs.id)})
            act = 'T'
            res = ['Qty ?']
        else:
            # error, no product found with the given code
            act = 'E'
            res = ['no product found with the given code', '', message]
            terminal.write({'tmp_val1': ''})
    
elif t.tmp_val1 == '2':
    # Quantity has been scanned
    # check it
    if t.tmp_val4:
        act = 'T'
        res = ['SRC Location ?']
        terminal.write({'tmp_val1':'3'})
        
    else:
        qty = 0
        try:
            qty = float(message)
            terminal.write({'tmp_val1': '3', 'tmp_val4': str(qty)})
            act = 'T'
            res = ['SRC Location ?']
            
        except ValueError as e:
            act = 'E'
            res = ['Qty scanned is not an number', '', message]
            terminal.write({'tmp_val1': '1'})
    
elif t.tmp_val1 == '3':
    # SRC_LOCATION has been scanned
    # check it
    if t.tmp_val3:
        act = 'T'
        res = ['DST Location ?']
        terminal.write({'tmp_val1':'4'})
        
    else:
        location_rs = location_obj.search([('barcode', '=', message)])
        if location_rs:
            terminal.write({'tmp_val1':'4', 'tmp_val3': str(location_rs.id)})
            act = 'T'
            res = ['DST Location ?']
        
        else:
            # error, no location found with the given barcode
            act = 'E'
            res = ['no location found with the given barcode', '', message]
            terminal.write({'tmp_val1': '2'})
    
    
elif t.tmp_val1 == '4':
    # DST_LOCATION has been scanned
    # check it and go to the end
    
    location_rs = location_obj.search([('barcode', '=', message)])
    if location_rs:
        # location_dest_id found, so create move and go to the end step
        res_id = model.create_move_scanner(int(t.tmp_val5), int(t.tmp_val3), location_rs.id, qty=float(t.tmp_val4), uom=None)
        terminal.write({'tmp_val1':'0'})
        act = 'M'
        res = ['Move id = %s created' % (res_id) ]
    
    else:
        # error, no location found with the given barcode
        act = 'E'
        res = ['no location found with the given barcode', '', message]
        terminal.write({'tmp_val1': '3'})
    