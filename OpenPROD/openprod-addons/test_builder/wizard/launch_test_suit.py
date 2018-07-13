# coding: utf-8
'''
Created on 30 juil. 2015

@author: sylvain
'''

from openerp import models, api, fields
import tempfile, os
from behave.configuration import Configuration
from behave.runner import Runner

class launch_test_suit(models.TransientModel):
    """ 
    description 
    """
    _name = 'launch.test.suit'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    batch_id = fields.Many2one('batch', string='Batch', required=False, ondelete='cascade')
    batch_ids = fields.Many2many('batch')
    scenario_id = fields.Many2one('scenario', string='Scenario', required=False, ondelete='cascade')
    scenario_line_id = fields.Many2one('scenario.line', string='Scenario Line', required=False, ondelete='cascade')
    lang_code = fields.Char(string='Lang code', size=5, default=lambda x: x.env['ir.config_parameter'].get_param('test_builder.default_lang'))
    target_id = fields.Many2one('target.db', string='Database', required=True, ondelete='cascade', default=lambda x: x.get_default_target())
    empty_batch = False
    
    def get_default_target(self):
        target_id = int(self.env['ir.config_parameter'].get_param('test_builder.default_target_db_id'))
        return self.env['target.db'].browse(target_id)
    
    @api.multi
    def launch_test_suit(self, context={}):
        if len(self.batch_ids):
            for batch_id in self.batch_ids:
                ret = self._launch_test_suit(batch_id, context)
            return ret
        else:
            return self._launch_test_suit(self.batch_id, context)
    
    def _launch_test_suit(self, batch_id, context={}):
        if self.scenario_line_id:
            test_text = self.get_text_for_scenario_line(self.scenario_line_id)
        elif self.scenario_id:
            test_text = self.get_text_for_scenario(self.scenario_id, empty_batch = True)
        elif batch_id:
            test_text = self.get_text_for_batch(batch_id)
        else:
                raise Warning(_('You must set a batch or a scenario'))
        
        print test_text
        path = self.make_tmp_file(test_text)
        try:
            run_id = self.launch_test(path, batch_id)
        except Exception:
            raise
        finally:
            os.remove(path)
        if batch_id:
            batch_id.write({
                                 'last_run_result': run_id.result,
                                 'last_run_date': run_id.create_date,
                                 })
        if not self.scenario_line_id:
            return {
                'res_model': 'run',
                'res_id': run_id.id,
                'type': 'ir.actions.act_window',
                'views': [[False, 'form']],
                }
        else:
            return run_id
        
    def get_text_for_batch(self, batch_id):
        headers = ["Feature: " + batch_id.name + "@" + str(batch_id.id) + "@"]
        if batch_id.description:
            headers += ['\t' + batch_id.description]
        scenarios_text = [self.get_text_for_scenario(x.scenario_id) for x in batch_id.scenario_ids]
        return '\n'.join(headers + scenarios_text)
    
    def get_text_for_scenario(self, scenario_id, empty_batch=False):
        headers = []
        if empty_batch:
            headers.append("Feature: Empty")
            self.empty_batch = True
        headers += ["Scenario: " + scenario_id.name + "@" + str(scenario_id.id) + "@"]
        if scenario_id.description:
            headers += [scenario_id.description]
        scenario_lines_text = [x.text + "@" + str(x.id) + "@" for x in scenario_id.scenario_line_ids]
        return '\n\t'.join(headers + scenario_lines_text)
    
    def get_text_for_scenario_line(self, scenario_line_id):
        self.empty_batch = True
        return """Feature: Empty
Scenario: Empty
    {}
        """.format(scenario_line_id.text + "@" + str(scenario_line_id.id) + "@")
    
    def make_tmp_file(self, text):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "features/")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".feature", dir=path) as f:
            f.write(text.encode('utf-8'))
        return f.name
    
    def launch_test(self, path, batch_id):
        c = Configuration("")
        if not c.format:
            c.format = [ c.default_format ]
        c.paths = [path]
        c.userdata['lang_code'] = self.lang_code
        c.userdata['target_id'] = self.target_id
        c.userdata['base_url'] = self.target_id.target_id.url
        c.userdata['batch_id'] = batch_id.id
        c.userdata['scenario_id'] = self.scenario_id.id
        c.userdata['scenario_line_id'] = self.scenario_line_id.id
        c.userdata['empty_batch'] = self.empty_batch
        c.userdata['browser_vm_url'] = self.env['ir.config_parameter'].get_param('test_builder.vm_url')
        self.config = c
        r = Runner(c)
        r.run()
        if self.scenario_line_id:
            return r.feature.status
        else:
            return c.userdata.get('run_id', None)
    