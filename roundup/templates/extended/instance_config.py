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
# $Id: instance_config.py,v 1.8 2001-10-23 01:00:18 richard Exp $

MAIL_DOMAIN=MAILHOST=HTTP_HOST=None
HTTP_PORT=0

try:
    from localconfig import *
except ImportError:
    localconfig = None

import os

# roundup home is this package's directory
INSTANCE_HOME=os.path.split(__file__)[0]

# The SMTP mail host that roundup will use to send mail
if not MAILHOST:
    MAILHOST = 'localhost'

# The domain name used for email addresses.
if not MAIL_DOMAIN:
    MAIL_DOMAIN = 'fill.me.in.'

# the next two are only used for the standalone HTTP server.
if not HTTP_HOST:
    HTTP_HOST = ''
if not HTTP_PORT:
    HTTP_PORT = 9080

# This is the directory that the database is going to be stored in
DATABASE = os.path.join(INSTANCE_HOME, 'db')

# This is the directory that the HTML templates reside in
TEMPLATES = os.path.join(INSTANCE_HOME, 'html')

# The email address that mail to roundup should go to
ISSUE_TRACKER_EMAIL = 'issue_tracker@%s'%MAIL_DOMAIN

# The web address that the instance is viewable at
ISSUE_TRACKER_WEB = 'http://some.useful.url/'

# The email address that roundup will complain to if it runs into trouble
ADMIN_EMAIL = 'roundup-admin@%s'%MAIL_DOMAIN

# Somewhere for roundup to log stuff internally sent to stdout or stderr
LOG = os.path.join(INSTANCE_HOME, 'roundup.log')

# Where to place the web filtering HTML on the index page
FILTER_POSITION = 'bottom'      # one of 'top', 'bottom', 'top and bottom'

# Deny or allow anonymous access to the web interface
ANONYMOUS_ACCESS = 'deny'

# Deny or allow anonymous users to register through the web interface
ANONYMOUS_REGISTER = 'deny'

#
# $Log: not supported by cvs2svn $
# Revision 1.7  2001/10/22 03:25:01  richard
# Added configuration for:
#  . anonymous user access and registration (deny/allow)
#  . filter "widget" location on index page (top, bottom, both)
# Updated some documentation.
#
# Revision 1.6  2001/10/01 06:10:42  richard
# stop people setting up roundup with our addresses as default - need to
# handle this better in the init
#
# Revision 1.5  2001/08/07 00:24:43  richard
# stupid typo
#
# Revision 1.4  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.3  2001/08/02 06:38:17  richard
# Roundupdb now appends "mailing list" information to its messages which
# include the e-mail address and web interface address. Templates may
# override this in their db classes to include specific information (support
# instructions, etc).
#
# Revision 1.2  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
# Revision 1.1  2001/07/23 04:33:21  anthonybaxter
# split __init__.py into 2. dbinit and instance_config.
#
#
# vim: set filetype=python ts=4 sw=4 et si
