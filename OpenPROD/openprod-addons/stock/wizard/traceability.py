# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class traceability_wizard(models.TransientModel):
    """ 
    Traceability wizard
    """
    _name = 'traceability.wizard'
    _description = 'Traceability label'
    _parent_name = "parent_id"
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    initial_label_id = fields.Many2one('stock.label', string='Initial label', required=True, ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    parent_id = fields.Many2one('traceability.wizard')
    child_ids = fields.One2many('traceability.wizard', 'parent_id',  string='Childs')
    move_qty = fields.Float(string='Move quantity', default=0.0, required=False)
    source_id = fields.Many2one('stock.location', string='Source', required=False, ondelete='cascade')
    destination_id = fields.Many2one('stock.location', string='Destination', required=False, ondelete='cascade')
    move_date = fields.Datetime()
    
    
    @api.model
    def build_traceability_upstream(self, label_id):
        self.search([('initial_label_id', '=', label_id)]).unlink()
        # dernier mouvement pour l'étiquette
        sml = self.env['stock.move.label'].search([('label_id', '=', label_id)], order="done_date desc", limit=1)
        if len(sml):
            saved = self.save_line(sml, None)
            self.recursion_traceability_upstream(sml, saved)
        
    def recursion_traceability_upstream(self, sml, parent_id):
        wo_id = sml.move_id.wo_incoming_id or sml.move_id.wo_outgoing_id
        if not wo_id:
            prev_sml = self.env['stock.move.label'].search([('label_id', '=', sml.label_id.id), ('done_date', '<', sml.done_date)], order="done_date desc", limit=1)
            if not prev_sml:
                return
            prev_parent_id = self.save_line(prev_sml, parent_id)
            self.recursion_traceability_upstream(prev_sml, prev_parent_id)
            return
        prod_declaration_ids = wo_id.workorder_produce_ids
        for prod_declaration_id in prod_declaration_ids:
            decl_line_id = self.create({
                    'parent_id': parent_id.id,
                    'name': '%s %s' % (prod_declaration_id.wo_id.name_get()[0][1], prod_declaration_id.date),
                    'initial_label_id':parent_id.initial_label_id.id,
                    'move_qty': sml.uom_qty,
                    'source_id': sml.move_id.location_id.id,
                    'destination_id': sml.move_id.location_dest_id.id,
                    'move_date': sml.done_date,
                    })
            prev_prod_declaration_id = self.env['mrp.wo.produce'].search([('wo_id', '=', wo_id.id), ('date', '<', prod_declaration_id.date)], order="date desc", limit=1)
            domain = [
                                                                           ('wo_id', 'in', wo_id.mo_id.workorder_ids.ids),
                                                                           ('date', '<=', prod_declaration_id.date),
                                                                           ]
            if prev_prod_declaration_id:
                domain.append(('date', '>', prev_prod_declaration_id.date))
            conso_declaration_ids = self.env['mrp.wo.consumption'].search(domain)
            # on groupe les conso de toutes les déclarations par étiquettes
            prev_label_ids = set()
            for conso_declaration_id in conso_declaration_ids:
                prev_label_ids.update([y.label_id.id for x in conso_declaration_id.move_ids for y in x.move_label_ids])
            for label_id in prev_label_ids:
                new_sml = self.env['stock.move.label'].search([
                                                           ('label_id', '=', label_id), 
                                                           ('done_date', '<', prod_declaration_id.date),
                                                           ('move_id.type', '=', 'in')], order="done_date desc", limit=1)
                if new_sml:
                    new_parent_id = self.save_line(new_sml, decl_line_id)
                    self.recursion_traceability_upstream(new_sml, new_parent_id)
    
    def save_line(self, sml, parent_id):
        name = u"{}".format(sml.label_id.name)
        move_id = sml.move_id
        if move_id.purchase_line_id:
            name += u" {}".format(move_id.purchase_line_id.name_get()[0][1])
        elif move_id.sale_line_id:
            name += u" {}".format(move_id.sale_line_id.name_get()[0][1])
        elif move_id.wo_outgoing_id:
            name += u" {}".format(move_id.wo_outgoing_id.name_get()[0][1])
        elif move_id.wo_incoming_id:
            name += u" {}".format(move_id.wo_incoming_id.name_get()[0][1])
        elif move_id.picking_id:
            name += u" {}".format(move_id.picking_id.name_get()[0][1])
        else:
            name += _(" free move")
        
        name += u" {}".format(move_id.product_id.name)
        return self.create({
                    'parent_id': parent_id.id if parent_id else None,
                    'name': name,
                    'initial_label_id':parent_id.initial_label_id.id if parent_id else sml.label_id.id,
                    'move_qty': sml.uom_qty,
                    'source_id': move_id.location_id.id,
                    'destination_id': move_id.location_dest_id.id,
                    'move_date': sml.done_date,
                    })
    
    
    
    @api.model
    def build_traceability_downstream(self, label_id):
        self.search([('initial_label_id', '=', label_id)]).unlink()
        # dernier mouvement pour l'étiquette
        sml = self.env['stock.move.label'].search([('label_id', '=', label_id)], order="done_date asc", limit=1)
        if len(sml):
            saved = self.save_line(sml, None)
            self.recursion_traceability_downstream(sml, saved)
        
    def recursion_traceability_downstream(self, sml, parent_id):
        wo_id = sml.move_id.wo_outgoing_id or sml.move_id.wo_incoming_id
        if not wo_id:
            next_sml = self.env['stock.move.label'].search([('label_id', '=', sml.label_id.id), 
                                                            ('done_date', '>', sml.done_date)], order="done_date asc", limit=1)
            if not next_sml:
                return
            next_parent_id = self.save_line(next_sml, parent_id)
            self.recursion_traceability_downstream(next_sml, next_parent_id)
            return
        prod_consumption_ids = wo_id.workorder_consumption_ids
        for prod_consumption_id in prod_consumption_ids:
            decl_line_id = self.create({
                    'parent_id': parent_id.id,
                    'name': '%s %s' % (prod_consumption_id.wo_id.name_get()[0][1], prod_consumption_id.date),
                    'initial_label_id':parent_id.initial_label_id.id,
                    'move_qty': sml.move_id.uom_qty,
                    'source_id': sml.move_id.location_id.id,
                    'destination_id': sml.move_id.location_dest_id.id,
                    'move_date': sml.done_date,
                    })
            next_prod_consumption_id = self.env['mrp.wo.consumption'].search([('wo_id', '=', wo_id.id), ('date', '>', prod_consumption_id.date)], order="date desc", limit=1)
            domain = [
                                                                           ('wo_id', 'in', wo_id.mo_id.workorder_ids.ids),
                                                                           ('date', '>=', prod_consumption_id.date),
                                                                           ]
            if next_prod_consumption_id:
                domain.append(('date', '>', next_prod_consumption_id.date))
            conso_production_ids = self.env['mrp.wo.produce'].search(domain)
            # on groupe les conso de toutes les déclarations par étiquettes
            prev_label_ids = set()
            for conso_production_id in conso_production_ids:
                prev_label_ids.update([y.label_id.id for x in conso_production_id.move_ids for y in x.move_label_ids])
            for label_id in prev_label_ids:
                new_sml = self.env['stock.move.label'].search([
                                                           ('label_id', '=', label_id), 
                                                           ('done_date', '>', prod_consumption_id.date),
                                                           ('move_id.type', '=', 'out')], order="done_date asc", limit=1)
                if not new_sml:
                    return
                new_parent_id = self.save_line(new_sml, decl_line_id)
                self.recursion_traceability_downstream(new_sml, new_parent_id)
    
    