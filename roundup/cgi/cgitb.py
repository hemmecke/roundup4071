#
# This module was written by Ka-Ping Yee, <ping@lfw.org>.
# 
# $Id: cgitb.py,v 1.3 2002-09-06 07:23:29 richard Exp $

__doc__ = """
Extended CGI traceback handler by Ka-Ping Yee, <ping@lfw.org>.
"""

import sys, os, types, string, keyword, linecache, tokenize, inspect, pydoc

from roundup.i18n import _

def breaker():
    return ('<body bgcolor="white">' +
            '<font color="white" size="-5"> > </font> ' +
            '</table>' * 5)

def niceDict(indent, dict):
    l = []
    for k,v in dict.items():
        l.append('%s%s: %r'%(indent,k,v))
    return '\n'.join(l)

def pt_html(context=5):
    import cgi
    etype, evalue = sys.exc_type, sys.exc_value
    if type(etype) is types.ClassType:
        etype = etype.__name__
    pyver = 'Python ' + string.split(sys.version)[0] + '<br>' + sys.executable
    head = pydoc.html.heading(
        '<font size=+1><strong>%s</strong>: %s</font>'%(etype, evalue),
        '#ffffff', '#777777', pyver)

    head = head + _('<p>A problem occurred in your template</p><pre>')

    l = []
    for frame, file, lnum, func, lines, index in inspect.trace(context):
        args, varargs, varkw, locals = inspect.getargvalues(frame)
        if locals.has_key('__traceback_info__'):
            ti = locals['__traceback_info__']
            l.append(str(ti))
        if locals.has_key('__traceback_supplement__'):
            ts = locals['__traceback_supplement__']
            if len(ts) == 2:
                supp, context = ts
                l.append('in template %r'%context.id)
            elif len(ts) == 3:
                supp, context, info = ts
                l.append('in expression %r\n current variables:\n%s\n%s\n'%(info,
                    niceDict('    ', context.global_vars),
                    niceDict('    ', context.local_vars)))
                # context._scope_stack))
    return head + cgi.escape('\n'.join(l)) + '</pre><p>&nbsp;</p>'

def html(context=5):
    etype, evalue = sys.exc_type, sys.exc_value
    if type(etype) is types.ClassType:
        etype = etype.__name__
    pyver = 'Python ' + string.split(sys.version)[0] + '<br>' + sys.executable
    head = pydoc.html.heading(
        '<font size=+1><strong>%s</strong>: %s</font>'%(etype, evalue),
        '#ffffff', '#777777', pyver)

    head = head + (_('<p>A problem occurred while running a Python script. '
                   'Here is the sequence of function calls leading up to '
                   'the error, with the most recent (innermost) call first. '
                   'The exception attributes are:'))

    indent = '<tt><small>%s</small>&nbsp;</tt>' % ('&nbsp;' * 5)
    traceback = []
    for frame, file, lnum, func, lines, index in inspect.trace(context):
        if file is None:
            link = '''&lt;file is None - probably inside <tt>eval</tt> or
                    <tt>exec</tt>&gt;'''
        else:
            file = os.path.abspath(file)
            link = '<a href="file:%s">%s</a>' % (file, pydoc.html.escape(file))
        args, varargs, varkw, locals = inspect.getargvalues(frame)
        if func == '?':
            call = ''
        else:
            call = 'in <strong>%s</strong>' % func + inspect.formatargvalues(
                    args, varargs, varkw, locals,
                    formatvalue=lambda value: '=' + pydoc.html.repr(value))

        level = '''
<table width="100%%" bgcolor="#dddddd" cellspacing=0 cellpadding=2 border=0>
<tr><td>%s %s</td></tr></table>''' % (link, call)

        if index is None or file is None:
            traceback.append('<p>' + level)
            continue

        # do a file inspection
        names = []
        def tokeneater(type, token, start, end, line, names=names):
            if type == tokenize.NAME and token not in keyword.kwlist:
                if token not in names:
                    names.append(token)
            if type == tokenize.NEWLINE: raise IndexError
        def linereader(file=file, lnum=[lnum]):
            line = linecache.getline(file, lnum[0])
            lnum[0] = lnum[0] + 1
            return line

        try:
            tokenize.tokenize(linereader, tokeneater)
        except IndexError:
            pass
        lvals = []
        for name in names:
            if name in frame.f_code.co_varnames:
                if locals.has_key(name):
                    value = pydoc.html.repr(locals[name])
                else:
                    value = _('<em>undefined</em>')
                name = '<strong>%s</strong>' % name
            else:
                if frame.f_globals.has_key(name):
                    value = pydoc.html.repr(frame.f_globals[name])
                else:
                    value = _('<em>undefined</em>')
                name = '<em>global</em> <strong>%s</strong>' % name
            lvals.append('%s&nbsp;= %s'%(name, value))
        if lvals:
            lvals = string.join(lvals, ', ')
            lvals = indent + '<small><font color="#909090">%s'\
                '</font></small><br>'%lvals
        else:
            lvals = ''

        excerpt = []
        i = lnum - index
        for line in lines:
            number = '&nbsp;' * (5-len(str(i))) + str(i)
            number = '<small><font color="#909090">%s</font></small>' % number
            line = '<tt>%s&nbsp;%s</tt>' % (number, pydoc.html.preformat(line))
            if i == lnum:
                line = '''
<table width="100%%" bgcolor="#white" cellspacing=0 cellpadding=0 border=0>
<tr><td>%s</td></tr></table>''' % line
            excerpt.append('\n' + line)
            if i == lnum:
                excerpt.append(lvals)
            i = i + 1
        traceback.append('<p>' + level + string.join(excerpt, '\n'))

    traceback.reverse()

    exception = '<p><strong>%s</strong>: %s' % (str(etype), str(evalue))
    attribs = []
    if type(evalue) is types.InstanceType:
        for name in dir(evalue):
            value = pydoc.html.repr(getattr(evalue, name))
            attribs.append('<br>%s%s&nbsp;= %s' % (indent, name, value))

    return head + string.join(attribs) + string.join(traceback) + '<p>&nbsp;</p>'

def handler():
    print breaker()
    print html()

#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/09/06 07:21:31  richard
# much nicer error messages when there's a templating error
#
# Revision 1.1  2002/08/30 08:28:44  richard
# New CGI interface support
#
# Revision 1.10  2002/01/16 04:49:45  richard
# Handle a special case that the CGI interface tickles. I need to check if
# this needs fixing in python's core.
#
# Revision 1.9  2002/01/08 11:56:24  richard
# missed an import _
#
# Revision 1.8  2002/01/05 02:22:32  richard
# i18n'ification
#
# Revision 1.7  2001/11/22 15:46:42  jhermann
# Added module docstrings to all modules.
#
# Revision 1.6  2001/09/29 13:27:00  richard
# CGI interfaces now spit up a top-level index of all the instances they can
# serve.
#
# Revision 1.5  2001/08/07 00:24:42  richard
# stupid typo
#
# Revision 1.4  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.3  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
# Revision 1.2  2001/07/22 12:09:32  richard
# Final commit of Grande Splite
#
# Revision 1.1  2001/07/22 11:58:35  richard
# More Grande Splite
#
#
# vim: set filetype=python ts=4 sw=4 et si
