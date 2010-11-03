# -*- coding: utf8 -*-

"""
Initial Share online provider library implementation
http://wiki.forum.nokia.com/index.php/How_to_create_your_own_Share_Online_provider
"""

import os
import re
import time
import base64
import hashlib
import datetime
import xml.dom.minidom

###### XML document skeletons ###### 

CONFIG_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<configure_file service_id="com.example" category_id="1" coding_id="2" version="1.0">
<provider> 
  <configure_file_URL>http://www.example.com/config</configure_file_URL> 
  <browserView reltype="alternate" /> 
  <signup_URL></signup_URL> 
  <easy_registration_URL></easy_registration_URL> 
</provider>
<laf> 
  <title>Example.Com</title> 
  <context_pane_icon file='defaulticon.svg'>defaulticon.svg</context_pane_icon>
  <selection_list_icon file='defaulticon.svg'>defaulticon.svg</selection_list_icon>
  <icon file='defaulticon.svg' encoding='BASE64'>PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4NCjwhLS0gR2VuZXJhdG9yOiBBZG2Zz4NCg==</icon>
</laf>
<media_options> 
  <format_list> 
    <format>image/jpeg</format> 
    <format>video/mp4</format> 
    <format>video/3gpp</format> 
    <format>audio/amr</format> 
  </format_list> 
  <maximum_pixels horizontal="0" vertical="0" /> 
  <maximum_bytes bytes="0" /> 
</media_options>
<entry_options> 
  <title_text present="0" required="0" /> 
  <caption_text present="1" required="0" /> 
  <body_text present="0" required="0" /> 
  <min_items items="1" /> 
  <max_items items="1" /> 
  <max_size size="0" /> 
  <tags present='1' required='0'/> 
  <privacy_levels present='1' required='0' /> 
</entry_options>
<location_options>
  <gps_info present='1' />
  <network_info present='1' />
</location_options>
<protocol_options> 
  <protocol plugin="Atom" version="0.3" authentication="wsse"> 
    <endpoint_path>http://www.example.com/service</endpoint_path> 
    <roundtrip_editing>0</roundtrip_editing> 
  </protocol> 
</protocol_options> 
</configure_file>
"""

SERVICE_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<feed version="0.3"
      xmlns="http://purl.org/atom/ns#"
      xmlns:dc="http://purl.org/dc/elements/1.1/"
      xml:lang="en">
  <link rel="service.post" href="http://www.example.com/post/pub" type="application/x.atom+xml" title="PUBLIC" />
  <link rel="service.post" href="http://www.example.com/post/res" type="application/x.atom+xml" title="RESTRICED" />
  <link rel="service.feed" href="http://www.example.com/feed" type="application/x.atom+xml" title="Latest" />
  <link rel="alternate" href="http://www.example.com/" type="text/html" title="Example.com home page" />
</feed>
"""

ENTRY_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<entry xmlns="http://purl.org/atom/ns#">
<title>{{ entry.title }}</title>
<summary>{{ entry.summmary }}</summary>
<issued>{{ entry.issued|date:"Y-m-d H:i:s" }}Z</issued>
<link type="text/html" rel="alternative" href="{{ entry.link_href }}" title="HTML" />
<id>{{ entry.id }}</id>
</entry>
"""


###### WSSE authentication related functions ###### 
# wsse_re = re.compile('UsernameToken Username="([^"]+)", PasswordDigest="([^"]+)", Nonce="([^"]+)", Created="([^"]+)"')
WSSE_RE = re.compile(r"""\b([a-zA-Z]+)\s*=\s*["']([^"]+)["']""")

class WsseAuthError(Exception):
    "Custom Error class for WSSE errors."

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
def _remove_child_nodes(elem):
    "Removes all child nodes from 'elem'."
    while elem.hasChildNodes():
        node = elem.firstChild
        _remove_child_nodes(node)
        elem.removeChild(node)

def config_set_provider(doc, conf, host):
    """Populates elements inside <provider> element."""
    provider_e = doc.getElementsByTagName('provider')[0]
    for key in conf:
        key_e = provider_e.getElementsByTagName(key)[0]
        if conf[key]:
            #conf[key] = host + conf[key] 
            for node in key_e.childNodes:
                key_e.removeChild(node)
            key_e.appendChild(doc.createTextNode(host + conf[key]))

def config_set_laf(doc, conf):
    """Populates elements inside <laf> element."""
    laf_e = doc.getElementsByTagName('laf')[0]
    # Set title
    title_e = laf_e.getElementsByTagName('title')[0]
    _remove_child_nodes(title_e)
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
    """Populates elements inside <media_options> element."""
    media_options_e = doc.getElementsByTagName('media_options')[0]
    format_list_e = media_options_e.getElementsByTagName('format_list')[0]
    format_list_e.appendChild(doc.createTextNode('\n    '))
    for elem in format_list_e.getElementsByTagName('format'):
        _remove_child_nodes(elem)
        format_list_e.removeChild(elem)
    for format_type in conf['format_list']:
        format_e = doc.createElement('format')
        format_e.appendChild(doc.createTextNode(format_type))
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
    "Sets the value of <endpoint_path> element"
    endpoint_path_e = doc.getElementsByTagName('endpoint_path')[0]
    _remove_child_nodes(endpoint_path_e)
    endpoint_path_e.appendChild(doc.createTextNode(host + url))

def config_set_service_id(doc, service_id):
    "Sets the value of service_id attribute in <configure> element"
    configure_file_e = doc.getElementsByTagName('configure_file')[0]
    configure_file_e.setAttribute('service_id', service_id)

def config_create_xml(sharing_settings, host):
    "Sets all values in configure file."
    #config_doc = xml.dom.minidom.parse('shareonline-config.xml')
    config_doc = xml.dom.minidom.parseString(CONFIG_XML)
    config_set_service_id(config_doc, sharing_settings.service_id)
    config_set_provider(config_doc, sharing_settings.provider, host)
    config_set_laf(config_doc, sharing_settings.laf)
    config_set_media_options(config_doc, sharing_settings.media_options)
    config_set_attributes(config_doc, 'entry_options', 
                          sharing_settings.entry_options)
    config_set_attributes(config_doc, 'location_options', 
                          sharing_settings.location_options)
    config_set_post_url(config_doc, sharing_settings.post_url, host)
    return config_doc.toprettyxml('', newl='', encoding='utf-8')

###### Service document ######

def services(slist):
    "Creates 'service' xml document."
    #services_doc = xml.dom.minidom.parse('shareonline-service.xml')
    services_doc = xml.dom.minidom.parseString(SERVICE_XML)
    feed_e = services_doc.getElementsByTagName('feed')[0]
    while feed_e.hasChildNodes():
        for node in feed_e.childNodes:
            feed_e.removeChild(node)
    for link in slist:
        link_e = services_doc.createElement('link')
        for attr in link.keys():
            link_e.setAttribute(attr, link[attr])
        feed_e.appendChild(link_e)
    return services_doc.toprettyxml(' ', newl='\n', encoding='utf-8')

###### Post handlers ######

def create_element_with_text(doc, tagname, text):
    "Creates new element 'tagname' and put 'text' node into it"
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
    entry_e.appendChild(create_element_with_text(doc, 'title', data['title']))
    entry_e.appendChild(create_element_with_text(doc, 'summary', data['summary']))
    entry_e.appendChild(create_element_with_text(doc, 'issued', data['issued']))
    link_e = doc.createElement('link')
    for attr, val in [('type', 'text/html'), 
                      ('rel', 'alternative'), 
                      ('title', 'HTML')]:
        link_e.setAttribute(attr, val)
    link_e.setAttribute('href', data['link'])
    entry_e.appendChild(link_e)
    entry_e.appendChild(create_element_with_text(doc, 'id', data['id']))
    return doc.toprettyxml('', newl='\n', encoding='utf-8')

###### Post data handlers ######
 
def _save_post_data(raw_post_data, path, postfix):
    """
    Saves request's raw post data (xml) to a file.
    Useful for debugging.
    """
    try:
        now = datetime.datetime.now()
        filename = now.strftime('%Y%m%dT%H%M%S') + '.%06d-' % \
                   now.microsecond + postfix + ".xml"
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
    """Parses request XML and returns data from all known elements."""
    dom = xml.dom.minidom.parseString(xmldata)
    text_tags = ['title', 'summary', 'generator', 'dc:subject', 'issued']
    data = {}
    # Try to find all known elements, which contain only text
    for tag in text_tags:
        elem = dom.getElementsByTagName(tag)
        if elem and elem[0].firstChild:
            data[tag] = elem[0].firstChild.data.strip()
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
    USERNAME = 'Test'
    PASSWORD = 'cat'
    HTTP_X_WSSE = wsse_header(USERNAME, PASSWORD)
    print HTTP_X_WSSE
    VALIDATED_USERNAME = wsse_auth(HTTP_X_WSSE, 'cat')
    if USERNAME == VALIDATED_USERNAME:
        print "Valid Username:", wsse_auth(HTTP_X_WSSE, 'cat')
    else:
        print "Validation failed"
