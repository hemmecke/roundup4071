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
# $Id: test_init.py,v 1.4 2001-08-07 00:24:43 richard Exp $

import unittest, os, shutil, errno, imp, sys

from roundup.init import init

class MyTestCase(unittest.TestCase):
    count = 0
    def setUp(self):
        MyTestCase.count = MyTestCase.count + 1
        self.dirname = '_test_%s'%self.count
        try:
            shutil.rmtree(self.dirname)
        except OSError, error:
            if error.errno != errno.ENOENT: raise

    def tearDown(self):
        try:
            shutil.rmtree(self.dirname)
        except OSError, error:
            if error.errno != errno.ENOENT: raise

class ClassicTestCase(MyTestCase):
    backend = 'anydbm'
    def testCreation(self):
        ae = self.assertEqual

        # create the instance
        init(self.dirname, 'classic', self.backend, 'sekrit')

        # check we can load the package
        instance = imp.load_package(self.dirname, self.dirname)

        # and open the database
        db = instance.open()

        # check the basics of the schema and initial data set
        l = db.priority.list()
        ae(l, ['1', '2', '3', '4', '5'])
        l = db.status.list()
        ae(l, ['1', '2', '3', '4', '5', '6', '7', '8'])
        l = db.keyword.list()
        ae(l, [])
        l = db.user.list()
        ae(l, ['1'])
        l = db.msg.list()
        ae(l, [])
        l = db.file.list()
        ae(l, [])
        l = db.issue.list()
        ae(l, [])

class ExtendedTestCase(MyTestCase):
    backend = 'anydbm'
    def testCreation(self):
        ae = self.assertEqual

        # create the instance
        init(self.dirname, 'extended', self.backend, 'sekrit')

        # check we can load the package
        instance = imp.load_package(self.dirname, self.dirname)

        # and open the database
        db = instance.open()

        # check the basics of the schema and initial data set
        l = db.priority.list()
        ae(l, ['1', '2', '3', '4'])
        l = db.status.list()
        ae(l, ['1', '2', '3', '4', '5', '6', '7', '8'])
        l = db.keyword.list()
        ae(l, [])
        l = db.user.list()
        ae(l, ['1'])
        l = db.msg.list()
        ae(l, [])
        l = db.file.list()
        ae(l, [])
        l = db.issue.list()
        ae(l, [])
        l = db.support.list()
        ae(l, [])
        l = db.rate.list()
        ae(l, ['1', '2', '3'])
        l = db.source.list()
        ae(l, ['1', '2', '3', '4'])
        l = db.platform.list()
        ae(l, ['1', '2', '3'])
        l = db.timelog.list()
        ae(l, [])

def suite():
    l = [unittest.makeSuite(ClassicTestCase, 'test'),
         unittest.makeSuite(ExtendedTestCase, 'test')]
    try:
        import bsddb
        x = ClassicTestCase
        x.backend = 'bsddb'
        l.append(unittest.makeSuite(x, 'test'))
        x = ExtendedTestCase
        x.backend = 'bsddb'
        l.append(unittest.makeSuite(x, 'test'))
    except:
        print 'bsddb module not found, skipping bsddb DBTestCase'

    try:
        import bsddb3
        x = ClassicTestCase
        x.backend = 'bsddb3'
        l.append(unittest.makeSuite(x, 'test'))
        x = ExtendedTestCase
        x.backend = 'bsddb3'
        l.append(unittest.makeSuite(x, 'test'))
    except:
        print 'bsddb3 module not found, skipping bsddb3 DBTestCase'

    return unittest.TestSuite(l)

#
# $Log: not supported by cvs2svn $
# Revision 1.3  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.2  2001/08/05 07:45:27  richard
# Added tests for instance initialisation
#
# Revision 1.1  2001/08/05 07:07:58  richard
# added tests for roundup.init - but they're disabled until I can figure _if_
# we can run them (import problems).
#
#
#
# vim: set filetype=python ts=4 sw=4 et si
