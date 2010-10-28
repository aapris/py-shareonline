'''
Created on Oct 21, 2010

@author: arista
'''

# Initial Share online implementation
# http://wiki.forum.nokia.com/index.php/How_to_create_your_own_Share_Online_provider

import re
import time
import os
import base64
import hashlib
import datetime
from xml.dom import minidom


###### WSSE authentication related functions ###### 
# wsse_re = re.compile('UsernameToken Username="([^"]+)", PasswordDigest="([^"]+)", Nonce="([^"]+)", Created="([^"]+)"')
WSSE_RE = re.compile(r"""\b([a-zA-Z]+)\s*=\s*["']([^"]+)["']""")

class WsseAuthError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def _wsse_passworddigest(nonce, created, password):
    "Creates WSSE password digest from nonce, timestamp and password."
    key = "%s%s%s" % (nonce, created, password)
    digest = base64.b64encode(hashlib.sha1(key).digest())
    return digest

def _wsse_header_vars(password):
    """Creates WSSE passworddigest, nonce, and timestamp from password ."""
    random = '%s%s%s' % (os.urandom(64), time.time(), password)
    nonce = hashlib.md5(random).hexdigest()
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    passworddigest = _wsse_passworddigest(nonce, created, password)
    return passworddigest, nonce, created 

def _wsse_header(username, passworddigest, nonce, created):
    """Combines valid Http-X-WSSE header from parameters"""
    http_x_wsse = 'UsernameToken Username="%s", PasswordDigest="%s", Nonce="%s", Created="%s"' % \
                  (username, passworddigest, base64.b64encode(nonce), created)
    return http_x_wsse

def wsse_header(username, password):
    """Creates valid Http-X-WSSE header from username and plain password"""
    passworddigest, nonce, created = _wsse_header_vars(password)
    http_x_wsse = _wsse_header(username, passworddigest, nonce, created)
    return http_x_wsse

def wsse_auth(http_x_wsse, password):
    """
    Validates 'http_x_wsse' header string against 'password'.
    Returns UserName if password passes validation.
    # TODO: add optional max_age parameter and raise WsseAuthExpiredError if
    # timestamp is too old.
    """
    wsse = {}
    # Find all values in the header
    for key, val in WSSE_RE.findall(http_x_wsse):
        wsse[key.lower()] = val
    # Check that all mandatary keys are present
    for key in ['username', 'passworddigest', 'nonce', 'created']:
        if key not in wsse:
            raise WsseAuthError(u"Missing key '%s' in wsse auth header" % key)
    nonce = base64.b64decode(wsse['nonce'])
    digest = _wsse_passworddigest(nonce, wsse['created'], password)
    if wsse['passworddigest'] == digest:
        return wsse['username']
    else:
        return None

def wsse_auth_failed(realm):
    """
    Returns headers (and body) to return correct authentication headers
    when WSSE authentication has failed.
    """
    body = u"Unauthorized!\n"
    headers = {}
    headers['Status'] = '401 Unauthorized'
    headers['WWW-Authenticate'] = 'WSSE realm="%s", profile="UsernameToken"' % realm
    headers['Content-Type'] = 'text/plain; charset=UTF-8'
    return headers, body

###### Posted data handlers ###### 
 

def _save_post_data(raw_post_data, path, postfix):
    """
    Saves request's raw post data (xml) to a file.
    Useful for debugging.
    """
    try:
        now = datetime.datetime.now()
        filename = now.strftime('%Y%m%dT%H%M%S') + '.%06d-' % now.microsecond + postfix + ".xml"
        filepath = os.path.join(path, filename)
        f = open(filepath, 'wb')
        f.write(raw_post_data)
        f.close()
        return filepath
    except Exception, error:
        print error
        # TODO: logging error here
        return None

def _parse_request_xml(xml):
    """Parse request XML and return data from all known elements."""
    dom = minidom.parseString(xml)
    text_tags = ['title', 'summary', 'generator', 'dc:subject', 'issued']
    data = {}
    # Try to find all known elements, which contain only text
    for tag in text_tags:
        e = dom.getElementsByTagName(tag)
        if e and e[0].firstChild:
            data[tag] = e[0].firstChild.data.strip()
    # Content is a special case containing BASE64 encoded filedata
    content = dom.getElementsByTagName('content')
    if content:
        if content[0].attributes['mode'].value.lower() == 'base64':
            data['filedata'] = base64.b64decode(content[0].firstChild.data)
            data['filetype'] = content[0].attributes['type'].value.lower()
        elif content[0].attributes['mode'].value.lower() == 'xml' and \
             content[0].firstChild:
            data['content'] = content[0].firstChild.data.strip()
    # Link is a special case and it has a href attribute, 
    # which contains an ID of previously posted content.
    # (This may mean that client is verifying that post was successful
    # or wants to update it's data.)
    link = dom.getElementsByTagName('link')
    if link and link[0].attributes['href'].value:
        data['uid'] = link[0].attributes['href'].value
    return data

if __name__ == '__main__':
    username = 'Test'
    password = 'kissa'
    http_x_wsse = wsse_header(username, password)
    print http_x_wsse
    validated_username = wsse_auth(http_x_wsse, 'kissa')
    if username == validated_username:
        print "Valid Username:", wsse_auth(http_x_wsse, 'kissa')
    else:
        print "Validation failed"
