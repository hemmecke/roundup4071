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
# $Id: test_mailsplit.py,v 1.6 2001-10-21 03:35:13 richard Exp $

import unittest, cStringIO

from roundup.mailgw import parseContent

class MailsplitTestCase(unittest.TestCase):
    def testPreComment(self):
        s = '''
blah blah blah blah... blah blah? blah blah blah blah blah. blah blah blah
blah blah blah blah blah blah blah blah blah blah blah!

issue_tracker@foo.com wrote:
> blah blah blah blahblah blahblah blahblah blah blah blah blah blah blah
> blah blah blah blah blah blah blah blah blah?  blah blah blah blah blah
> blah blah blah blah blah blah blah...  blah blah blah blah.  blah blah
> blah blah blah blah?  blah blah blah blah blah blah!  blah blah!
>
> -------
> nosy: userfoo, userken
> _________________________________________________
> Roundup issue tracker
> issue_tracker@foo.com
> http://foo.com/cgi-bin/roundup.cgi/issue_tracker/

--
blah blah blah signature
userfoo@foo.com
'''
        summary, content = parseContent(s)
        self.assertEqual(summary, 'blah blah blah blah... blah blah? blah blah blah blah blah. blah blah blah')
        self.assertEqual(content, 'blah blah blah blah... blah blah? blah blah blah blah blah. blah blah blah\nblah blah blah blah blah blah blah blah blah blah blah!')

    def testPostComment(self):
        s = '''
issue_tracker@foo.com wrote:
> blah blah blah blahblah blahblah blahblah blah blah blah blah blah
> blah
> blah blah blah blah blah blah blah blah blah?  blah blah blah blah
> blah
> blah blah blah blah blah blah blah...  blah blah blah blah.  blah
> blah
> blah blah blah blah?  blah blah blah blah blah blah!  blah blah!
>
> -------
> nosy: userfoo, userken
> _________________________________________________
> Roundup issue tracker
> issue_tracker@foo.com
> http://foo.com/cgi-bin/roundup.cgi/issue_tracker/

blah blah blah blah... blah blah? blah blah blah blah blah. blah blah blah
blah blah blah blah blah blah blah blah blah blah blah!

--
blah blah blah signature
userfoo@foo.com
'''
        summary, content = parseContent(s)
        self.assertEqual(summary, 'blah blah blah blah... blah blah? blah blah blah blah blah. blah blah blah')
        self.assertEqual(content, 'blah blah blah blah... blah blah? blah blah blah blah blah. blah blah blah\nblah blah blah blah blah blah blah blah blah blah blah!')

    def testSimple(self):
        s = '''testing'''
        summary, content = parseContent(s)
        self.assertEqual(summary, 'testing')
        self.assertEqual(content, 'testing')

    def testParagraphs(self):
        s = '''testing\n\ntesting\n\ntesting'''
        summary, content = parseContent(s)
        print `summary`, `content`
        self.assertEqual(summary, 'testing')
        self.assertEqual(content, 'testing\n\ntesting\n\ntesting')

    def testEmpty(self):
        s = ''
        summary, content = parseContent(s)
        self.assertEqual(summary, '')
        self.assertEqual(content, '')

def suite():
   return unittest.makeSuite(MailsplitTestCase, 'test')


#
# $Log: not supported by cvs2svn $
# Revision 1.5  2001/08/07 00:24:43  richard
# stupid typo
#
# Revision 1.4  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.3  2001/08/05 07:06:25  richard
# removed some print statements
#
# Revision 1.2  2001/08/03 07:23:09  richard
# er, removed the innocent from the the code :)
#
# Revision 1.1  2001/08/03 07:18:22  richard
# Implemented correct mail splitting (was taking a shortcut). Added unit
# tests. Also snips signatures now too.
#
#
#
# vim: set filetype=python ts=4 sw=4 et si
