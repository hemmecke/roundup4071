##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
# 
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
# 
##############################################################################
__doc__='''Package wrapper for Page Templates

This wrapper allows the Page Template modules to be segregated in a
separate package.

$Id: __init__.py,v 1.1 2002-08-30 08:27:34 richard Exp $'''
__version__='$$'[11:-2]


# Placeholder for Zope Product data
misc_ = {}

def initialize(context):
    # Import lazily, and defer initialization to the module
    import ZopePageTemplate
    ZopePageTemplate.initialize(context)
