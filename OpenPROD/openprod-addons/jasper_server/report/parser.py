# -*- coding: utf-8 -*-


from cStringIO import StringIO
from HTMLParser import HTMLParser
from lxml.etree import parse
from tempfile import mkstemp
from dime import Message
import os

import email
import re


class NotMultipartError(Exception):
    pass


class HTML2Text(HTMLParser):
    """
    Instance the HTML for decode the message
    return by the JasperServer
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.output = StringIO()
        self.is_valid = True
        self.is_linefeed = True
        self.is_title = True

    def get_text(self):
        return self.output.getvalue()

    def handle_data(self, data):
        if not self.is_valid:
            self.output.write(data)
        if self.is_linefeed:
            self.output.write('\n')
        elif self.is_title:
            self.output.write('\n')

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.is_valid = False
        elif tag == 'p':
            self.is_linefeed = False
        elif tag.startswith('h'):
            self.is_title = False

    def handle_endtag(self, tag):
        if tag == "body":
            self.is_valid = True
        elif tag == 'p':
            self.is_linefeed = True
        elif tag.startswith('h'):
            self.is_title = True


# def ParseDIME(source, list_file):
#     """
#     We must decompose the dime record to return the PDF only
#     """
#     fp = StringIO(source)
#     a = Message.load(fp)
#     for x in a.records:
#         if x.type.value == 'application/pdf':
#             content = x.data
#             # Store the PDF in TEMP directory
#             fd, f_name = mkstemp(suffix='.pdf', prefix='jasper')
#             list_file.append(f_name)
#             fpdf = open(f_name, 'w+b')
#             fpdf.write(content)
#             fpdf.close()
#             os.close(fd)
#
#
def ParseXML(source):
    """
    Read the JasperServer Error code
    and return the code and the message
    """
    fp = StringIO(source)
    tree = parse(fp)
    fp.close()
    r = tree.xpath('//runReportReturn')
    if not r:
        raise Exception('Error, invalid Jasper Message')
    fp = StringIO(r[0].text.encode('utf-8'))
    tree = parse(fp)
    fp.close()
    rcode = tree.xpath('//returnCode')
    rmess = tree.xpath('//returnMessage')
    return (rcode and rcode[0].text or '0',
            rmess and rmess[0].text or 'unknow message')


def ParseHTML(source):
    """
    Read the HTML content return by an authentification error
    """
    p = HTML2Text()
    p.feed(source)
    return p.get_text()


def ParseContent(source, content_type='application/dime'):
    """
    Parse the content and return a decode stream
    """
    if content_type == 'application/dime':
        fp = StringIO(source)
        a = Message.load(fp)
        content = ''
        for x in a.records:
            if x.type.value == 'application/pdf':
                content = x.data
        return content
    elif content_type.startswith('multipart/related'):
        srch = re.search(r'----=[^\r\n]*', source)
        if srch is None:
            raise NotMultipartError()
        boundary = srch.group()
        res = " \n" + source
        res = "Content-Type: multipart/alternative; boundary=%s\n%s" % (boundary, res)  # noqa
        message = email.message_from_string(res)
        attachment = message.get_payload()[1]
        return attachment.get_payload()
    else:
        raise Exception('Unknown Content Type')


def ParseMultipart(res, list_file):
    srch = re.search(r'----=[^\r\n]*', res)
    if srch is None:
        raise NotMultipartError()
    boundary = srch.group()
    res = " \n" + res
    res = "Content-Type: multipart/alternative; boundary=%s\n%s" % (boundary, res)  # noqa
    message = email.message_from_string(res)
    attachment = message.get_payload()[1]
    # return {'content-type': attachment.get_content_type(),
    # 'data': attachment.get_payload()}
    # Store the PDF in TEMP directory
    fd, f_name = mkstemp(suffix='.pdf', prefix='jasper')
    list_file.append(f_name)
    fpdf = open(f_name, 'w+b')
    fpdf.write(attachment.get_payload())
    fpdf.close()
    os.close(fd)


def ParseResponse(resp, list_file, doc_format='pdf'):
    fd, f_name = mkstemp(suffix='.' + doc_format.lower(), prefix='jasper')
    list_file.append(f_name)
    fpdf = open(f_name, 'w+b')
    fpdf.write(resp['data'])
    fpdf.close()
    os.close(fd)


def WriteContent(content, list_file):
    """
    Write content in tempory file
    """
    fd, f_name = mkstemp(suffix='.pdf', prefix='jasper')
    list_file.append(f_name)
    fpdf = open(f_name, 'w+b')
    fpdf.write(content)
    fpdf.close()
    os.close(fd)

if __name__ == '__main__':
    print ParseHTML("""<html><head><title>Apache Tomcat/5.5.20 - Rapport d'erreur</title>
<style><!--H1 {font-family:Tahoma,Arial,sans-serif;color:white;
                    background-color:#525D76;font-size:22px;}
           H2 {font-family:Tahoma,Arial,sans-serif;color:white;
                    background-color:#525D76;font-size:16px;}
           H3 {font-family:Tahoma,Arial,sans-serif;color:white;
                    background-color:#525D76;font-size:14px;}
           BODY {font-family:Tahoma,Arial,sans-serif;color:black;
                    background-color:white;}
           B {font-family:Tahoma,Arial,sans-serif;color:white;
                    background-color:#525D76;}
           P {font-family:Tahoma,Arial,sans-serif;
                    background:white;color:black;font-size:12px;}
           A {color : black;}A.name {color : black;}
                    HR {color : #525D76;}--></style>
</head><body>
<h1>Etat HTTP 401 - Bad credentials</h1>
<HR size="1" noshade="noshade"><p><b>type</b> Rapport d'état</p>
<p><b>message</b> <u>Bad credentials</u></p><p><b>description</b>
<u>La requête nécessite une authentification HTTP (Bad credentials).</u></p>
<HR size="1" noshade="noshade"><h3>Apache Tomcat/5.5.20</h3>
</body></html>""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
