#
# Copyright (c) 2003 Richard Jones, rjones@ekit-inc.com
# This module is free software, and you may redistribute it and/or modify
# under the same terms as Python, so long as this copyright message and
# disclaimer are retained in their original form.
#
# This module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# $Id: test_cgi.py,v 1.6 2003-01-20 23:05:20 richard Exp $

import unittest, os, shutil, errno, sys, difflib, cgi

from roundup.cgi import client
from roundup import init, instance, password, hyperdb, date

def makeForm(args):
    form = cgi.FieldStorage()
    for k,v in args.items():
        if type(v) is type([]):
            [form.list.append(cgi.MiniFieldStorage(k, x)) for x in v]
        else:
            form.list.append(cgi.MiniFieldStorage(k, v))
    return form

class FormTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = '_test_cgi_form'
        try:
            shutil.rmtree(self.dirname)
        except OSError, error:
            if error.errno not in (errno.ENOENT, errno.ESRCH): raise
        # create the instance
        init.install(self.dirname, 'classic', 'anydbm')
        init.initialise(self.dirname, 'sekrit')
        # check we can load the package
        self.instance = instance.open(self.dirname)
        # and open the database
        self.db = self.instance.open('admin')
        self.db.user.create(username='Chef', address='chef@bork.bork.bork',
            realname='Bork, Chef', roles='User')
        self.db.user.create(username='mary', address='mary@test',
            roles='User', realname='Contrary, Mary')

        test = self.instance.dbinit.Class(self.db, "test",
            boolean=hyperdb.Boolean(), link=hyperdb.Link('test'),
            multilink=hyperdb.Multilink('test'), date=hyperdb.Date(),
            interval=hyperdb.Interval())

    def tearDown(self):
        self.db.close()
        try:
            shutil.rmtree(self.dirname)
        except OSError, error:
            if error.errno not in (errno.ENOENT, errno.ESRCH): raise

    #
    # Empty form
    #
    def testNothing(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({})), {})

    def testNothingWithRequired(self):
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({':required': 'title'}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({':required': 'title,status',
            'status':'1'}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({':required': ['title','status'],
            'status':'1'}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({':required': 'status',
            'status':''}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({':required': 'nosy',
            'nosy':''}))

    #
    # Nonexistant edit
    #
    def testEditNonexistant(self):
        self.assertRaises(IndexError, client.parsePropsFromForm, self.db,
            self.db.test, makeForm({'boolean': ''}), '1')

    #
    # String
    #
    def testEmptyString(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'title': ''})), {})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'title': ' '})), {})
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({'title': ['', '']}))

    def testSetString(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'title': 'foo'})), {'title': 'foo'})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'title': 'a\r\nb\r\n'})), {'title': 'a\nb'})
        nodeid = self.db.issue.create(title='foo')
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'title': 'foo'}), nodeid), {})

    def testEmptyStringSet(self):
        nodeid = self.db.issue.create(title='foo')
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'title': ''}), nodeid), {'title': None})
        nodeid = self.db.issue.create(title='foo')
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'title': ' '}), nodeid), {'title': None})

    #
    # Link
    #
    def testEmptyLink(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'status': ''})), {})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'status': ' '})), {})
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({'status': ['', '']}))
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'status': '-1'})), {})

    def testSetLink(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'status': 'unread'})), {'status': '1'})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'status': '1'})), {'status': '1'})
        nodeid = self.db.issue.create(status='unread')
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'status': 'unread'}), nodeid), {})

    def testUnsetLink(self):
        nodeid = self.db.issue.create(status='unread')
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'status': '-1'}), nodeid), {'status': None})

    def testInvalidLinkValue(self):
# XXX This is not the current behaviour - should we enforce this?
#        self.assertRaises(IndexError, client.parsePropsFromForm, self.db,
#            self.db.issue, makeForm({'status': '4'}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({'status': 'frozzle'}))

        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.test, makeForm({'link': 'frozzle'}))

    #
    # Multilink
    #
    def testEmptyMultilink(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': ''})), {})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': ' '})), {})

    def testSetMultilink(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': '1'})), {'nosy': ['1']})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': 'admin'})), {'nosy': ['1']})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': ['1','2']})), {'nosy': ['1','2']})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': '1,2'})), {'nosy': ['1','2']})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': 'admin,2'})), {'nosy': ['1','2']})

    def testEmptyMultilinkSet(self):
        nodeid = self.db.issue.create(nosy=['1','2'])
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': ''}), nodeid), {'nosy': []})
        nodeid = self.db.issue.create(nosy=['1','2'])
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': ' '}), nodeid), {'nosy': []})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': '1,2'}), nodeid), {})

    def testInvalidMultilinkValue(self):
# XXX This is not the current behaviour - should we enforce this?
#        self.assertRaises(IndexError, client.parsePropsFromForm, self.db,
#            self.db.issue, makeForm({'nosy': '4'}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({'nosy': 'frozzle'}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({'nosy': '1,frozzle'}))

        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.test, makeForm({'multilink': 'frozzle'}))

    def testMultilinkAdd(self):
        nodeid = self.db.issue.create(nosy=['1'])
        # do nothing
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':add:nosy': ''}), nodeid), {})

        # do something ;)
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':add:nosy': '2'}), nodeid), {'nosy': ['1','2']})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':add:nosy': '2,mary'}), nodeid), {'nosy': ['1','2','4']})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':add:nosy': ['2','3']}), nodeid), {'nosy': ['1','2','3']})

    def testMultilinkAddNew(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':add:nosy': ['2','3']})), {'nosy': ['2','3']})

    def testMultilinkRemove(self):
        nodeid = self.db.issue.create(nosy=['1','2'])
        # do nothing
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':remove:nosy': ''}), nodeid), {})

        # do something ;)
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':remove:nosy': '1'}), nodeid), {'nosy': ['2']})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':remove:nosy': 'admin,2'}), nodeid), {'nosy': []})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':remove:nosy': ['1','2']}), nodeid), {'nosy': []})

        # remove one that doesn't exist?
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({':remove:nosy': '4'}), nodeid)

    def testMultilinkRetired(self):
        self.db.user.retire('2')
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({'nosy': ['2','3']})), {'nosy': ['2','3']})
        nodeid = self.db.issue.create(nosy=['1','2'])
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':remove:nosy': '2'}), nodeid), {'nosy': ['1']})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.issue,
            makeForm({':add:nosy': '3'}), nodeid), {'nosy': ['1','2','3']})

    def testAddRemoveNonexistant(self):
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({':remove:foo': '2'}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.issue, makeForm({':add:foo': '2'}))

    #
    # Password
    #
    def testEmptyPassword(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.user,
            makeForm({'password': ''})), {})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.user,
            makeForm({'password': ''})), {})
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.user, makeForm({'password': ['', '']}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.user, makeForm({'password': 'foo',
            'password:confirm': ['', '']}))

    def testSetPassword(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.user,
            makeForm({'password': 'foo', 'password:confirm': 'foo'})),
            {'password': 'foo'})

    def testSetPasswordConfirmBad(self):
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.user, makeForm({'password': 'foo'}))
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.user, makeForm({'password': 'foo',
            'password:confirm': 'bar'}))

    def testEmptyPasswordNotSet(self):
        nodeid = self.db.user.create(username='1',
            password=password.Password('foo'))
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.user,
            makeForm({'password': ''}), nodeid), {})
        nodeid = self.db.user.create(username='2',
            password=password.Password('foo'))
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.user,
            makeForm({'password': '', 'password:confirm': ''}), nodeid), {})

    #
    # Boolean
    #
    def testEmptyBoolean(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'boolean': ''})), {})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'boolean': ' '})), {})
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.test, makeForm({'boolean': ['', '']}))

    def testSetBoolean(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'boolean': 'yes'})), {'boolean': 1})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'boolean': 'a\r\nb\r\n'})), {'boolean': 0})
        nodeid = self.db.test.create(boolean=1)
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'boolean': 'yes'}), nodeid), {})
        nodeid = self.db.test.create(boolean=0)
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'boolean': 'no'}), nodeid), {})

    def testEmptyBooleanSet(self):
        nodeid = self.db.test.create(boolean=0)
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'boolean': ''}), nodeid), {'boolean': None})
        nodeid = self.db.test.create(boolean=1)
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'boolean': ' '}), nodeid), {'boolean': None})

    #
    # Date
    #
    def testEmptyDate(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'date': ''})), {})
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'date': ' '})), {})
        self.assertRaises(ValueError, client.parsePropsFromForm, self.db,
            self.db.test, makeForm({'date': ['', '']}))

    def testSetDate(self):
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'date': '2003-01-01'})),
            {'date': date.Date('2003-01-01')})
        nodeid = self.db.test.create(date=date.Date('2003-01-01'))
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'date': '2003-01-01'}), nodeid), {})

    def testEmptyDateSet(self):
        nodeid = self.db.test.create(date=date.Date('.'))
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'date': ''}), nodeid), {'date': None})
        nodeid = self.db.test.create(date=date.Date('1970-01-01.00:00:00'))
        self.assertEqual(client.parsePropsFromForm(self.db, self.db.test,
            makeForm({'date': ' '}), nodeid), {'date': None})

def suite():
    l = [unittest.makeSuite(FormTestCase),
    ]
    return unittest.TestSuite(l)


# vim: set filetype=python ts=4 sw=4 et si
