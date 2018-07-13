#!/usr/bin/env python
# coding: utf-8
from bottle import route, run, response, request
import sqlite3
import argparse
import logging.handlers
from pprint import pformat
from base64 import b64decode
import json

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Openprod maintenance contract server.")
parser.add_argument('--syslog', action='store_true')
parser.add_argument('--log-file', action='store', nargs='?', const='/var/log/openprod/contract_server.log')
parser.add_argument('--log-level', action='store', default='info')
parser.add_argument('--host', action='store', default='0.0.0.0')
parser.add_argument('--database', action='store', default='contracts.db')
parser.add_argument('--port', action='store', default=8888, type=int)
args = parser.parse_args()

level = logging.getLevelName(args.log_level.upper())
logger.setLevel(level)

if args.syslog:
    handler = logging.handlers.SysLogHandler('/dev/log')
elif args.log_file:
    handler = logging.FileHandler(args.log_file)
else:
    handler = logging.StreamHandler()

logger.addHandler(handler)

logger.info("Contract server started with arguments %s", pformat(vars(args)))

requests = {
            'initialize_db': """create table if not exists contracts (
                                                                      contract_number text,
                                                                      start_date datetime,
                                                                      end_date datetime,
                                                                      company text);
                                create table if not exists logs (
                                                                 source_ip text,
                                                                 contract_number text,
                                                                 is_registered boolean,
                                                                 request_date datetime default current_timestamp,
                                                                 company text);""",
            'select_contract': u"""select start_date, end_date from contracts where contract_number = ? and date('now') between start_date and end_date limit 1""",
            'log_request': u"""insert into logs (source_ip, contract_number, is_registered, company) values (?, ?, ?, ?)""",
            }

conn = sqlite3.connect(args.database)

with conn:
    conn.executescript(requests['initialize_db'])
    
@route('/nocontract')
def nocontract():
    with conn:
        c = conn.cursor()
        c.execute(requests['log_request'], (request.remote_addr, None, False, None))

@route('/<contract>')
def index(contract):
    with conn:
        c= conn.cursor()
        c.execute(requests['select_contract'], (contract,))
        res = c.fetchone()
        ok = bool(res)
        c.execute(requests['log_request'], (request.remote_addr, contract, ok, request.query.company_name or 'None'))
        http_status = 200 if ok else 400
        response.status = http_status
        return json.dumps({'start_date': res[0], 'end_date':res[1], 'state': 'active'}) if ok else ""

run(host=args.host, port=args.port)
