#
# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
# This module is free software, and you may redistribute it and/or modify
# under the same terms as Python, so long as this copyright message and
# disclaimer are retained in their original form.
#
# IN NO EVENT SHALL BIZAR SOFTWARE PTY LTD BE LIABLE TO ANY PARTY FOR
# DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING
# OUT OF THE USE OF THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# BIZAR SOFTWARE PTY LTD SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS"
# BASIS, AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
# SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
# 
# $Id: cgi_client.py,v 1.38 2001-10-22 03:25:01 richard Exp $

import os, cgi, pprint, StringIO, urlparse, re, traceback, mimetypes
import base64, Cookie, time

import roundupdb, htmltemplate, date, hyperdb, password

class Unauthorised(ValueError):
    pass

class NotFound(ValueError):
    pass

class Client:
    '''
    A note about login
    ------------------

    If the user has no login cookie, then they are anonymous. There
    are two levels of anonymous use. If there is no 'anonymous' user, there
    is no login at all and the database is opened in read-only mode. If the
    'anonymous' user exists, the user is logged in using that user (though
    there is no cookie). This allows them to modify the database, and all
    modifications are attributed to the 'anonymous' user.


    Customisation
    -------------
      FILTER_POSITION - one of 'top', 'bottom', 'top and bottom'
      ANONYMOUS_ACCESS - one of 'deny', 'allow'
      ANONYMOUS_REGISTER - one of 'deny', 'allow'

    '''
    FILTER_POSITION = 'bottom'       # one of 'top', 'bottom', 'top and bottom'
    ANONYMOUS_ACCESS = 'deny'        # one of 'deny', 'allow'
    ANONYMOUS_REGISTER = 'deny'      # one of 'deny', 'allow'

    def __init__(self, instance, out, env):
        self.instance = instance
        self.out = out
        self.env = env
        self.path = env['PATH_INFO']
        self.split_path = self.path.split('/')

        self.headers_done = 0
        self.form = cgi.FieldStorage(environ=env)
        self.headers_done = 0
        self.debug = 0

    def getuid(self):
        return self.db.user.lookup(self.user)

    def header(self, headers={'Content-Type':'text/html'}):
        if not headers.has_key('Content-Type'):
            headers['Content-Type'] = 'text/html'
        for entry in headers.items():
            self.out.write('%s: %s\n'%entry)
        self.out.write('\n')
        self.headers_done = 1

    def pagehead(self, title, message=None):
        url = self.env['SCRIPT_NAME'] + '/' #self.env.get('PATH_INFO', '/')
        machine = self.env['SERVER_NAME']
        port = self.env['SERVER_PORT']
        if port != '80': machine = machine + ':' + port
        base = urlparse.urlunparse(('http', machine, url, None, None, None))
        if message is not None:
            message = '<div class="system-msg">%s</div>'%message
        else:
            message = ''
        style = open(os.path.join(self.TEMPLATES, 'style.css')).read()
        if self.user is not None:
            userid = self.db.user.lookup(self.user)
            user_info = '(login: <a href="user%s">%s</a>)'%(userid, self.user)
        else:
            user_info = ''
        self.write('''<html><head>
<title>%s</title>
<style type="text/css">%s</style>
</head>
<body bgcolor=#ffffff>
%s
<table width=100%% border=0 cellspacing=0 cellpadding=2>
<tr class="location-bar"><td><big><strong>%s</strong></big> %s</td></tr>
</table>
'''%(title, style, message, title, user_info))

    def pagefoot(self):
        if self.debug:
            self.write('<hr><small><dl>')
            self.write('<dt><b>Path</b></dt>')
            self.write('<dd>%s</dd>'%(', '.join(map(repr, self.split_path))))
            keys = self.form.keys()
            keys.sort()
            if keys:
                self.write('<dt><b>Form entries</b></dt>')
                for k in self.form.keys():
                    v = str(self.form[k].value)
                    self.write('<dd><em>%s</em>:%s</dd>'%(k, cgi.escape(v)))
            keys = self.env.keys()
            keys.sort()
            self.write('<dt><b>CGI environment</b></dt>')
            for k in keys:
                v = self.env[k]
                self.write('<dd><em>%s</em>:%s</dd>'%(k, cgi.escape(v)))
            self.write('</dl></small>')
        self.write('</body></html>')

    def write(self, content):
        if not self.headers_done:
            self.header()
        self.out.write(content)

    def index_arg(self, arg):
        ''' handle the args to index - they might be a list from the form
            (ie. submitted from a form) or they might be a command-separated
            single string (ie. manually constructed GET args)
        '''
        if self.form.has_key(arg):
            arg =  self.form[arg]
            if type(arg) == type([]):
                return [arg.value for arg in arg]
            return arg.value.split(',')
        return []

    def index_filterspec(self, filter):
        ''' pull the index filter spec from the form

        Links and multilinks want to be lists - the rest are straight
        strings.
        '''
        props = self.db.classes[self.classname].getprops()
        # all the form args not starting with ':' are filters
        filterspec = {}
        for key in self.form.keys():
            if key[0] == ':': continue
            if not props.has_key(key): continue
            if key not in filter: continue
            prop = props[key]
            value = self.form[key]
            if (isinstance(prop, hyperdb.Link) or
                    isinstance(prop, hyperdb.Multilink)):
                if type(value) == type([]):
                    value = [arg.value for arg in value]
                else:
                    value = value.value.split(',')
                l = filterspec.get(key, [])
                l = l + value
                filterspec[key] = l
            else:
                filterspec[key] = value.value
        return filterspec

    def customization_widget(self):
        ''' The customization widget is visible by default. The widget
            visibility is remembered by show_customization.  Visibility
            is not toggled if the action value is "Redisplay"
        '''
        if not self.form.has_key('show_customization'):
            visible = 1
        else:
            visible = int(self.form['show_customization'].value)
            if self.form.has_key('action'):
                if self.form['action'].value != 'Redisplay':
                    visible = self.form['action'].value == '+'
            
        return visible

    default_index_sort = ['-activity']
    default_index_group = ['priority']
    default_index_filter = ['status']
    default_index_columns = ['id','activity','title','status','assignedto']
    default_index_filterspec = {'status': ['1', '2', '3', '4', '5', '6', '7']}
    def index(self):
        ''' put up an index
        '''
        self.classname = 'issue'
        # see if the web has supplied us with any customisation info
        defaults = 1
        for key in ':sort', ':group', ':filter', ':columns':
            if self.form.has_key(key):
                defaults = 0
                break
        if defaults:
            # no info supplied - use the defaults
            sort = self.default_index_sort
            group = self.default_index_group
            filter = self.default_index_filter
            columns = self.default_index_columns
            filterspec = self.default_index_filterspec
        else:
            sort = self.index_arg(':sort')
            group = self.index_arg(':group')
            filter = self.index_arg(':filter')
            columns = self.index_arg(':columns')
            filterspec = self.index_filterspec(filter)
        return self.list(columns=columns, filter=filter, group=group,
            sort=sort, filterspec=filterspec)

    # XXX deviates from spec - loses the '+' (that's a reserved character
    # in URLS
    def list(self, sort=None, group=None, filter=None, columns=None,
            filterspec=None, show_customization=None):
        ''' call the template index with the args

            :sort    - sort by prop name, optionally preceeded with '-'
                     to give descending or nothing for ascending sorting.
            :group   - group by prop name, optionally preceeded with '-' or
                     to sort in descending or nothing for ascending order.
            :filter  - selects which props should be displayed in the filter
                     section. Default is all.
            :columns - selects the columns that should be displayed.
                     Default is all.

        '''
        cn = self.classname
        self.pagehead('Index of %s'%cn)
        if sort is None: sort = self.index_arg(':sort')
        if group is None: group = self.index_arg(':group')
        if filter is None: filter = self.index_arg(':filter')
        if columns is None: columns = self.index_arg(':columns')
        if filterspec is None: filterspec = self.index_filterspec(filter)
        if show_customization is None:
            show_customization = self.customization_widget()

        htmltemplate.index(self, self.TEMPLATES, self.db, cn, filterspec,
            filter, columns, sort, group,
            show_customization=show_customization)
        self.pagefoot()

    def shownode(self, message=None):
        ''' display an item
        '''
        cn = self.classname
        cl = self.db.classes[cn]

        # possibly perform an edit
        keys = self.form.keys()
        num_re = re.compile('^\d+$')
        if keys:
            try:
                props, changed = parsePropsFromForm(self.db, cl, self.form,
                    self.nodeid)
                cl.set(self.nodeid, **props)
                self._post_editnode(self.nodeid, changed)
                # and some nice feedback for the user
                message = '%s edited ok'%', '.join(changed)
            except:
                s = StringIO.StringIO()
                traceback.print_exc(None, s)
                message = '<pre>%s</pre>'%cgi.escape(s.getvalue())

        # now the display
        id = self.nodeid
        if cl.getkey():
            id = cl.get(id, cl.getkey())
        self.pagehead('%s: %s'%(self.classname.capitalize(), id), message)

        nodeid = self.nodeid

        # use the template to display the item
        htmltemplate.item(self, self.TEMPLATES, self.db, self.classname, nodeid)
        self.pagefoot()
    showissue = shownode
    showmsg = shownode

    def showuser(self, message=None):
        ''' display an item
        '''
        if self.user in ('admin', self.db.user.get(self.nodeid, 'username')):
            self.shownode(message)
        else:
            raise Unauthorised

    def showfile(self):
        ''' display a file
        '''
        nodeid = self.nodeid
        cl = self.db.file
        type = cl.get(nodeid, 'type')
        if type == 'message/rfc822':
            type = 'text/plain'
        self.header(headers={'Content-Type': type})
        self.write(cl.get(nodeid, 'content'))

    def _createnode(self):
        ''' create a node based on the contents of the form
        '''
        cl = self.db.classes[self.classname]
        props, dummy = parsePropsFromForm(self.db, cl, self.form)
        return cl.create(**props)

    def _post_editnode(self, nid, changes=None):
        ''' do the linking and message sending part of the node creation
        '''
        cn = self.classname
        cl = self.db.classes[cn]
        # link if necessary
        keys = self.form.keys()
        for key in keys:
            if key == ':multilink':
                value = self.form[key].value
                if type(value) != type([]): value = [value]
                for value in value:
                    designator, property = value.split(':')
                    link, nodeid = roundupdb.splitDesignator(designator)
                    link = self.db.classes[link]
                    value = link.get(nodeid, property)
                    value.append(nid)
                    link.set(nodeid, **{property: value})
            elif key == ':link':
                value = self.form[key].value
                if type(value) != type([]): value = [value]
                for value in value:
                    designator, property = value.split(':')
                    link, nodeid = roundupdb.splitDesignator(designator)
                    link = self.db.classes[link]
                    link.set(nodeid, **{property: nid})

        # generate an edit message
        # don't bother if there's no messages or nosy list 
        props = cl.getprops()
        note = None
        if self.form.has_key('__note'):
            note = self.form['__note']
            note = note.value
        send = len(cl.get(nid, 'nosy', [])) or note
        if (send and props.has_key('messages') and
                isinstance(props['messages'], hyperdb.Multilink) and
                props['messages'].classname == 'msg'):

            # handle the note
            if note:
                if '\n' in note:
                    summary = re.split(r'\n\r?', note)[0]
                else:
                    summary = note
                m = ['%s\n'%note]
            else:
                summary = 'This %s has been edited through the web.\n'%cn
                m = [summary]

            first = 1
            for name, prop in props.items():
                if changes is not None and name not in changes: continue
                if first:
                    m.append('\n-------')
                    first = 0
                value = cl.get(nid, name, None)
                if isinstance(prop, hyperdb.Link):
                    link = self.db.classes[prop.classname]
                    key = link.labelprop(default_to_id=1)
                    if value is not None and key:
                        value = link.get(value, key)
                    else:
                        value = '-'
                elif isinstance(prop, hyperdb.Multilink):
                    if value is None: value = []
                    l = []
                    link = self.db.classes[prop.classname]
                    key = link.labelprop(default_to_id=1)
                    for entry in value:
                        if key:
                            l.append(link.get(entry, key))
                        else:
                            l.append(entry)
                    value = ', '.join(l)
                m.append('%s: %s'%(name, value))

            # now create the message
            content = '\n'.join(m)
            message_id = self.db.msg.create(author=self.getuid(),
                recipients=[], date=date.Date('.'), summary=summary,
                content=content)
            messages = cl.get(nid, 'messages')
            messages.append(message_id)
            props = {'messages': messages}
            cl.set(nid, **props)

    def newnode(self, message=None):
        ''' Add a new node to the database.
        
        The form works in two modes: blank form and submission (that is,
        the submission goes to the same URL). **Eventually this means that
        the form will have previously entered information in it if
        submission fails.

        The new node will be created with the properties specified in the
        form submission. For multilinks, multiple form entries are handled,
        as are prop=value,value,value. You can't mix them though.

        If the new node is to be referenced from somewhere else immediately
        (ie. the new node is a file that is to be attached to a support
        issue) then supply one of these arguments in addition to the usual
        form entries:
            :link=designator:property
            :multilink=designator:property
        ... which means that once the new node is created, the "property"
        on the node given by "designator" should now reference the new
        node's id. The node id will be appended to the multilink.
        '''
        cn = self.classname
        cl = self.db.classes[cn]

        # possibly perform a create
        keys = self.form.keys()
        if [i for i in keys if i[0] != ':']:
            props = {}
            try:
                nid = self._createnode()
                self._post_editnode(nid)
                # and some nice feedback for the user
                message = '%s created ok'%cn
            except:
                s = StringIO.StringIO()
                traceback.print_exc(None, s)
                message = '<pre>%s</pre>'%cgi.escape(s.getvalue())
        self.pagehead('New %s'%self.classname.capitalize(), message)
        htmltemplate.newitem(self, self.TEMPLATES, self.db, self.classname,
            self.form)
        self.pagefoot()
    newissue = newnode
    newuser = newnode

    def newfile(self, message=None):
        ''' Add a new file to the database.
        
        This form works very much the same way as newnode - it just has a
        file upload.
        '''
        cn = self.classname
        cl = self.db.classes[cn]

        # possibly perform a create
        keys = self.form.keys()
        if [i for i in keys if i[0] != ':']:
            try:
                file = self.form['content']
                type = mimetypes.guess_type(file.filename)[0]
                if not type:
                    type = "application/octet-stream"
                self._post_editnode(cl.create(content=file.file.read(),
                    type=type, name=file.filename))
                # and some nice feedback for the user
                message = '%s created ok'%cn
            except:
                s = StringIO.StringIO()
                traceback.print_exc(None, s)
                message = '<pre>%s</pre>'%cgi.escape(s.getvalue())

        self.pagehead('New %s'%self.classname.capitalize(), message)
        htmltemplate.newitem(self, self.TEMPLATES, self.db, self.classname,
            self.form)
        self.pagefoot()

    def classes(self, message=None):
        ''' display a list of all the classes in the database
        '''
        if self.user == 'admin':
            self.pagehead('Table of classes', message)
            classnames = self.db.classes.keys()
            classnames.sort()
            self.write('<table border=0 cellspacing=0 cellpadding=2>\n')
            for cn in classnames:
                cl = self.db.getclass(cn)
                self.write('<tr class="list-header"><th colspan=2 align=left>%s</th></tr>'%cn.capitalize())
                for key, value in cl.properties.items():
                    if value is None: value = ''
                    else: value = str(value)
                    self.write('<tr><th align=left>%s</th><td>%s</td></tr>'%(
                        key, cgi.escape(value)))
            self.write('</table>')
            self.pagefoot()
        else:
            raise Unauthorised

    def login(self, message=None):
        self.pagehead('Login to roundup', message)
        self.write('''
<table>
<tr><td colspan=2 class="strong-header">Existing User Login</td></tr>
<form action="login_action" method=POST>
<tr><td align=right>Login name: </td>
    <td><input name="__login_name"></td></tr>
<tr><td align=right>Password: </td>
    <td><input type="password" name="__login_password"></td></tr>
<tr><td></td>
    <td><input type="submit" value="Log In"></td></tr>
</form>
''')
        if self.user is None and not self.ANONYMOUS_REGISTER == 'deny':
            self.write('</table')
            return
        self.write('''
<p>
<tr><td colspan=2 class="strong-header">New User Registration</td></tr>
<tr><td colspan=2><em>marked items</em> are optional...</td></tr>
<form action="newuser_action" method=POST>
<tr><td align=right><em>Name: </em></td>
    <td><input name="__newuser_realname"></td></tr>
<tr><td align=right><em>Organisation: </em></td>
    <td><input name="__newuser_organisation"></td></tr>
<tr><td align=right>E-Mail Address: </td>
    <td><input name="__newuser_address"></td></tr>
<tr><td align=right><em>Phone: </em></td>
    <td><input name="__newuser_phone"></td></tr>
<tr><td align=right>Preferred Login name: </td>
    <td><input name="__newuser_username"></td></tr>
<tr><td align=right>Password: </td>
    <td><input type="password" name="__newuser_password"></td></tr>
<tr><td align=right>Password Again: </td>
    <td><input type="password" name="__newuser_confirm"></td></tr>
<tr><td></td>
    <td><input type="submit" value="Register"></td></tr>
</form>
</table>
''')

    def login_action(self, message=None):
        if not self.form.has_key('__login_name'):
            return self.login(message='Username required')
        self.user = self.form['__login_name'].value
        if self.form.has_key('__login_password'):
            password = self.form['__login_password'].value
        else:
            password = ''
        # make sure the user exists
        try:
            uid = self.db.user.lookup(self.user)
        except KeyError:
            name = self.user
            self.make_user_anonymous()
            return self.login(message='No such user "%s"'%name)

        # and that the password is correct
        pw = self.db.user.get(uid, 'password')
        if password != self.db.user.get(uid, 'password'):
            self.make_user_anonymous()
            return self.login(message='Incorrect password')

        # construct the cookie
        uid = self.db.user.lookup(self.user)
        user = base64.encodestring('%s:%s'%(self.user, password))[:-1]
        path = '/'.join((self.env['SCRIPT_NAME'], self.env['INSTANCE_NAME'],
            ''))
        self.header({'Set-Cookie': 'roundup_user=%s; Path=%s;'%(user, path)})
        return self.index()

    def make_user_anonymous(self):
        # make us anonymous if we can
        try:
            self.db.user.lookup('anonymous')
            self.user = 'anonymous'
        except KeyError:
            self.user = None

    def logout(self, message=None):
        self.make_user_anonymous()
        # construct the logout cookie
        path = '/'.join((self.env['SCRIPT_NAME'], self.env['INSTANCE_NAME'],
            ''))
        now = Cookie._getdate()
        self.header({'Set-Cookie':
            'roundup_user=deleted; Max-Age=0; expires=%s; Path=%s;'%(now, path)})
        return self.index()

    def newuser_action(self, message=None):
        ''' create a new user based on the contents of the form and then
        set the cookie
        '''
        # TODO: pre-check the required fields and username key property
        cl = self.db.classes['user']
        props, dummy = parsePropsFromForm(self.db, cl, self.form)
        uid = cl.create(**props)
        self.user = self.db.user.get(uid, 'username')
        password = self.db.user.get(uid, 'password')
        # construct the cookie
        uid = self.db.user.lookup(self.user)
        user = base64.encodestring('%s:%s'%(self.user, password))[:-1]
        path = '/'.join((self.env['SCRIPT_NAME'], self.env['INSTANCE_NAME'],
            ''))
        self.header({'Set-Cookie': 'roundup_user=%s; Path=%s;'%(user, path)})
        return self.index()

    def main(self, dre=re.compile(r'([^\d]+)(\d+)'),
            nre=re.compile(r'new(\w+)')):

        # determine the uid to use
        self.db = self.instance.open('admin')
        cookie = Cookie.Cookie(self.env.get('HTTP_COOKIE', ''))
        user = 'anonymous'
        if (cookie.has_key('roundup_user') and
                cookie['roundup_user'].value != 'deleted'):
            cookie = cookie['roundup_user'].value
            user, password = base64.decodestring(cookie).split(':')
            # make sure the user exists
            try:
                uid = self.db.user.lookup(user)
                # now validate the password
                if password != self.db.user.get(uid, 'password'):
                    user = 'anonymous'
            except KeyError:
                user = 'anonymous'

        # make sure the anonymous user is valid if we're using it
        if user == 'anonymous':
            self.make_user_anonymous()
        else:
            self.user = user
        self.db.close()

        # make sure totally anonymous access is OK
        if self.ANONYMOUS_ACCESS == 'deny' and self.user is None:
            return self.login()

        # re-open the database for real, using the user
        self.db = self.instance.open(self.user)

        # now figure which function to call
        path = self.split_path
        if not path or path[0] in ('', 'index'):
            self.index()
        elif not path:
            raise 'ValueError', 'Path not understood'

        #
        # Everthing ignores path[1:]
        #
        # The file download link generator actually relies on this - it
        # appends the name of the file to the URL so the download file name
        # is correct, but doesn't actually use it.
        action = path[0]
        if action == 'list_classes':
            self.classes()
            return
        if action == 'login':
            self.login()
            return
        if action == 'login_action':
            self.login_action()
            return
        if action == 'newuser_action':
            self.newuser_action()
            return
        if action == 'logout':
            self.logout()
            return
        m = dre.match(action)
        if m:
            self.classname = m.group(1)
            self.nodeid = m.group(2)
            try:
                cl = self.db.classes[self.classname]
            except KeyError:
                raise NotFound
            try:
                cl.get(self.nodeid, 'id')
            except IndexError:
                raise NotFound
            try:
                func = getattr(self, 'show%s'%self.classname)
            except AttributeError:
                raise NotFound
            func()
            return
        m = nre.match(action)
        if m:
            self.classname = m.group(1)
            try:
                func = getattr(self, 'new%s'%self.classname)
            except AttributeError:
                raise NotFound
            func()
            return
        self.classname = action
        try:
            self.db.getclass(self.classname)
        except KeyError:
            raise NotFound
        self.list()

    def __del__(self):
        self.db.close()


class ExtendedClient(Client): 
    '''Includes pages and page heading information that relate to the
       extended schema.
    ''' 
    showsupport = Client.shownode
    showtimelog = Client.shownode
    newsupport = Client.newnode
    newtimelog = Client.newnode

    default_index_sort = ['-activity']
    default_index_group = ['priority']
    default_index_filter = ['status']
    default_index_columns = ['activity','status','title','assignedto']
    default_index_filterspec = {'status': ['1', '2', '3', '4', '5', '6', '7']}

    def pagehead(self, title, message=None):
        url = self.env['SCRIPT_NAME'] + '/' #self.env.get('PATH_INFO', '/')
        machine = self.env['SERVER_NAME']
        port = self.env['SERVER_PORT']
        if port != '80': machine = machine + ':' + port
        base = urlparse.urlunparse(('http', machine, url, None, None, None))
        if message is not None:
            message = '<div class="system-msg">%s</div>'%message
        else:
            message = ''
        style = open(os.path.join(self.TEMPLATES, 'style.css')).read()
        user_name = self.user or ''
        if self.user == 'admin':
            admin_links = ' | <a href="list_classes">Class List</a>'
        else:
            admin_links = ''
        if self.user not in (None, 'anonymous'):
            userid = self.db.user.lookup(self.user)
            user_info = '''
<a href="issue?assignedto=%s&status=-1,unread,deferred,chatting,need-eg,in-progress,testing,done-cbb&:filter=status,assignedto&:sort=activity&:columns=id,activity,status,title,assignedto&:group=priority&show_customization=1">My Issues</a> |
<a href="support?assignedto=%s&status=-1,unread,deferred,chatting,need-eg,in-progress,testing,done-cbb&:filter=status,assignedto&:sort=activity&:columns=id,activity,status,title,assignedto&:group=customername&show_customization=1">My Support</a> |
<a href="user%s">My Details</a> | <a href="logout">Logout</a>
'''%(userid, userid, userid)
        else:
            user_info = '<a href="login">Login</a>'
        if self.user is not None:
            add_links = '''
| Add
<a href="newissue">Issue</a>,
<a href="newsupport">Support</a>,
<a href="newuser">User</a>
'''
        else:
            add_links = ''
        self.write('''<html><head>
<title>%s</title>
<style type="text/css">%s</style>
</head>
<body bgcolor=#ffffff>
%s
<table width=100%% border=0 cellspacing=0 cellpadding=2>
<tr class="location-bar"><td><big><strong>%s</strong></big></td>
<td align=right valign=bottom>%s</td></tr>
<tr class="location-bar">
<td align=left>All
<a href="issue?status=-1,unread,deferred,chatting,need-eg,in-progress,testing,done-cbb&:sort=activity&:filter=status&:columns=id,activity,status,title,assignedto&:group=priority&show_customization=1">Issues</a>,
<a href="support?status=-1,unread,deferred,chatting,need-eg,in-progress,testing,done-cbb&:sort=activity&:filter=status&:columns=id,activity,status,title,assignedto&:group=customername&show_customization=1">Support</a>
| Unassigned
<a href="issue?assignedto=-1&status=-1,unread,deferred,chatting,need-eg,in-progress,testing,done-cbb&:sort=activity&:filter=status,assignedto&:columns=id,activity,status,title,assignedto&:group=priority&show_customization=1">Issues</a>,
<a href="support?assignedto=-1&status=-1,unread,deferred,chatting,need-eg,in-progress,testing,done-cbb&:sort=activity&:filter=status,assignedto&:columns=id,activity,status,title,assignedto&:group=customername&show_customization=1">Support</a>
%s
%s</td>
<td align=right>%s</td>
</table>
'''%(title, style, message, title, user_name, add_links, admin_links,
    user_info))

def parsePropsFromForm(db, cl, form, nodeid=0):
    '''Pull properties for the given class out of the form.
    '''
    props = {}
    changed = []
    keys = form.keys()
    num_re = re.compile('^\d+$')
    for key in keys:
        if not cl.properties.has_key(key):
            continue
        proptype = cl.properties[key]
        if isinstance(proptype, hyperdb.String):
            value = form[key].value.strip()
        elif isinstance(proptype, hyperdb.Password):
            value = password.Password(form[key].value.strip())
        elif isinstance(proptype, hyperdb.Date):
            value = date.Date(form[key].value.strip())
        elif isinstance(proptype, hyperdb.Interval):
            value = date.Interval(form[key].value.strip())
        elif isinstance(proptype, hyperdb.Link):
            value = form[key].value.strip()
            # see if it's the "no selection" choice
            if value == '-1':
                # don't set this property
                continue
            else:
                # handle key values
                link = cl.properties[key].classname
                if not num_re.match(value):
                    try:
                        value = db.classes[link].lookup(value)
                    except KeyError:
                        raise ValueError, 'property "%s": %s not a %s'%(
                            key, value, link)
        elif isinstance(proptype, hyperdb.Multilink):
            value = form[key]
            if type(value) != type([]):
                value = [i.strip() for i in value.value.split(',')]
            else:
                value = [i.value.strip() for i in value]
            link = cl.properties[key].classname
            l = []
            for entry in map(str, value):
                if not num_re.match(entry):
                    try:
                        entry = db.classes[link].lookup(entry)
                    except KeyError:
                        raise ValueError, \
                            'property "%s": "%s" not an entry of %s'%(key,
                            entry, link.capitalize())
                l.append(entry)
            l.sort()
            value = l
        props[key] = value
        # if changed, set it
        if nodeid and value != cl.get(nodeid, key):
            changed.append(key)
            props[key] = value
    return props, changed

#
# $Log: not supported by cvs2svn $
# Revision 1.37  2001/10/21 07:26:35  richard
# feature #473127: Filenames. I modified the file.index and htmltemplate
#  source so that the filename is used in the link and the creation
#  information is displayed.
#
# Revision 1.36  2001/10/21 04:44:50  richard
# bug #473124: UI inconsistency with Link fields.
#    This also prompted me to fix a fairly long-standing usability issue -
#    that of being able to turn off certain filters.
#
# Revision 1.35  2001/10/21 00:17:54  richard
# CGI interface view customisation section may now be hidden (patch from
#  Roch'e Compaan.)
#
# Revision 1.34  2001/10/20 11:58:48  richard
# Catch errors in login - no username or password supplied.
# Fixed editing of password (Password property type) thanks Roch'e Compaan.
#
# Revision 1.33  2001/10/17 00:18:41  richard
# Manually constructing cookie headers now.
#
# Revision 1.32  2001/10/16 03:36:21  richard
# CGI interface wasn't handling checkboxes at all.
#
# Revision 1.31  2001/10/14 10:55:00  richard
# Handle empty strings in HTML template Link function
#
# Revision 1.30  2001/10/09 07:38:58  richard
# Pushed the base code for the extended schema CGI interface back into the
# code cgi_client module so that future updates will be less painful.
# Also removed a debugging print statement from cgi_client.
#
# Revision 1.29  2001/10/09 07:25:59  richard
# Added the Password property type. See "pydoc roundup.password" for
# implementation details. Have updated some of the documentation too.
#
# Revision 1.28  2001/10/08 00:34:31  richard
# Change message was stuffing up for multilinks with no key property.
#
# Revision 1.27  2001/10/05 02:23:24  richard
#  . roundup-admin create now prompts for property info if none is supplied
#    on the command-line.
#  . hyperdb Class getprops() method may now return only the mutable
#    properties.
#  . Login now uses cookies, which makes it a whole lot more flexible. We can
#    now support anonymous user access (read-only, unless there's an
#    "anonymous" user, in which case write access is permitted). Login
#    handling has been moved into cgi_client.Client.main()
#  . The "extended" schema is now the default in roundup init.
#  . The schemas have had their page headings modified to cope with the new
#    login handling. Existing installations should copy the interfaces.py
#    file from the roundup lib directory to their instance home.
#  . Incorrectly had a Bizar Software copyright on the cgitb.py module from
#    Ping - has been removed.
#  . Fixed a whole bunch of places in the CGI interface where we should have
#    been returning Not Found instead of throwing an exception.
#  . Fixed a deviation from the spec: trying to modify the 'id' property of
#    an item now throws an exception.
#
# Revision 1.26  2001/09/12 08:31:42  richard
# handle cases where mime type is not guessable
#
# Revision 1.25  2001/08/29 05:30:49  richard
# change messages weren't being saved when there was no-one on the nosy list.
#
# Revision 1.24  2001/08/29 04:49:39  richard
# didn't clean up fully after debugging :(
#
# Revision 1.23  2001/08/29 04:47:18  richard
# Fixed CGI client change messages so they actually include the properties
# changed (again).
#
# Revision 1.22  2001/08/17 00:08:10  richard
# reverted back to sending messages always regardless of who is doing the web
# edit. change notes weren't being saved. bleah. hackish.
#
# Revision 1.21  2001/08/15 23:43:18  richard
# Fixed some isFooTypes that I missed.
# Refactored some code in the CGI code.
#
# Revision 1.20  2001/08/12 06:32:36  richard
# using isinstance(blah, Foo) now instead of isFooType
#
# Revision 1.19  2001/08/07 00:24:42  richard
# stupid typo
#
# Revision 1.18  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.17  2001/08/02 06:38:17  richard
# Roundupdb now appends "mailing list" information to its messages which
# include the e-mail address and web interface address. Templates may
# override this in their db classes to include specific information (support
# instructions, etc).
#
# Revision 1.16  2001/08/02 05:55:25  richard
# Web edit messages aren't sent to the person who did the edit any more. No
# message is generated if they are the only person on the nosy list.
#
# Revision 1.15  2001/08/02 00:34:10  richard
# bleah syntax error
#
# Revision 1.14  2001/08/02 00:26:16  richard
# Changed the order of the information in the message generated by web edits.
#
# Revision 1.13  2001/07/30 08:12:17  richard
# Added time logging and file uploading to the templates.
#
# Revision 1.12  2001/07/30 06:26:31  richard
# Added some documentation on how the newblah works.
#
# Revision 1.11  2001/07/30 06:17:45  richard
# Features:
#  . Added ability for cgi newblah forms to indicate that the new node
#    should be linked somewhere.
# Fixed:
#  . Fixed the agument handling for the roundup-admin find command.
#  . Fixed handling of summary when no note supplied for newblah. Again.
#  . Fixed detection of no form in htmltemplate Field display.
#
# Revision 1.10  2001/07/30 02:37:34  richard
# Temporary measure until we have decent schema migration...
#
# Revision 1.9  2001/07/30 01:25:07  richard
# Default implementation is now "classic" rather than "extended" as one would
# expect.
#
# Revision 1.8  2001/07/29 08:27:40  richard
# Fixed handling of passed-in values in form elements (ie. during a
# drill-down)
#
# Revision 1.7  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
# Revision 1.6  2001/07/29 04:04:00  richard
# Moved some code around allowing for subclassing to change behaviour.
#
# Revision 1.5  2001/07/28 08:16:52  richard
# New issue form handles lack of note better now.
#
# Revision 1.4  2001/07/28 00:34:34  richard
# Fixed some non-string node ids.
#
# Revision 1.3  2001/07/23 03:56:30  richard
# oops, missed a config removal
#
# Revision 1.2  2001/07/22 12:09:32  richard
# Final commit of Grande Splite
#
# Revision 1.1  2001/07/22 11:58:35  richard
# More Grande Splite
#
#
# vim: set filetype=python ts=4 sw=4 et si
