# -*- coding: utf-8 -*-
from openerp.exceptions import AccessError
from openerp.http import Controller
from openerp.http import route
from openerp.http import Response
from psycopg2 import IntegrityError
from openerp import http
import psycopg2

class CommitController(Controller):
    @route('/post_commit/', auth='none', csrf=False, type="json")
    def handler(self, request, **kwargs):
        # Pour plus d'info sur le fichier JSON voir  : https://docs.gitlab.com/ce/user/project/integrations/webhooks.html
        commits = request.jsonrequest.get('commits','')
        if not commits :
            Response.status = "400 Bad Request"
            return {
                 "error": "no commits"
            }
        for commit in commits :
            if not commit.get('id','') :
                Response.status = "400 Bad Request"
                return {
                    "error": "no id for commit"
                }
            revision = commit.get('id','')
            if not commit.get('message','') :
                Response.status = "400 Bad Request"
                return {
                    "error": "no message for commit"
                }
            message = commit.get('message','')
            if not commit.get('author','').get('name','') :
                Response.status = "400 Bad Request"
                return {
                    "error": "no author name for commit"
                }
            username = commit.get('author','').get('name','') 
            if not commit.get('url','') :
                Response.status = "400 Bad Request"
                return {
                    "error": "no url for commit"
                }
            url = commit.get('url','')
            if not request.jsonrequest.get('ref','') :
                Response.status = "400 Bad Request"
                return {
                    "error": "no branch name for commit"
                }
            branch_name = request.jsonrequest.get('ref','')

            try :
                #Define our connection string
                conn_string = "host='localhost' dbname='track' user='openprod' password='admin3849'"

                # get a connection, if a connect cannot be made an exception will be raised here
                conn = psycopg2.connect(conn_string)
            
                # conn.cursor will return a cursor object, you can use this cursor to perform queries
                cursor = conn.cursor()

                sql = """INSERT INTO public.tracker_commit( username, create_uid, create_date, source_created_datetime, 
                         branch_name,message, revision,url, write_date, write_uid)
                               VALUES (%s, %s,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP, %s, %s, %s,%s,CURRENT_TIMESTAMP,1) RETURNING id;"""
                cursor.execute(sql, (username,1,branch_name, message, revision,url))
                db_version = cursor.fetchone()
                conn.commit()
                cursor.close()
            except IntegrityError:
                Response.status = "400 Bad Request"
                return {
                    "error": "revision %s already used" % (
                        revision
                    )
                }
            except (Exception, psycopg2.DatabaseError) as error:
                print(error)
            except : 
                print "error"
            finally:
                if conn is not None:
                    conn.close()

        Response.status = "200 Ok"
        return {'commit': 'commit added'}
