# -*- coding: utf-8 -*-
{
    'name' : 'Project',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Project',
    'description' : """ Project """,
    'website': 'http://objectif-pi.com',
    'data': [
             'security/project_security.xml',
             'wizard/create_task_view.xml',
             'wizard/wizard_create_timetracking_view.xml',
             'project_view.xml',
             'mrp_view.xml',
             'calendar_event_view.xml',
             'common_model_view.xml',
             'security/ir.model.access.csv',
             'data/project_workflow.xml',
             'wizard/quick_create_project_view.xml',
           ],
    'depends': [
               'mrp',
               'base_openprod',
               ],
    'installable': True,
    'auto_install': False,
}