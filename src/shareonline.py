'''
Created on Oct 21, 2010

@author: arista
'''

# Initial Share online implementation
# http://wiki.forum.nokia.com/index.php/How_to_create_your_own_Share_Online_provider

#import sys
import os
import re
import time
import base64
import hashlib
import datetime
import xml.dom.minidom


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

###### config file related functions ###### 

# FIXME: This doesn't work as expected (leaves whitespace)
def _removeChildNodes(e):
    while e.hasChildNodes():
        n = e.firstChild
        _removeChildNodes(n)
        e.removeChild(n)

def config_set_provider(doc, conf, host):
    """Populate elements inside <provider> element."""
    provider_e = doc.getElementsByTagName('provider')[0]
    for key in conf:
        key_e = provider_e.getElementsByTagName(key)[0]
        if conf[key]:
            #conf[key] = host + conf[key] 
            for node in key_e.childNodes:
                key_e.removeChild(node)
            key_e.appendChild(doc.createTextNode(host + conf[key]))

def config_set_laf(doc, conf):
    """Populate elements inside <laf> element."""
    laf_e = doc.getElementsByTagName('laf')[0]
    # Set title
    title_e = laf_e.getElementsByTagName('title')[0]
    _removeChildNodes(title_e)
    title_e.appendChild(doc.createTextNode(conf['title']))
    # Set all 3 '*icon' elements, all of them have 'file' attribute
    iconfilename = os.path.basename(conf['icon_svg_path'])
    icon_base64 = base64.b64encode(open(conf['icon_svg_path']).read())
    for icon_tag in ['context_pane_icon', 'selection_list_icon', 'icon']:
        icon_e  = laf_e.getElementsByTagName(icon_tag)[0]
        for node in icon_e.childNodes:
            icon_e.removeChild(node)
        icon_e.setAttribute('file', iconfilename)
        if icon_tag == 'icon':
            icon_e.appendChild(doc.createTextNode(icon_base64))
        else:
            icon_e.appendChild(doc.createTextNode(iconfilename))

def config_set_media_options(doc, conf):
    """Populate elements inside <media_options> element."""
    media_options_e = doc.getElementsByTagName('media_options')[0]
    format_list_e = media_options_e.getElementsByTagName('format_list')[0]
    format_list_e.appendChild(doc.createTextNode('\n    '))
    for e in format_list_e.getElementsByTagName('format'):
        # e.normalize()
        _removeChildNodes(e)
        format_list_e.removeChild(e)
    for format in conf['format_list']:
        format_e = doc.createElement('format')
        format_e.appendChild(doc.createTextNode(format))
        format_list_e.appendChild(format_e)
        format_list_e.appendChild(doc.createTextNode('\n    '))
    for media_tag in ['maximum_pixels', 'maximum_bytes']:
        media_e = media_options_e.getElementsByTagName(media_tag)[0]
        for attr in conf[media_tag]:
            media_e.setAttribute(attr, conf[media_tag][attr])

def config_set_attributes(doc, tagname, conf):
    """General function to set element's attributes (inside <tagname>)."""
    parent = doc.getElementsByTagName(tagname)[0]
    for tag in conf.keys():
        elem = parent.getElementsByTagName(tag)[0]
        for attr in conf[tag]:
            elem.setAttribute(attr, conf[tag][attr])

def config_set_post_url(doc, url, host):
    endpoint_path_e = doc.getElementsByTagName('endpoint_path')[0]
    _removeChildNodes(endpoint_path_e)
    endpoint_path_e.appendChild(doc.createTextNode(host + url))

def config_set_service_id(doc, service_id):
    configure_file_e = doc.getElementsByTagName('configure_file')[0]
    configure_file_e.setAttribute('service_id', service_id)

def config_create_xml(sharing_settings, host):
    config_doc = xml.dom.minidom.parse('shareonline-config.xml')
    config_set_service_id(config_doc, sharing_settings.service_id)
    config_set_provider(config_doc, sharing_settings.provider, host)
    config_set_laf(config_doc, sharing_settings.laf)
    config_set_media_options(config_doc, sharing_settings.media_options)
    config_set_attributes(config_doc, 'entry_options', sharing_settings.entry_options)
    config_set_attributes(config_doc, 'location_options', sharing_settings.location_options)
    config_set_post_url(config_doc, sharing_settings.post_url, host)
    return config_doc.toprettyxml('', newl='', encoding='utf-8')

###### Service document ######

def services(slist):
    services_doc = xml.dom.minidom.parse('shareonline-service.xml')
    feed_e = services_doc.getElementsByTagName('feed')[0]
    while feed_e.hasChildNodes():
        for e in feed_e.childNodes:
            feed_e.removeChild(e)
    for link in slist:
        link_e = services_doc.createElement('link')
        for attr in link.keys():
            link_e.setAttribute(attr, link[attr])
        feed_e.appendChild(link_e)
    return services_doc.toprettyxml('', newl='', encoding='utf-8')

###### Post handlers ######

def createElementWithText(doc, tagname, text):
    "Create new element 'tagname' and put 'text' node into it"
    element = doc.createElement(tagname)
    text_node = doc.createTextNode(text)
    element.appendChild(text_node)
    return element

def create_entry(data):
    """
    Creates 'entry' xml document.
    This function uses xml.dom.minidom to create document from scratch. 
    """
    impl = xml.dom.minidom.getDOMImplementation()
    doc = impl.createDocument(None, "entry", None)
    entry_e = doc.documentElement
    entry_e.setAttribute('xmlns', 'http://purl.org/atom/ns#')
    entry_e.appendChild(createElementWithText(doc, 'title', data['title']))
    entry_e.appendChild(createElementWithText(doc, 'summary', data['summary']))
    entry_e.appendChild(createElementWithText(doc, 'issued', data['issued']))
    link_e = doc.createElement('link')
    for attr, val in [('type', 'text/html'), 
                      ('rel', 'alternative'), 
                      ('title', 'HTML')]:
        link_e.setAttribute(attr, val)
    link_e.setAttribute('href', data['link'])
    entry_e.appendChild(link_e)
    entry_e.appendChild(createElementWithText(doc, 'id', data['id']))
    return doc.toprettyxml('', newl='', encoding='utf-8')



###### Post data handlers ###### 
 
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

def _parse_request_xml(xmldata):
    """Parse request XML and return data from all known elements."""
    dom = xml.dom.minidom.parseString(xmldata)
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
    # or wants to update it's data.
    link = dom.getElementsByTagName('link')
    if link and link[0].attributes['href'].value:
        data['uid'] = link[0].attributes['href'].value
    return data

if __name__ == '__main__':
    username = 'Test'
    password = 'cat'
    http_x_wsse = wsse_header(username, password)
    print http_x_wsse
    validated_username = wsse_auth(http_x_wsse, 'cat')
    if username == validated_username:
        print "Valid Username:", wsse_auth(http_x_wsse, 'cat')
    else:
        print "Validation failed"
