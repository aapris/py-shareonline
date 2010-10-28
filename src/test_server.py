import os
import datetime
import web
import shareonline_config
import shareonline
import xml.dom.minidom
import glob
import sharing_settings

urls = (
  '/', 'index',
  '/config', 'config',
  '/service', 'service',
  '/post/(.*)', 'post',
  '/latest', 'latest',
  '/feed', 'feed',
  '/entry/(.*)', 'showentry',
  '/file/(.*)', 'showfile',
)


RAWPOSTDATA_DIR = 'rawpostdata'

def _get_host(web):
    return '%s://%s' % (web.ctx.env['wsgi.url_scheme'], web.ctx.env['HTTP_HOST'])

def services(slist):
    services_doc = xml.dom.minidom.parse('shareonline-service.xml')
    feed_e = services_doc.getElementsByTagName('feed')[0]
    while feed_e.hasChildNodes():
        for e in feed_e.childNodes:
            print feed_e.removeChild(e)
    for link in slist:
        link_e = services_doc.createElement('link')
        for attr in link.keys():
            link_e.setAttribute(attr, link[attr])
        feed_e.appendChild(link_e)
    web.header('Content-Type', 'application/atom+xml; charset=UTF-8')
    return services_doc.toprettyxml('', newl='', encoding='utf-8')


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

# Views:

class index:
    """Provides links for all resources."""
    def GET(self):
        #for key in web.ctx.env.keys():
        #    print key, web.ctx.env[key]
        web.header('Content-Type', 'text/html; charset=UTF-8')
        links = [
            ('/config', 'Configuration file for S60'),
            ('/feed', 'Atom feed'),
            ('/latest', 'Latest posts'),
        ]
        html = u"<br/>\n".join([u"<a href='%s'>%s</a>" % (l[0], l[1]) for l in links])
        return html

class latest:
    """Shows links to latest posts."""
    def GET(self):
        posts = []
        for post in glob.glob(RAWPOSTDATA_DIR + '/*.xml'):
            with open(post, 'rb') as f:
                postdata = f.read()
            data = shareonline._parse_request_xml(postdata)
            if 'summary' in data:
                posts.append(u"<a href='/entry/%s'>%s</a>" % (os.path.basename(post), data['summary']))
                if data['filetype'].startswith('image'):
                    posts.append(u"""<img src="/file/%s" width="100" alt=""/>""" % (os.path.basename(post))) 
                    #posts.append(u"<a href='/entry/%s'>%s</a>" % (os.path.basename(post), data['summary']))
        web.header('Content-Type', 'text/html; charset=UTF-8')
        return u"<br/>".join(posts)


class showentry:
    """
    """
    def GET(self, postfile):
        print postfile
        post = RAWPOSTDATA_DIR + '/' + postfile
        with open(post, 'rb') as f:
            postdata = f.read()
        data = shareonline._parse_request_xml(postdata)
        html = []
        html.append(u"""<h1>%(summary)s</h1>""" % (data))
        if data['filetype'].startswith('image'):
            html.append(u"""<img src="/file/%s" width="400" alt=""/>""" % (postfile)) 
        #del data['filedata']
        #print data
        web.header('Content-Type', 'text/html; charset=UTF-8')
        return u"\n".join(html)

class showfile:
    """
    """
    def GET(self, postfile):
        post = RAWPOSTDATA_DIR + '/' + postfile
        postdata = open(post, 'rb').read()
        data = shareonline._parse_request_xml(postdata)
        web.header('Content-Type', data['filetype'])
        return data['filedata']

class feed:
    """
    Returns a very simple and dummy atom feed document of latests posts.
    This function uses plain strings to create document. 
    """
    def GET(self):
        host = _get_host(web)
        posts = ['<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="fi">']
        # Read all raw posts to a list
        postfiles = glob.glob(RAWPOSTDATA_DIR + '/*.xml')
        postfiles.sort()
        postfiles.reverse()
        for post in postfiles:
            postdata = open(post, 'rb').read()
            data = shareonline._parse_request_xml(postdata)
            data['host'] = host
            data['id'] = os.path.basename(post)
            if 'filedata' not in data: continue # this was not a post containing filedata
            posts.append(u"""<entry><title>%(summary)s</title>
         <link href="%(host)s/entry/%(id)s" rel="alternate"></link>
         <updated>%(issued)s</updated>
          <author><name>demo</name><uri>http://www.example.com/</uri></author>
         <id>%(host)s/entry/%(id)s</id>
         <summary type="html"></summary></entry>""" % (data))
        posts.append(u"</feed>")
        web.header('Content-Type', 'application/atom+xml; charset=UTF-8')
        return u"\n".join(posts)

class config:
    def GET(self):
        host = _get_host(web)
        web.header('Content-Type', 'application/isf.sharing.config')
        return shareonline_config.create_config_xml(sharing_settings, host)

class service:
    def GET(self):
        host = _get_host(web)
        slist = [
          {'rel': 'service.post', 'href': host + '/post/pub', 'type': 'application/atom+xml', 'title': 'PUBLIC'},
          {'rel': 'service.post', 'href': host + '/post/res', 'type': 'application/atom+xml', 'title': 'RESTRICED'},
          {'rel': 'service.feed', 'href': host + '/feed', 'type': 'application/atom+xml', 'title': 'Shareonline provider demo feed'},
          {'rel': 'alternate', 'href': host + '', 'type': 'text/html', 'title': 'Shareonline demo site'},
        ]
        web.header('Content-Type', 'application/atom+xml; charset=UTF-8')
        return services(slist)

class post:
    def POST(self, service):
        post_dir = RAWPOSTDATA_DIR
        if os.path.isdir(RAWPOSTDATA_DIR) == False:
            os.makedirs(RAWPOSTDATA_DIR)
        post_file = shareonline._save_post_data(web.data(), post_dir, 'demo')
        contentfile_name = os.path.basename(post_file)
        #contentfile_body = os.path.splitext(contentfile_name)[0]
        #ext = '.jpg'
        data = shareonline._parse_request_xml(web.data())
        if 'filedata' in data:
            #if 'filetype' in data:
            #    ext = '.' + data['filetype'].split('/')[1]
            #content_filepath = os.path.join(content_dir, contentfile_body)
            #f = open(content_filepath + ext, 'wb')
            #f.write(data['filedata'])
            #f.close()
            del data['filedata']
            print data
        else: # read original post
            print data
            postdata = open(RAWPOSTDATA_DIR + '/' + data['uid'], 'rb').read()
            data = shareonline._parse_request_xml(postdata)
            del data['filedata']
        web.header('Content-Type', 'application/atom+xml; charset=UTF-8')
        data['id'] = contentfile_name
        data['link'] = "/entry/" + contentfile_name
        print data
        entry_xml = create_entry(data)
        print entry_xml
        web.Created()
        return entry_xml


app = web.application(urls, globals())

if __name__ == "__main__":
    app.run()

