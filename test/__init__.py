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
# $Id: __init__.py,v 1.7 2001-08-07 00:24:43 richard Exp $

import unittest

import test_dates, test_schema, test_db, test_multipart, test_mailsplit
import test_init

def go():
    suite = unittest.TestSuite((
        test_dates.suite(),
        test_schema.suite(),
        test_db.suite(),
        test_init.suite(),
        test_multipart.suite(),
        test_mailsplit.suite(),
    ))
    runner = unittest.TextTestRunner()
    runner.run(suite)

#
# $Log: not supported by cvs2svn $
# Revision 1.6  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.5  2001/08/05 07:45:27  richard
# Added tests for instance initialisation
#
# Revision 1.4  2001/08/03 07:18:22  richard
# Implemented correct mail splitting (was taking a shortcut). Added unit
# tests. Also snips signatures now too.
#
# Revision 1.3  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
# Revision 1.2  2001/07/28 06:43:02  richard
# Multipart message class has the getPart method now. Added some tests for it.
#
# Revision 1.1  2001/07/27 06:55:07  richard
# moving tests -> test
#
# Revision 1.3  2001/07/25 04:34:31  richard
# Added id and log to tests files...
#
#
# vim: set filetype=python ts=4 sw=4 et si
