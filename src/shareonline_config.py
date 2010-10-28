import sys
import os
import base64
import xml.dom.minidom

# FIXME: This doesn't work as expected (leaves whitespace)
def _removeChildNodes(e):
    while e.hasChildNodes():
        n = e.firstChild
        _removeChildNodes(n)
        e.removeChild(n)

###### config file related functions ###### 

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

if __name__ == '__main__':
    import sharing_settings
    print config_create_xml(sharing_settings, 'http://0.0.0.0:8080')
