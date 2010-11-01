# 
import os
import web
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
CACHE_DIR = 'static'

def _get_host(web):
    return '%s://%s' % (web.ctx.env['wsgi.url_scheme'], web.ctx.env['HTTP_HOST'])

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
            if 'filetype' in data:
                posts.append(u"<a href='/entry/%s'>%s</a>" % (os.path.basename(post), data['summary']))
                if 'filetype' in data and data['filetype'].startswith('image'):
                    posts.append(u"""<img src="/file/%s" width="100" alt=""/>""" % (os.path.basename(post))) 
                    #posts.append(u"<a href='/entry/%s'>%s</a>" % (os.path.basename(post), data['summary']))
        web.header('Content-Type', 'text/html; charset=UTF-8')
        return u"<br/>".join(posts)


class showentry:
    """
    """
    def GET(self, postfile):
        post = os.path.join(RAWPOSTDATA_DIR, postfile)
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
        post = os.path.join(RAWPOSTDATA_DIR, postfile)
        with open(post, 'rb') as f:
            postdata = f.read()
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
            with open(post, 'rb') as f:
                postdata = f.read()
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
        return shareonline.config_create_xml(sharing_settings, host)

def authenticate_user(web):
    http_x_wsse = web.ctx.env.get('HTTP_X_WSSE', '')
    password = 'cat' # hardcoded password
    try:
        auth_user = shareonline.wsse_auth(http_x_wsse, password)
    except shareonline.WsseAuthError, error:
        print error
        auth_user = 'no_wsse_auth'
    return auth_user

class service:
    def GET(self):
        username = authenticate_user(web)
        # If username is None: return wsse_auth error
        host = _get_host(web)
        slist = []
        slist.append({'rel': 'service.post', 'href': host + '/post/pub', 'type': 'application/atom+xml', 'title': 'PUBLIC'})
        if username:
            slist.append({'rel': 'service.post', 'href': host + '/post/res', 'type': 'application/atom+xml', 'title': 'RESTRICED'},)
        slist.append({'rel': 'service.feed', 'href': host + '/feed', 'type': 'application/atom+xml', 'title': 'Shareonline provider demo feed'})
        slist.append({'rel': 'alternate', 'href': host + '', 'type': 'text/html', 'title': 'Shareonline demo site'})
        web.header('Content-Type', 'application/atom+xml; charset=UTF-8')
        return shareonline.services(slist)

def get_filename(post_file, data):
    contentfile_name = os.path.basename(post_file)
    contentfile_body = os.path.splitext(contentfile_name)[0]
    ext = '.' + data['filetype'].split('/')[1]
    return os.path.join(CACHE_DIR, contentfile_body + ext)

class post:
    def POST(self, service):
        username = authenticate_user(web)
        # If username is None: return wsse_auth error
        for DIR in [RAWPOSTDATA_DIR, CACHE_DIR]:
            if os.path.isdir(DIR) == False:
                os.makedirs(DIR)
        post_file = shareonline._save_post_data(web.data(), RAWPOSTDATA_DIR, username + '-request')
        contentfile_name = os.path.basename(post_file)
        #contentfile_body = os.path.splitext(post_file)[0]
        data = shareonline._parse_request_xml(web.data())
        if 'filedata' in data:
            if 'filetype' in data:
                content_filepath = get_filename(post_file, data)
                with open(content_filepath, 'wb') as f:
                    f.write(data['filedata'])
            del data['filedata']
            print data
        else: # read original post
            print data
            post = os.path.join(RAWPOSTDATA_DIR, data['uid'])
            with open(post, 'rb') as f:
                postdata = f.read()
            data = shareonline._parse_request_xml(postdata)
            del data['filedata']
        web.header('Content-Type', 'application/atom+xml; charset=UTF-8')
        data['id'] = contentfile_name
        data['link'] = "/entry/" + contentfile_name
        #print data
        entry_xml = shareonline.create_entry(data)
        #print entry_xml
        web.Created()
        shareonline._save_post_data(entry_xml, RAWPOSTDATA_DIR, username + '-response')
        return entry_xml

app = web.application(urls, globals())

if __name__ == "__main__":
    app.run()

