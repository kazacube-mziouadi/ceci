# -*- coding: utf-8 -*-
from openerp.workflow.instance import WorkflowInstance
from openerp.workflow.helpers import Session, Record
from openerp.workflow.workitem import WorkflowItem
from openerp.workflow.service import WorkflowService
import logging

logger = logging.getLogger(__name__)

#===============================================================================
# SERVICE
#===============================================================================
def s_validate(self, signal):
    result = False
    # ids of all active workflow instances for a corresponding resource (id, model_nam)
    self.cr.execute('select id from wkf_instance where res_id=%s and res_type=%s and progress', (self.record.id, self.record.model))
    # TODO: Refactor the workflow instance object
    for (instance_id,) in self.cr.fetchall():
        wi = WorkflowInstance(self.session, self.record, {'id': instance_id})
        res2 = wi.validate(signal)

        result = result or res2
    return result


def s_write(self):
    self.cr.execute('select id from wkf_instance where res_id=%s and res_type=%s and progress=true',
        (self.record.id or None, self.record.model or None)
    )
    for (instance_id,) in self.cr.fetchall():
        WorkflowInstance(self.session, self.record, {'id': instance_id}).update()
            
            
def s_create(self):
        WorkflowService.CACHE.setdefault(self.cr.dbname, {})

        wkf_ids = WorkflowService.CACHE[self.cr.dbname].get(self.record.model, None)

        if not wkf_ids:
            self.cr.execute('select id from wkf where osv=%s and on_create=True and is_active', (self.record.model,))
            wkf_ids = self.cr.fetchall()
            WorkflowService.CACHE[self.cr.dbname][self.record.model] = wkf_ids

        for (wkf_id, ) in wkf_ids:
            query = 'UPDATE %s SET wkf_id=%s WHERE id = %s'%(self.record.model.replace('.', '_'), wkf_id, self.record.id)
            self.cr.execute(query)
            WorkflowInstance.create(self.session, self.record, wkf_id)
            
WorkflowService.validate = s_validate
WorkflowService.write = s_write
WorkflowService.create = s_create



#===============================================================================
# INSTANCES
#===============================================================================
@classmethod
def i_create(cls, session, record, workflow_id):
    assert isinstance(session, Session)
    assert isinstance(record, Record)
    assert isinstance(workflow_id, (int, long))

    cr = session.cr
    cr.execute('SELECT flow_start, id, name, required, sequence FROM wkf_activity WHERE wkf_id=%s ORDER BY flow_start', (workflow_id,))
    activities = cr.dictfetchall()
    wi = False
    stack = []
    instance_id = False
    for activity in activities:
        if activity['flow_start']:
            cr.execute("""INSERT INTO wkf_instance (name, 
                                                    activity_id, 
                                                    required, 
                                                    sequence, 
                                                    res_type, 
                                                    res_id, 
                                                    uid, 
                                                    wkf_id, 
                                                    state, 
                                                    progress, 
                                                    date, 
                                                    is_active) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true, now(), true) RETURNING id""", (activity['name'], 
                                                                                                             activity['id'], 
                                                                                                             activity['required'], 
                                                                                                             activity['sequence'], 
                                                                                                             record.model, 
                                                                                                             record.id, 
                                                                                                             session.uid, 
                                                                                                             workflow_id, 
                                                                                                             'active'))
            instance_id = cr.fetchone()[0]
            WorkflowItem.create(session, record, activity, instance_id, stack)
            cr.execute('SELECT * FROM wkf_instance WHERE id = %s', (instance_id,))
            values = cr.dictfetchone()
            wi = WorkflowInstance(session, record, values)
            wi.update()
        else:
            cr.execute("""INSERT INTO wkf_instance (name, 
                                                    activity_id, 
                                                    required, 
                                                    sequence, 
                                                    res_type, 
                                                    res_id, 
                                                    wkf_id, 
                                                    state, 
                                                    is_active) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true) RETURNING id""", (activity['name'], 
                                                                                            activity['id'], 
                                                                                            activity['required'], 
                                                                                            activity['sequence'], 
                                                                                            record.model, 
                                                                                            record.id, 
                                                                                            workflow_id, 
                                                                                            'active'))
            
    return wi

WorkflowInstance.create = i_create


#===============================================================================
# WORKITEM
#===============================================================================

@classmethod
def wi_create(cls, session, record, activity, instance_id, stack):
    assert isinstance(session, Session)
    assert isinstance(record, Record)
    assert isinstance(activity, dict)
    assert isinstance(instance_id, (long, int))
    assert isinstance(stack, list)
    
    cr = session.cr
    cr.execute("UPDATE wkf_instance SET progress=true, uid=%s, date=now() WHERE activity_id=%s AND res_id = %s and res_type = %s", (session.uid, activity['id'], record.id, record.model))
    cr.execute("select nextval('wkf_workitem_id_seq')")
    id_new = cr.fetchone()[0]
    cr.execute("insert into wkf_workitem (id,act_id,inst_id,state) values (%s,%s,%s,'active')", (id_new, activity['id'], instance_id))
    cr.execute('select * from wkf_workitem where id=%s',(id_new,))
    work_item_values = cr.dictfetchone()
    logger.info('Created workflow item in activity %s',
                activity['id'],
                extra={'ident': (session.uid, record.model, record.id)})

    workflow_item = WorkflowItem(session, record, work_item_values)
    workflow_item.process(stack=stack)
    
# Sortie d'une activité
def _split_test(self, split_mode, signal, stack):
    cr = self.session.cr
    cr.execute('select * from wkf_transition where act_from=%s ORDER BY sequence,id', (self.workitem['act_id'],))
    test = False
    transitions = []
    alltrans = cr.dictfetchall()
    if split_mode in ('XOR', 'OR'):
        for transition in alltrans:
            if self.wkf_expr_check(transition,signal):
                test = True
                transitions.append((transition['id'], self.workitem['inst_id']))
                if split_mode=='XOR':
                    break
                
    else:
        test = True
        for transition in alltrans:
            if not self.wkf_expr_check(transition, signal):
                test = False
                break
            
            cr.execute('select count(*) from wkf_witm_trans where trans_id=%s and inst_id=%s', (transition['id'], self.workitem['inst_id']))
            if not cr.fetchone()[0]:
                transitions.append((transition['id'], self.workitem['inst_id']))

    if test and transitions:
        cr.executemany('insert into wkf_witm_trans (trans_id,inst_id) values (%s,%s)', transitions)
        cr.execute('delete from wkf_workitem where id=%s', (self.workitem['id'],))
#         cr.execute("UPDATE wkf_instance SET progress=false WHERE activity_id=%s AND res_id=%s and res_type=%s", (self.workitem['act_id'], self.record.id, self.record.model))
        cr.execute("UPDATE wkf_instance SET progress=false WHERE id=%s", (self.workitem['inst_id'], ))# self.record.id, self.record.model))
        for t in transitions:
            self._join_test(t[0], t[1], stack)
            
        return True
    
    return False

#         cr.execute('select is_active, activity_id from wkf_activity where id=(select act_to from wkf_transition where id=%s)', (trans_id,))
# Entrée dans une activité
def _join_test(self, trans_id, inst_id, stack):
    def get_activity(transition_id):
        res = False
        cr.execute('SELECT is_active, activity_id FROM wkf_instance WHERE activity_id=(SELECT act_to FROM wkf_transition WHERE id=%s) AND res_id=%s AND res_type=%s LIMIT 1', (transition_id, self.record.id, self.record.model))
        instance = cr.dictfetchone()
        if instance:
            if instance['is_active']:
                act_id = instance['activity_id']
                cr.execute("SELECT * FROM wkf_activity WHERE id = %s", (act_id, ))
                res = cr.dictfetchone()
            else:
                cr.execute("SELECT id from wkf_transition WHERE act_from=%s AND is_default=true LIMIT 1", (instance['activity_id'], ))
                new_transition_id = cr.dictfetchone() 
                if new_transition_id:
                    res = get_activity(new_transition_id['id'])
                
        return res
        
    cr = self.session.cr
#     cr.execute('select * from wkf_activity where id=(select act_to from wkf_transition where id=%s)', (trans_id,))
#     cr.dictfetchone()
    activity = get_activity(trans_id)
    if activity:
        cr.execute("SELECT id FROM wkf_instance WHERE activity_id=%s AND res_id=%s AND res_type=%s", (activity['id'], self.record.id, self.record.model))
        instance = cr.dictfetchone()
        if activity['join_mode']=='XOR':
            WorkflowItem.create(self.session, self.record, activity, instance['id'], stack=stack)
            cr.execute('delete from wkf_witm_trans where inst_id=%s and trans_id=%s', (inst_id, trans_id))
        else:
            cr.execute('select id from wkf_transition where act_to=%s ORDER BY sequence,id', (activity['id'],))
            trans_ids = cr.fetchall()
            ok = True
            for (id,) in trans_ids:
                cr.execute('select count(*) from wkf_witm_trans where trans_id=%s and inst_id=%s', (id, inst_id))
                res = cr.fetchone()[0]
                if not res:
                    ok = False
                    break
            if ok:
                for (id,) in trans_ids:
                    cr.execute('delete from wkf_witm_trans where trans_id=%s and inst_id=%s', (id, inst_id))
                    
                WorkflowItem.create(self.session, self.record, activity, instance['id'], stack=stack)
            
WorkflowItem._join_test = _join_test
WorkflowItem._split_test = _split_test
WorkflowItem.create = wi_create
