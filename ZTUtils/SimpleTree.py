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
__doc__='''Simple Tree classes

$Id: SimpleTree.py,v 1.1 2002-08-30 08:25:34 richard Exp $'''
__version__='$Revision: 1.1 $'[11:-2]

from Tree import TreeMaker, TreeNode, b2a

class SimpleTreeNode(TreeNode):
    def branch(self):
        if self.state == 0:
            return {'link': None, 'img': '&nbsp;&nbsp;'}

        if self.state < 0:
            setst = 'expand'
            exnum = self.aq_parent.expansion_number
            img = 'pl'
        else:
            setst = 'collapse'
            exnum = self.expansion_number
            img = 'mi'

        base = self.aq_acquire('baseURL')
        obid = self.id
        pre = self.aq_acquire('tree_pre')

        return {'link': '?%s-setstate=%s,%s,%s#%s' % (pre, setst[0],
                                                      exnum, obid, obid),
        'img': '<img src="%s/p_/%s" alt="%s" border="0">' % (base, img, setst)}
        

class SimpleTreeMaker(TreeMaker):
    '''Generate Simple Trees'''

    def __init__(self, tree_pre="tree"):
        self.tree_pre = tree_pre

    def node(self, object):
        node = SimpleTreeNode()
        node.object = object
        node.id = b2a(self.getId(object))
        return node

    def markRoot(self, node):
        node.tree_pre = self.tree_pre
        node.baseURL = node.object.REQUEST['BASEPATH1']
