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
# $Id: hyperdb.py,v 1.19 2001-08-29 04:47:18 richard Exp $

# standard python modules
import cPickle, re, string

# roundup modules
import date


#
# Types
#
class String:
    """An object designating a String property."""
    def __repr__(self):
        return '<%s>'%self.__class__

class Date:
    """An object designating a Date property."""
    def __repr__(self):
        return '<%s>'%self.__class__

class Interval:
    """An object designating an Interval property."""
    def __repr__(self):
        return '<%s>'%self.__class__

class Link:
    """An object designating a Link property that links to a
       node in a specified class."""
    def __init__(self, classname):
        self.classname = classname
    def __repr__(self):
        return '<%s to "%s">'%(self.__class__, self.classname)

class Multilink:
    """An object designating a Multilink property that links
       to nodes in a specified class.
    """
    def __init__(self, classname):
        self.classname = classname
    def __repr__(self):
        return '<%s to "%s">'%(self.__class__, self.classname)

class DatabaseError(ValueError):
    pass


#
# the base Database class
#
class Database:
    # flag to set on retired entries
    RETIRED_FLAG = '__hyperdb_retired'


_marker = []
#
# The base Class class
#
class Class:
    """The handle to a particular class of nodes in a hyperdatabase."""

    def __init__(self, db, classname, **properties):
        """Create a new class with a given name and property specification.

        'classname' must not collide with the name of an existing class,
        or a ValueError is raised.  The keyword arguments in 'properties'
        must map names to property objects, or a TypeError is raised.
        """
        self.classname = classname
        self.properties = properties
        self.db = db
        self.key = ''

        # do the db-related init stuff
        db.addclass(self)

    # Editing nodes:

    def create(self, **propvalues):
        """Create a new node of this class and return its id.

        The keyword arguments in 'propvalues' map property names to values.

        The values of arguments must be acceptable for the types of their
        corresponding properties or a TypeError is raised.
        
        If this class has a key property, it must be present and its value
        must not collide with other key strings or a ValueError is raised.
        
        Any other properties on this class that are missing from the
        'propvalues' dictionary are set to None.
        
        If an id in a link or multilink property does not refer to a valid
        node, an IndexError is raised.
        """
        if propvalues.has_key('id'):
            raise KeyError, '"id" is reserved'

        if self.db.journaltag is None:
            raise DatabaseError, 'Database open read-only'

        # new node's id
        newid = str(self.count() + 1)

        # validate propvalues
        num_re = re.compile('^\d+$')
        for key, value in propvalues.items():
            if key == self.key:
                try:
                    self.lookup(value)
                except KeyError:
                    pass
                else:
                    raise ValueError, 'node with key "%s" exists'%value

            # try to handle this property
            try:
                prop = self.properties[key]
            except KeyError:
                raise KeyError, '"%s" has no property "%s"'%(self.classname,
                    key)

            if isinstance(prop, Link):
                if type(value) != type(''):
                    raise ValueError, 'link value must be String'
                link_class = self.properties[key].classname
                # if it isn't a number, it's a key
                if not num_re.match(value):
                    try:
                        value = self.db.classes[link_class].lookup(value)
                    except:
                        raise IndexError, 'new property "%s": %s not a %s'%(
                            key, value, self.properties[key].classname)
                propvalues[key] = value
                if not self.db.hasnode(link_class, value):
                    raise IndexError, '%s has no node %s'%(link_class, value)

                # register the link with the newly linked node
                self.db.addjournal(link_class, value, 'link',
                    (self.classname, newid, key))

            elif isinstance(prop, Multilink):
                if type(value) != type([]):
                    raise TypeError, 'new property "%s" not a list of ids'%key
                link_class = self.properties[key].classname
                l = []
                for entry in value:
                    if type(entry) != type(''):
                        raise ValueError, 'link value must be String'
                    # if it isn't a number, it's a key
                    if not num_re.match(entry):
                        try:
                            entry = self.db.classes[link_class].lookup(entry)
                        except:
                            raise IndexError, 'new property "%s": %s not a %s'%(
                                key, entry, self.properties[key].classname)
                    l.append(entry)
                value = l
                propvalues[key] = value

                # handle additions
                for id in value:
                    if not self.db.hasnode(link_class, id):
                        raise IndexError, '%s has no node %s'%(link_class, id)
                    # register the link with the newly linked node
                    self.db.addjournal(link_class, id, 'link',
                        (self.classname, newid, key))

            elif isinstance(prop, String):
                if type(value) != type(''):
                    raise TypeError, 'new property "%s" not a string'%key

            elif isinstance(prop, Date):
                if not isinstance(value, date.Date):
                    raise TypeError, 'new property "%s" not a Date'% key

            elif isinstance(prop, Interval):
                if not isinstance(value, date.Interval):
                    raise TypeError, 'new property "%s" not an Interval'% key

        for key, prop in self.properties.items():
            if propvalues.has_key(key):
                continue
            if isinstance(prop, Multilink):
                propvalues[key] = []
            else:
                propvalues[key] = None

        # done
        self.db.addnode(self.classname, newid, propvalues)
        self.db.addjournal(self.classname, newid, 'create', propvalues)
        return newid

    def get(self, nodeid, propname, default=_marker):
        """Get the value of a property on an existing node of this class.

        'nodeid' must be the id of an existing node of this class or an
        IndexError is raised.  'propname' must be the name of a property
        of this class or a KeyError is raised.
        """
        if propname == 'id':
            return nodeid
        d = self.db.getnode(self.classname, nodeid)
        if not d.has_key(propname) and default is not _marker:
            return default
        return d[propname]

    # XXX not in spec
    def getnode(self, nodeid):
        ''' Return a convenience wrapper for the node
        '''
        return Node(self, nodeid)

    def set(self, nodeid, **propvalues):
        """Modify a property on an existing node of this class.
        
        'nodeid' must be the id of an existing node of this class or an
        IndexError is raised.

        Each key in 'propvalues' must be the name of a property of this
        class or a KeyError is raised.

        All values in 'propvalues' must be acceptable types for their
        corresponding properties or a TypeError is raised.

        If the value of the key property is set, it must not collide with
        other key strings or a ValueError is raised.

        If the value of a Link or Multilink property contains an invalid
        node id, a ValueError is raised.
        """
        if not propvalues:
            return

        if propvalues.has_key('id'):
            raise KeyError, '"id" is reserved'

        if self.db.journaltag is None:
            raise DatabaseError, 'Database open read-only'

        node = self.db.getnode(self.classname, nodeid)
        if node.has_key(self.db.RETIRED_FLAG):
            raise IndexError
        num_re = re.compile('^\d+$')
        for key, value in propvalues.items():
            if not node.has_key(key):
                raise KeyError, key

            # check to make sure we're not duplicating an existing key
            if key == self.key and node[key] != value:
                try:
                    self.lookup(value)
                except KeyError:
                    pass
                else:
                    raise ValueError, 'node with key "%s" exists'%value

            prop = self.properties[key]

            if isinstance(prop, Link):
                link_class = self.properties[key].classname
                # if it isn't a number, it's a key
                if type(value) != type(''):
                    raise ValueError, 'link value must be String'
                if not num_re.match(value):
                    try:
                        value = self.db.classes[link_class].lookup(value)
                    except:
                        raise IndexError, 'new property "%s": %s not a %s'%(
                            key, value, self.properties[key].classname)

                if not self.db.hasnode(link_class, value):
                    raise IndexError, '%s has no node %s'%(link_class, value)

                # register the unlink with the old linked node
                if node[key] is not None:
                    self.db.addjournal(link_class, node[key], 'unlink',
                        (self.classname, nodeid, key))

                # register the link with the newly linked node
                if value is not None:
                    self.db.addjournal(link_class, value, 'link',
                        (self.classname, nodeid, key))

            elif isinstance(prop, Multilink):
                if type(value) != type([]):
                    raise TypeError, 'new property "%s" not a list of ids'%key
                link_class = self.properties[key].classname
                l = []
                for entry in value:
                    # if it isn't a number, it's a key
                    if type(entry) != type(''):
                        raise ValueError, 'link value must be String'
                    if not num_re.match(entry):
                        try:
                            entry = self.db.classes[link_class].lookup(entry)
                        except:
                            raise IndexError, 'new property "%s": %s not a %s'%(
                                key, entry, self.properties[key].classname)
                    l.append(entry)
                value = l
                propvalues[key] = value

                #handle removals
                l = node[key]
                for id in l[:]:
                    if id in value:
                        continue
                    # register the unlink with the old linked node
                    self.db.addjournal(link_class, id, 'unlink',
                        (self.classname, nodeid, key))
                    l.remove(id)

                # handle additions
                for id in value:
                    if not self.db.hasnode(link_class, id):
                        raise IndexError, '%s has no node %s'%(link_class, id)
                    if id in l:
                        continue
                    # register the link with the newly linked node
                    self.db.addjournal(link_class, id, 'link',
                        (self.classname, nodeid, key))
                    l.append(id)

            elif isinstance(prop, String):
                if value is not None and type(value) != type(''):
                    raise TypeError, 'new property "%s" not a string'%key

            elif isinstance(prop, Date):
                if not isinstance(value, date.Date):
                    raise TypeError, 'new property "%s" not a Date'% key

            elif isinstance(prop, Interval):
                if not isinstance(value, date.Interval):
                    raise TypeError, 'new property "%s" not an Interval'% key

            node[key] = value

        self.db.setnode(self.classname, nodeid, node)
        self.db.addjournal(self.classname, nodeid, 'set', propvalues)

    def retire(self, nodeid):
        """Retire a node.
        
        The properties on the node remain available from the get() method,
        and the node's id is never reused.
        
        Retired nodes are not returned by the find(), list(), or lookup()
        methods, and other nodes may reuse the values of their key properties.
        """
        if self.db.journaltag is None:
            raise DatabaseError, 'Database open read-only'
        node = self.db.getnode(self.classname, nodeid)
        node[self.db.RETIRED_FLAG] = 1
        self.db.setnode(self.classname, nodeid, node)
        self.db.addjournal(self.classname, nodeid, 'retired', None)

    def history(self, nodeid):
        """Retrieve the journal of edits on a particular node.

        'nodeid' must be the id of an existing node of this class or an
        IndexError is raised.

        The returned list contains tuples of the form

            (date, tag, action, params)

        'date' is a Timestamp object specifying the time of the change and
        'tag' is the journaltag specified when the database was opened.
        """
        return self.db.getjournal(self.classname, nodeid)

    # Locating nodes:

    def setkey(self, propname):
        """Select a String property of this class to be the key property.

        'propname' must be the name of a String property of this class or
        None, or a TypeError is raised.  The values of the key property on
        all existing nodes must be unique or a ValueError is raised.
        """
        self.key = propname

    def getkey(self):
        """Return the name of the key property for this class or None."""
        return self.key

    def labelprop(self, default_to_id=0):
        ''' Return the property name for a label for the given node.

        This method attempts to generate a consistent label for the node.
        It tries the following in order:
            1. key property
            2. "name" property
            3. "title" property
            4. first property from the sorted property name list
        '''
        k = self.getkey()
        if  k:
            return k
        props = self.getprops()
        if props.has_key('name'):
            return 'name'
        elif props.has_key('title'):
            return 'title'
        if default_to_id:
            return 'id'
        props = props.keys()
        props.sort()
        return props[0]

    # TODO: set up a separate index db file for this? profile?
    def lookup(self, keyvalue):
        """Locate a particular node by its key property and return its id.

        If this class has no key property, a TypeError is raised.  If the
        'keyvalue' matches one of the values for the key property among
        the nodes in this class, the matching node's id is returned;
        otherwise a KeyError is raised.
        """
        cldb = self.db.getclassdb(self.classname)
        for nodeid in self.db.getnodeids(self.classname, cldb):
            node = self.db.getnode(self.classname, nodeid, cldb)
            if node.has_key(self.db.RETIRED_FLAG):
                continue
            if node[self.key] == keyvalue:
                return nodeid
        cldb.close()
        raise KeyError, keyvalue

    # XXX: change from spec - allows multiple props to match
    def find(self, **propspec):
        """Get the ids of nodes in this class which link to a given node.

        'propspec' consists of keyword args propname=nodeid   
          'propname' must be the name of a property in this class, or a
            KeyError is raised.  That property must be a Link or Multilink
            property, or a TypeError is raised.

          'nodeid' must be the id of an existing node in the class linked
            to by the given property, or an IndexError is raised.
        """
        propspec = propspec.items()
        for propname, nodeid in propspec:
            # check the prop is OK
            prop = self.properties[propname]
            if not isinstance(prop, Link) and not isinstance(prop, Multilink):
                raise TypeError, "'%s' not a Link/Multilink property"%propname
            if not self.db.hasnode(prop.classname, nodeid):
                raise ValueError, '%s has no node %s'%(link_class, nodeid)

        # ok, now do the find
        cldb = self.db.getclassdb(self.classname)
        l = []
        for id in self.db.getnodeids(self.classname, cldb):
            node = self.db.getnode(self.classname, id, cldb)
            if node.has_key(self.db.RETIRED_FLAG):
                continue
            for propname, nodeid in propspec:
                property = node[propname]
                if isinstance(prop, Link) and nodeid == property:
                    l.append(id)
                elif isinstance(prop, Multilink) and nodeid in property:
                    l.append(id)
        cldb.close()
        return l

    def stringFind(self, **requirements):
        """Locate a particular node by matching a set of its String properties.

        If the property is not a String property, a TypeError is raised.
        
        The return is a list of the id of all nodes that match.
        """
        for propname in requirements.keys():
            prop = self.properties[propname]
            if isinstance(not prop, String):
                raise TypeError, "'%s' not a String property"%propname
        l = []
        cldb = self.db.getclassdb(self.classname)
        for nodeid in self.db.getnodeids(self.classname, cldb):
            node = self.db.getnode(self.classname, nodeid, cldb)
            if node.has_key(self.db.RETIRED_FLAG):
                continue
            for key, value in requirements.items():
                if node[key] != value:
                    break
            else:
                l.append(nodeid)
        cldb.close()
        return l

    def list(self):
        """Return a list of the ids of the active nodes in this class."""
        l = []
        cn = self.classname
        cldb = self.db.getclassdb(cn)
        for nodeid in self.db.getnodeids(cn, cldb):
            node = self.db.getnode(cn, nodeid, cldb)
            if node.has_key(self.db.RETIRED_FLAG):
                continue
            l.append(nodeid)
        l.sort()
        cldb.close()
        return l

    # XXX not in spec
    def filter(self, filterspec, sort, group, num_re = re.compile('^\d+$')):
        ''' Return a list of the ids of the active nodes in this class that
            match the 'filter' spec, sorted by the group spec and then the
            sort spec
        '''
        cn = self.classname

        # optimise filterspec
        l = []
        props = self.getprops()
        for k, v in filterspec.items():
            propclass = props[k]
            if isinstance(propclass, Link):
                if type(v) is not type([]):
                    v = [v]
                # replace key values with node ids
                u = []
                link_class =  self.db.classes[propclass.classname]
                for entry in v:
                    if not num_re.match(entry):
                        try:
                            entry = link_class.lookup(entry)
                        except:
                            raise ValueError, 'new property "%s": %s not a %s'%(
                                k, entry, self.properties[k].classname)
                    u.append(entry)

                l.append((0, k, u))
            elif isinstance(propclass, Multilink):
                if type(v) is not type([]):
                    v = [v]
                # replace key values with node ids
                u = []
                link_class =  self.db.classes[propclass.classname]
                for entry in v:
                    if not num_re.match(entry):
                        try:
                            entry = link_class.lookup(entry)
                        except:
                            raise ValueError, 'new property "%s": %s not a %s'%(
                                k, entry, self.properties[k].classname)
                    u.append(entry)
                l.append((1, k, u))
            elif isinstance(propclass, String):
                # simple glob searching
                v = re.sub(r'([\|\{\}\\\.\+\[\]\(\)])', r'\\\1', v)
                v = v.replace('?', '.')
                v = v.replace('*', '.*?')
                l.append((2, k, re.compile(v, re.I)))
            else:
                l.append((6, k, v))
        filterspec = l

        # now, find all the nodes that are active and pass filtering
        l = []
        cldb = self.db.getclassdb(cn)
        for nodeid in self.db.getnodeids(cn, cldb):
            node = self.db.getnode(cn, nodeid, cldb)
            if node.has_key(self.db.RETIRED_FLAG):
                continue
            # apply filter
            for t, k, v in filterspec:
                if t == 0 and node[k] not in v:
                    # link - if this node'd property doesn't appear in the
                    # filterspec's nodeid list, skip it
                    break
                elif t == 1:
                    # multilink - if any of the nodeids required by the
                    # filterspec aren't in this node's property, then skip
                    # it
                    for value in v:
                        if value not in node[k]:
                            break
                    else:
                        continue
                    break
                elif t == 2 and not v.search(node[k]):
                    # RE search
                    break
#                elif t == 3 and node[k][:len(v)] != v:
#                    # start anchored
#                    break
#                elif t == 4 and node[k][-len(v):] != v:
#                    # end anchored
#                    break
#                elif t == 5 and node[k].find(v) == -1:
#                    # substring search
#                    break
                elif t == 6 and node[k] != v:
                    # straight value comparison for the other types
                    break
            else:
                l.append((nodeid, node))
        l.sort()
        cldb.close()

        # optimise sort
        m = []
        for entry in sort:
            if entry[0] != '-':
                m.append(('+', entry))
            else:
                m.append((entry[0], entry[1:]))
        sort = m

        # optimise group
        m = []
        for entry in group:
            if entry[0] != '-':
                m.append(('+', entry))
            else:
                m.append((entry[0], entry[1:]))
        group = m
        # now, sort the result
        def sortfun(a, b, sort=sort, group=group, properties=self.getprops(),
                db = self.db, cl=self):
            a_id, an = a
            b_id, bn = b
            # sort by group and then sort
            for list in group, sort:
                for dir, prop in list:
                    # handle the properties that might be "faked"
                    if not an.has_key(prop):
                        an[prop] = cl.get(a_id, prop)
                    av = an[prop]
                    if not bn.has_key(prop):
                        bn[prop] = cl.get(b_id, prop)
                    bv = bn[prop]

                    # sorting is class-specific
                    propclass = properties[prop]

                    # String and Date values are sorted in the natural way
                    if isinstance(propclass, String):
                        # clean up the strings
                        if av and av[0] in string.uppercase:
                            av = an[prop] = av.lower()
                        if bv and bv[0] in string.uppercase:
                            bv = bn[prop] = bv.lower()
                    if (isinstance(propclass, String) or
                            isinstance(propclass, Date)):
                        if dir == '+':
                            r = cmp(av, bv)
                            if r != 0: return r
                        elif dir == '-':
                            r = cmp(bv, av)
                            if r != 0: return r

                    # Link properties are sorted according to the value of
                    # the "order" property on the linked nodes if it is
                    # present; or otherwise on the key string of the linked
                    # nodes; or finally on  the node ids.
                    elif isinstance(propclass, Link):
                        link = db.classes[propclass.classname]
                        if av is None and bv is not None: return -1
                        if av is not None and bv is None: return 1
                        if av is None and bv is None: return 0
                        if link.getprops().has_key('order'):
                            if dir == '+':
                                r = cmp(link.get(av, 'order'),
                                    link.get(bv, 'order'))
                                if r != 0: return r
                            elif dir == '-':
                                r = cmp(link.get(bv, 'order'),
                                    link.get(av, 'order'))
                                if r != 0: return r
                        elif link.getkey():
                            key = link.getkey()
                            if dir == '+':
                                r = cmp(link.get(av, key), link.get(bv, key))
                                if r != 0: return r
                            elif dir == '-':
                                r = cmp(link.get(bv, key), link.get(av, key))
                                if r != 0: return r
                        else:
                            if dir == '+':
                                r = cmp(av, bv)
                                if r != 0: return r
                            elif dir == '-':
                                r = cmp(bv, av)
                                if r != 0: return r

                    # Multilink properties are sorted according to how many
                    # links are present.
                    elif isinstance(propclass, Multilink):
                        if dir == '+':
                            r = cmp(len(av), len(bv))
                            if r != 0: return r
                        elif dir == '-':
                            r = cmp(len(bv), len(av))
                            if r != 0: return r
                # end for dir, prop in list:
            # end for list in sort, group:
            # if all else fails, compare the ids
            return cmp(a[0], b[0])

        l.sort(sortfun)
        return [i[0] for i in l]

    def count(self):
        """Get the number of nodes in this class.

        If the returned integer is 'numnodes', the ids of all the nodes
        in this class run from 1 to numnodes, and numnodes+1 will be the
        id of the next node to be created in this class.
        """
        return self.db.countnodes(self.classname)

    # Manipulating properties:

    def getprops(self):
        """Return a dictionary mapping property names to property objects."""
        d = self.properties.copy()
        d['id'] = String()
        return d

    def addprop(self, **properties):
        """Add properties to this class.

        The keyword arguments in 'properties' must map names to property
        objects, or a TypeError is raised.  None of the keys in 'properties'
        may collide with the names of existing properties, or a ValueError
        is raised before any properties have been added.
        """
        for key in properties.keys():
            if self.properties.has_key(key):
                raise ValueError, key
        self.properties.update(properties)


# XXX not in spec
class Node:
    ''' A convenience wrapper for the given node
    '''
    def __init__(self, cl, nodeid):
        self.__dict__['cl'] = cl
        self.__dict__['nodeid'] = nodeid
    def keys(self):
        return self.cl.getprops().keys()
    def has_key(self, name):
        return self.cl.getprops().has_key(name)
    def __getattr__(self, name):
        if self.__dict__.has_key(name):
            return self.__dict__['name']
        try:
            return self.cl.get(self.nodeid, name)
        except KeyError, value:
            raise AttributeError, str(value)
    def __getitem__(self, name):
        return self.cl.get(self.nodeid, name)
    def __setattr__(self, name, value):
        try:
            return self.cl.set(self.nodeid, **{name: value})
        except KeyError, value:
            raise AttributeError, str(value)
    def __setitem__(self, name, value):
        self.cl.set(self.nodeid, **{name: value})
    def history(self):
        return self.cl.history(self.nodeid)
    def retire(self):
        return self.cl.retire(self.nodeid)


def Choice(name, *options):
    cl = Class(db, name, name=hyperdb.String(), order=hyperdb.String())
    for i in range(len(options)):
        cl.create(name=option[i], order=i)
    return hyperdb.Link(name)

#
# $Log: not supported by cvs2svn $
# Revision 1.18  2001/08/16 07:34:59  richard
# better CGI text searching - but hidden filter fields are disappearing...
#
# Revision 1.17  2001/08/16 06:59:58  richard
# all searches use re now - and they're all case insensitive
#
# Revision 1.16  2001/08/15 23:43:18  richard
# Fixed some isFooTypes that I missed.
# Refactored some code in the CGI code.
#
# Revision 1.15  2001/08/12 06:32:36  richard
# using isinstance(blah, Foo) now instead of isFooType
#
# Revision 1.14  2001/08/07 00:24:42  richard
# stupid typo
#
# Revision 1.13  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.12  2001/08/02 06:38:17  richard
# Roundupdb now appends "mailing list" information to its messages which
# include the e-mail address and web interface address. Templates may
# override this in their db classes to include specific information (support
# instructions, etc).
#
# Revision 1.11  2001/08/01 04:24:21  richard
# mailgw was assuming certain properties existed on the issues being created.
#
# Revision 1.10  2001/07/30 02:38:31  richard
# get() now has a default arg - for migration only.
#
# Revision 1.9  2001/07/29 09:28:23  richard
# Fixed sorting by clicking on column headings.
#
# Revision 1.8  2001/07/29 08:27:40  richard
# Fixed handling of passed-in values in form elements (ie. during a
# drill-down)
#
# Revision 1.7  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
# Revision 1.6  2001/07/29 05:36:14  richard
# Cleanup of the link label generation.
#
# Revision 1.5  2001/07/29 04:05:37  richard
# Added the fabricated property "id".
#
# Revision 1.4  2001/07/27 06:25:35  richard
# Fixed some of the exceptions so they're the right type.
# Removed the str()-ification of node ids so we don't mask oopsy errors any
# more.
#
# Revision 1.3  2001/07/27 05:17:14  richard
# just some comments
#
# Revision 1.2  2001/07/22 12:09:32  richard
# Final commit of Grande Splite
#
# Revision 1.1  2001/07/22 11:58:35  richard
# More Grande Splite
#
#
# vim: set filetype=python ts=4 sw=4 et si
