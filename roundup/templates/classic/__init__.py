# $Id: __init__.py,v 1.2 2001-07-24 10:46:22 anthonybaxter Exp $

import sys
from instance_config import *
try:
    from dbinit import *
except:
    pass # in install dir (probably :)
from interfaces import *

# 
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/07/23 23:28:43  richard
# Adding the classic template
#
# Revision 1.3  2001/07/23 23:16:01  richard
# Split off the interfaces (CGI, mailgw) into a separate file from the DB stuff.
#
# Revision 1.2  2001/07/23 04:33:21  anthonybaxter
# split __init__.py into 2. dbinit and instance_config.
#
#
