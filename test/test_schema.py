# $Id: test_schema.py,v 1.2 2001-07-29 07:01:39 richard Exp $ 

import unittest, os, shutil

from roundup.backends import anydbm
from roundup.hyperdb import String, Link, Multilink, Date, Interval, Class

class SchemaTestCase(unittest.TestCase):
    def setUp(self):
        class Database(anydbm.Database):
            pass
        # remove previous test, ignore errors
        if os.path.exists('_test_dir'):
            shutil.rmtree('_test_dir')
        os.mkdir('_test_dir')
        self.db = Database('_test_dir', 'test')
        self.db.clear()

    def tearDown(self):
        self.db.close()
        shutil.rmtree('_test_dir')

    def testA_Status(self):
        status = Class(self.db, "status", name=String())
        self.assert_(status, 'no class object generated')
        status.setkey("name")
        val = status.create(name="unread")
        self.assertEqual(val, '1', 'expecting "1"')
        val = status.create(name="in-progress")
        self.assertEqual(val, '2', 'expecting "2"')
        val = status.create(name="testing")
        self.assertEqual(val, '3', 'expecting "3"')
        val = status.create(name="resolved")
        self.assertEqual(val, '4', 'expecting "4"')
        val = status.count()
        self.assertEqual(val, 4, 'expecting 4')
        val = status.list()
        self.assertEqual(val, ['1', '2', '3', '4'], 'blah')
        val = status.lookup("in-progress")
        self.assertEqual(val, '2', 'expecting "2"')
        status.retire('3')
        val = status.list()
        self.assertEqual(val, ['1', '2', '4'], 'blah')

    def testB_Issue(self):
        issue = Class(self.db, "issue", title=String(), status=Link("status"))
        self.assert_(issue, 'no class object returned')

    def testC_User(self):
        user = Class(self.db, "user", username=String(), password=String())
        self.assert_(user, 'no class object returned')
        user.setkey("username")


def suite():
   return unittest.makeSuite(SchemaTestCase, 'test')


#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/07/27 06:55:07  richard
# moving tests -> test
#
# Revision 1.3  2001/07/25 04:34:31  richard
# Added id and log to tests files...
#
#
# vim: set filetype=python ts=4 sw=4 et si
