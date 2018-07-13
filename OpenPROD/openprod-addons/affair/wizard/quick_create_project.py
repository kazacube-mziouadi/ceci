# coding: utf-8

from openerp import models, fields


class quick_create_project(models.TransientModel):
    """
    Quick create wizard for projects
    """
    _inherit = 'quick.create.project'

    attach_to_affair_id = fields.Many2one('affair', string='Attach to affair',
                                          required=False, ondelete='cascade')

    def get_additional_vals(self):
        if self.attach_to_affair_id:
            affair_id = self.attach_to_affair_id.id
            return {
                'affair_id': affair_id,
            }
        else:
            return {}

    def get_copy_documents(self, phase_id):
        if self.attach_to_affair_id and self.attach_to_affair_id.directory_id:
            affair_id = self.attach_to_affair_id
            directory_id = affair_id.directory_id

            def get_copy_data(doc_id):
                res = doc_id.copy_data()[0]
                res['directory_id'] = directory_id.id
                res['attachment'] = doc_id.attachment
                res['is_template'] = False
                return res

            return [
                (0, 0, get_copy_data(x)) for x in phase_id.phase_document_ids
            ]
        else:
            return [(6, 0, phase_id.phase_document_ids.ids)]
        