# coding: utf-8

from openerp import http
from pprint import pformat, pprint
from .. import utils
from sqlalchemy.orm import joinedload

class TestOrm(http.Controller):
    
    def __init__(self, *args, **kwargs):
        self.orm = utils.Orm(http.request.env)
        super(TestOrm, self).__init__(*args, **kwargs)
    
    @http.route('/neworm', type='http')
    def test_orm(self, model):
        session = self.orm.sessionmaker()
        obj = self.orm[model]
        query = session.query(obj).options(joinedload('user'))
        #return "<br /><br /><br /><br />".join([unicode(x) + '<br />|||<br />' + unicode(x.calendar.name) for x in query.all()])
        #return "<br /><br /> <br />".join([unicode(x) + "<br />" + unicode(y) for x,y  in query.all()])
#         return "<br /><br /> <br />".join([unicode(x) for x in query.all()])
        return u"<br /><br /> <br />".join([u"{}<br />".format(unicode(x)) for x in query.all()])