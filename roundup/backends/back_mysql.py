#
# Copyright (c) 2003 Martynas Sklyzmantas, Andrey Lebedev <andrey@micro.lt>
#
# This module is free software, and you may redistribute it and/or modify
# under the same terms as Python, so long as this copyright message and
# disclaimer are retained in their original form.
#

'''This module defines a backend implementation for MySQL.


How to implement AUTO_INCREMENT:

mysql> create table foo (num integer auto_increment primary key, name
varchar(255)) AUTO_INCREMENT=1 type=InnoDB;

ql> insert into foo (name) values ('foo5');
Query OK, 1 row affected (0.00 sec)

mysql> SELECT num FROM foo WHERE num IS NULL;
+-----+
| num |
+-----+
|   4 |
+-----+
1 row in set (0.00 sec)

mysql> SELECT num FROM foo WHERE num IS NULL;
Empty set (0.00 sec)

NOTE: we don't need an index on the id column if it's PRIMARY KEY

'''
__docformat__ = 'restructuredtext'

from roundup.backends.rdbms_common import *
from roundup.backends import rdbms_common
import MySQLdb
import os, shutil
from MySQLdb.constants import ER


def db_nuke(config):
    """Clear all database contents and drop database itself"""
    if db_exists(config):
        conn = MySQLdb.connect(config.MYSQL_DBHOST, config.MYSQL_DBUSER,
            config.MYSQL_DBPASSWORD)
        try:
            conn.select_db(config.MYSQL_DBNAME)
        except:
            # no, it doesn't exist
            pass
        else:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            for table in tables:
                if __debug__:
                    print >>hyperdb.DEBUG, 'DROP TABLE %s'%table[0]
                cursor.execute("DROP TABLE %s"%table[0])
            if __debug__:
                print >>hyperdb.DEBUG, "DROP DATABASE %s"%config.MYSQL_DBNAME
            cursor.execute("DROP DATABASE %s"%config.MYSQL_DBNAME)
            conn.commit()
        conn.close()

    if os.path.exists(config.DATABASE):
        shutil.rmtree(config.DATABASE)

def db_create(config):
    """Create the database."""
    conn = MySQLdb.connect(config.MYSQL_DBHOST, config.MYSQL_DBUSER,
        config.MYSQL_DBPASSWORD)
    cursor = conn.cursor()
    if __debug__:
        print >>hyperdb.DEBUG, "CREATE DATABASE %s"%config.MYSQL_DBNAME
    cursor.execute("CREATE DATABASE %s"%config.MYSQL_DBNAME)
    conn.commit()
    conn.close()

def db_exists(config):
    """Check if database already exists."""
    conn = MySQLdb.connect(config.MYSQL_DBHOST, config.MYSQL_DBUSER,
        config.MYSQL_DBPASSWORD)
#    tables = None
    try:
        try:
            conn.select_db(config.MYSQL_DBNAME)
#            cursor = conn.cursor()
#            cursor.execute("SHOW TABLES")
#            tables = cursor.fetchall()
#            if __debug__:
#                print >>hyperdb.DEBUG, "tables %s"%(tables,)
        except MySQLdb.OperationalError:
            if __debug__:
                print >>hyperdb.DEBUG, "no database '%s'"%config.MYSQL_DBNAME
            return 0
    finally:
        conn.close()
    if __debug__:
        print >>hyperdb.DEBUG, "database '%s' exists"%config.MYSQL_DBNAME
    return 1


class Database(Database):
    arg = '%s'

    # Backend for MySQL to use.
    # InnoDB is faster, but if you're running <4.0.16 then you'll need to
    # use BDB to pass all unit tests.
    mysql_backend = 'InnoDB'
    #mysql_backend = 'BDB'

    hyperdb_to_sql_value = {
        hyperdb.String : str,
        # no fractional seconds for MySQL
        hyperdb.Date   : lambda x: x.formal(sep=' '),
        hyperdb.Link   : int,
        hyperdb.Interval  : lambda x: x.serialise(),
        hyperdb.Password  : str,
        hyperdb.Boolean   : int,
        hyperdb.Number    : lambda x: x,
    }

    def sql_open_connection(self):
        db = getattr(self.config, 'MYSQL_DATABASE')
        try:
            conn = MySQLdb.connect(*db)
        except MySQLdb.OperationalError, message:
            raise DatabaseError, message
        cursor = conn.cursor()
        cursor.execute("SET AUTOCOMMIT=0")
        cursor.execute("BEGIN")
        return (conn, cursor)
    
    def open_connection(self):
        # make sure the database actually exists
        if not db_exists(self.config):
            db_create(self.config)

        self.conn, self.cursor = self.sql_open_connection()

        try:
            self.load_dbschema()
        except MySQLdb.OperationalError, message:
            if message[0] != ER.NO_DB_ERROR:
                raise
        except MySQLdb.ProgrammingError, message:
            if message[0] != ER.NO_SUCH_TABLE:
                raise DatabaseError, message
            self.init_dbschema()
            self.sql("CREATE TABLE schema (schema TEXT) TYPE=%s"%
                self.mysql_backend)
            self.cursor.execute('''CREATE TABLE ids (name VARCHAR(255),
                num INTEGER) TYPE=%s'''%self.mysql_backend)
            self.cursor.execute('create index ids_name_idx on ids(name)')
            self.create_version_2_tables()

    def create_version_2_tables(self):
        # OTK store
        self.cursor.execute('''CREATE TABLE otks (otk_key VARCHAR(255),
            otk_value VARCHAR(255), otk_time FLOAT(20))
            TYPE=%s'''%self.mysql_backend)
        self.cursor.execute('CREATE INDEX otks_key_idx ON otks(otk_key)')

        # Sessions store
        self.cursor.execute('''CREATE TABLE sessions (
            session_key VARCHAR(255), session_time FLOAT(20),
            session_value VARCHAR(255)) TYPE=%s'''%self.mysql_backend)
        self.cursor.execute('''CREATE INDEX sessions_key_idx ON
            sessions(session_key)''')

        # full-text indexing store
        self.cursor.execute('''CREATE TABLE __textids (_class VARCHAR(255),
            _itemid VARCHAR(255), _prop VARCHAR(255), _textid INT)
            TYPE=%s'''%self.mysql_backend)
        self.cursor.execute('''CREATE TABLE __words (_word VARCHAR(30),
            _textid INT) TYPE=%s'''%self.mysql_backend)
        self.cursor.execute('CREATE INDEX words_word_ids ON __words(_word)')
        sql = 'insert into ids (name, num) values (%s,%s)'%(self.arg, self.arg)
        self.cursor.execute(sql, ('__textids', 1))

    def add_actor_column(self):
        ''' While we're adding the actor column, we need to update the
        tables to have the correct datatypes.'''
        assert 0, 'FINISH ME!'

        for spec in self.classes.values():
            new_has = spec.properties.has_key
            new_spec = spec.schema()
            new_spec[1].sort()
            old_spec[1].sort()
            if not force and new_spec == old_spec:
                # no changes
                return 0

            if __debug__:
                print >>hyperdb.DEBUG, 'update_class FIRING'

            # detect multilinks that have been removed, and drop their table
            old_has = {}
            for name,prop in old_spec[1]:
                old_has[name] = 1
                if new_has(name) or not isinstance(prop, hyperdb.Multilink):
                    continue
                # it's a multilink, and it's been removed - drop the old
                # table. First drop indexes.
                self.drop_multilink_table_indexes(spec.classname, ml)
                sql = 'drop table %s_%s'%(spec.classname, prop)
                if __debug__:
                    print >>hyperdb.DEBUG, 'update_class', (self, sql)
                self.cursor.execute(sql)
            old_has = old_has.has_key

            # now figure how we populate the new table
            if adding_actor:
                fetch = ['_activity', '_creation', '_creator']
            else:
                fetch = ['_actor', '_activity', '_creation', '_creator']
            properties = spec.getprops()
            for propname,x in new_spec[1]:
                prop = properties[propname]
                if isinstance(prop, hyperdb.Multilink):
                    if force or not old_has(propname):
                        # we need to create the new table
                        self.create_multilink_table(spec, propname)
                elif old_has(propname):
                    # we copy this col over from the old table
                    fetch.append('_'+propname)

            # select the data out of the old table
            fetch.append('id')
            fetch.append('__retired__')
            fetchcols = ','.join(fetch)
            cn = spec.classname
            sql = 'select %s from _%s'%(fetchcols, cn)
            if __debug__:
                print >>hyperdb.DEBUG, 'update_class', (self, sql)
            self.cursor.execute(sql)
            olddata = self.cursor.fetchall()

            # TODO: update all the other index dropping code
            self.drop_class_table_indexes(cn, old_spec[0])

            # drop the old table
            self.cursor.execute('drop table _%s'%cn)

            # create the new table
            self.create_class_table(spec)

            # do the insert of the old data - the new columns will have
            # NULL values
            args = ','.join([self.arg for x in fetch])
            sql = 'insert into _%s (%s) values (%s)'%(cn, fetchcols, args)
            if __debug__:
                print >>hyperdb.DEBUG, 'update_class', (self, sql, olddata[0])
            for entry in olddata:
                self.cursor.execute(sql, tuple(entry))

        return 1

    def __repr__(self):
        return '<myroundsql 0x%x>'%id(self)

    def sql_fetchone(self):
        return self.cursor.fetchone()

    def sql_fetchall(self):
        return self.cursor.fetchall()

    def sql_index_exists(self, table_name, index_name):
        self.cursor.execute('show index from %s'%table_name)
        for index in self.cursor.fetchall():
            if index[2] == index_name:
                return 1
        return 0

    def save_dbschema(self, schema):
        s = repr(self.database_schema)
        self.sql('INSERT INTO schema VALUES (%s)', (s,))
    
    def create_class_table(self, spec):
        cols, mls = self.determine_columns(spec.properties.items())

        # add on our special columns
        cols.append(('id', 'INTEGER PRIMARY KEY'))
        cols.append(('__retired__', 'INTEGER DEFAULT 0'))

        # create the base table
        scols = ','.join(['%s %s'%x for x in cols])
        sql = 'create table _%s (%s) type=%s'%(spec.classname, scols,
            self.mysql_backend)
        if __debug__:
            print >>hyperdb.DEBUG, 'create_class', (self, sql)
        self.cursor.execute(sql)

        self.create_class_table_indexes(spec)
        return cols, mls

    def drop_class_table_indexes(self, cn, key):
        # drop the old table indexes first
        l = ['_%s_id_idx'%cn, '_%s_retired_idx'%cn]
        if key:
            l.append('_%s_%s_idx'%(cn, key))

        table_name = '_%s'%cn
        for index_name in l:
            if not self.sql_index_exists(table_name, index_name):
                continue
            index_sql = 'drop index %s on %s'%(index_name, table_name)
            if __debug__:
                print >>hyperdb.DEBUG, 'drop_index', (self, index_sql)
            self.cursor.execute(index_sql)

    def create_journal_table(self, spec):
        # journal table
        cols = ','.join(['%s varchar'%x
            for x in 'nodeid date tag action params'.split()])
        sql = '''create table %s__journal (
            nodeid integer, date timestamp, tag varchar(255),
            action varchar(255), params varchar(255)) type=%s'''%(
            spec.classname, self.mysql_backend)
        if __debug__:
            print >>hyperdb.DEBUG, 'create_journal_table', (self, sql)
        self.cursor.execute(sql)
        self.create_journal_table_indexes(spec)

    def drop_journal_table_indexes(self, classname):
        index_name = '%s_journ_idx'%classname
        if not self.sql_index_exists('%s__journal'%classname, index_name):
            return
        index_sql = 'drop index %s on %s__journal'%(index_name, classname)
        if __debug__:
            print >>hyperdb.DEBUG, 'drop_index', (self, index_sql)
        self.cursor.execute(index_sql)

    def create_multilink_table(self, spec, ml):
        sql = '''CREATE TABLE `%s_%s` (linkid VARCHAR(255),
            nodeid VARCHAR(255)) TYPE=%s'''%(spec.classname, ml,
                self.mysql_backend)
        if __debug__:
          print >>hyperdb.DEBUG, 'create_class', (self, sql)
        self.cursor.execute(sql)
        self.create_multilink_table_indexes(spec, ml)

    def drop_multilink_table_indexes(self, classname, ml):
        l = [
            '%s_%s_l_idx'%(classname, ml),
            '%s_%s_n_idx'%(classname, ml)
        ]
        table_name = '%s_%s'%(classname, ml)
        for index_name in l:
            if not self.sql_index_exists(table_name, index_name):
                continue
            index_sql = 'drop index %s on %s'%(index_name, table_name)
            if __debug__:
                print >>hyperdb.DEBUG, 'drop_index', (self, index_sql)
            self.cursor.execute(index_sql)

    def drop_class_table_key_index(self, cn, key):
        table_name = '_%s'%cn
        index_name = '_%s_%s_idx'%(cn, key)
        if not self.sql_index_exists(table_name, index_name):
            return
        sql = 'drop index %s on %s'%(index_name, table_name)
        if __debug__:
            print >>hyperdb.DEBUG, 'drop_index', (self, sql)
        self.cursor.execute(sql)

    # old-skool id generation
    def newid(self, classname):
        ''' Generate a new id for the given class
        '''
        # get the next ID
        sql = 'select num from ids where name=%s'%self.arg
        if __debug__:
            print >>hyperdb.DEBUG, 'newid', (self, sql, classname)
        self.cursor.execute(sql, (classname, ))
        newid = int(self.cursor.fetchone()[0])

        # update the counter
        sql = 'update ids set num=%s where name=%s'%(self.arg, self.arg)
        vals = (int(newid)+1, classname)
        if __debug__:
            print >>hyperdb.DEBUG, 'newid', (self, sql, vals)
        self.cursor.execute(sql, vals)

        # return as string
        return str(newid)

    def setid(self, classname, setid):
        ''' Set the id counter: used during import of database

        We add one to make it behave like the seqeunces in postgres.
        '''
        sql = 'update ids set num=%s where name=%s'%(self.arg, self.arg)
        vals = (int(setid)+1, classname)
        if __debug__:
            print >>hyperdb.DEBUG, 'setid', (self, sql, vals)
        self.cursor.execute(sql, vals)

    def create_class(self, spec):
        rdbms_common.Database.create_class(self, spec)
        sql = 'insert into ids (name, num) values (%s, %s)'
        vals = (spec.classname, 1)
        if __debug__:
            print >>hyperdb.DEBUG, 'create_class', (self, sql, vals)
        self.cursor.execute(sql, vals)

class MysqlClass:
    # we're overriding this method for ONE missing bit of functionality.
    # look for "I can't believe it's not a toy RDBMS" below
    def filter(self, search_matches, filterspec, sort=(None,None),
            group=(None,None)):
        '''Return a list of the ids of the active nodes in this class that
        match the 'filter' spec, sorted by the group spec and then the
        sort spec

        "filterspec" is {propname: value(s)}

        "sort" and "group" are (dir, prop) where dir is '+', '-' or None
        and prop is a prop name or None

        "search_matches" is {nodeid: marker}

        The filter must match all properties specificed - but if the
        property value to match is a list, any one of the values in the
        list may match for that property to match.
        '''
        # just don't bother if the full-text search matched diddly
        if search_matches == {}:
            return []

        cn = self.classname

        timezone = self.db.getUserTimezone()
        
        # figure the WHERE clause from the filterspec
        props = self.getprops()
        frum = ['_'+cn]
        where = []
        args = []
        a = self.db.arg
        for k, v in filterspec.items():
            propclass = props[k]
            # now do other where clause stuff
            if isinstance(propclass, Multilink):
                tn = '%s_%s'%(cn, k)
                if v in ('-1', ['-1']):
                    # only match rows that have count(linkid)=0 in the
                    # corresponding multilink table)

                    # "I can't believe it's not a toy RDBMS"
                    # see, even toy RDBMSes like gadfly and sqlite can do
                    # sub-selects...
                    self.db.sql('select nodeid from %s'%tn)
                    s = ','.join([x[0] for x in self.db.sql_fetchall()])

                    where.append('id not in (%s)'%s)
                elif isinstance(v, type([])):
                    frum.append(tn)
                    s = ','.join([a for x in v])
                    where.append('id=%s.nodeid and %s.linkid in (%s)'%(tn,tn,s))
                    args = args + v
                else:
                    frum.append(tn)
                    where.append('id=%s.nodeid and %s.linkid=%s'%(tn, tn, a))
                    args.append(v)
            elif k == 'id':
                if isinstance(v, type([])):
                    s = ','.join([a for x in v])
                    where.append('%s in (%s)'%(k, s))
                    args = args + v
                else:
                    where.append('%s=%s'%(k, a))
                    args.append(v)
            elif isinstance(propclass, String):
                if not isinstance(v, type([])):
                    v = [v]

                # Quote the bits in the string that need it and then embed
                # in a "substring" search. Note - need to quote the '%' so
                # they make it through the python layer happily
                v = ['%%'+self.db.sql_stringquote(s)+'%%' for s in v]

                # now add to the where clause
                where.append(' or '.join(["_%s LIKE '%s'"%(k, s) for s in v]))
                # note: args are embedded in the query string now
            elif isinstance(propclass, Link):
                if isinstance(v, type([])):
                    if '-1' in v:
                        v = v[:]
                        v.remove('-1')
                        xtra = ' or _%s is NULL'%k
                    else:
                        xtra = ''
                    if v:
                        s = ','.join([a for x in v])
                        where.append('(_%s in (%s)%s)'%(k, s, xtra))
                        args = args + v
                    else:
                        where.append('_%s is NULL'%k)
                else:
                    if v == '-1':
                        v = None
                        where.append('_%s is NULL'%k)
                    else:
                        where.append('_%s=%s'%(k, a))
                        args.append(v)
            elif isinstance(propclass, Date):
                if isinstance(v, type([])):
                    s = ','.join([a for x in v])
                    where.append('_%s in (%s)'%(k, s))
                    args = args + [date.Date(x).serialise() for x in v]
                else:
                    try:
                        # Try to filter on range of dates
                        date_rng = Range(v, date.Date, offset=timezone)
                        if (date_rng.from_value):
                            where.append('_%s >= %s'%(k, a))                            
                            args.append(date_rng.from_value.serialise())
                        if (date_rng.to_value):
                            where.append('_%s <= %s'%(k, a))
                            args.append(date_rng.to_value.serialise())
                    except ValueError:
                        # If range creation fails - ignore that search parameter
                        pass                        
            elif isinstance(propclass, Interval):
                if isinstance(v, type([])):
                    s = ','.join([a for x in v])
                    where.append('_%s in (%s)'%(k, s))
                    args = args + [date.Interval(x).serialise() for x in v]
                else:
                    try:
                        # Try to filter on range of intervals
                        date_rng = Range(v, date.Interval)
                        if (date_rng.from_value):
                            where.append('_%s >= %s'%(k, a))
                            args.append(date_rng.from_value.serialise())
                        if (date_rng.to_value):
                            where.append('_%s <= %s'%(k, a))
                            args.append(date_rng.to_value.serialise())
                    except ValueError:
                        # If range creation fails - ignore that search parameter
                        pass                        
                    #where.append('_%s=%s'%(k, a))
                    #args.append(date.Interval(v).serialise())
            else:
                if isinstance(v, type([])):
                    s = ','.join([a for x in v])
                    where.append('_%s in (%s)'%(k, s))
                    args = args + v
                else:
                    where.append('_%s=%s'%(k, a))
                    args.append(v)

        # don't match retired nodes
        where.append('__retired__ <> 1')

        # add results of full text search
        if search_matches is not None:
            v = search_matches.keys()
            s = ','.join([a for x in v])
            where.append('id in (%s)'%s)
            args = args + v

        # "grouping" is just the first-order sorting in the SQL fetch
        # can modify it...)
        orderby = []
        ordercols = []
        if group[0] is not None and group[1] is not None:
            if group[0] != '-':
                orderby.append('_'+group[1])
                ordercols.append('_'+group[1])
            else:
                orderby.append('_'+group[1]+' desc')
                ordercols.append('_'+group[1])

        # now add in the sorting
        group = ''
        if sort[0] is not None and sort[1] is not None:
            direction, colname = sort
            if direction != '-':
                if colname == 'id':
                    orderby.append(colname)
                else:
                    orderby.append('_'+colname)
                    ordercols.append('_'+colname)
            else:
                if colname == 'id':
                    orderby.append(colname+' desc')
                    ordercols.append(colname)
                else:
                    orderby.append('_'+colname+' desc')
                    ordercols.append('_'+colname)

        # construct the SQL
        frum = ','.join(frum)
        if where:
            where = ' where ' + (' and '.join(where))
        else:
            where = ''
        cols = ['id']
        if orderby:
            cols = cols + ordercols
            order = ' order by %s'%(','.join(orderby))
        else:
            order = ''
        cols = ','.join(cols)
        sql = 'select %s from %s %s%s%s'%(cols, frum, where, group, order)
        args = tuple(args)
        if __debug__:
            print >>hyperdb.DEBUG, 'filter', (self, sql, args)
        self.db.cursor.execute(sql, args)
        l = self.db.cursor.fetchall()

        # return the IDs (the first column)
        # XXX numeric ids
        return [str(row[0]) for row in l]

class Class(MysqlClass, rdbms_common.Class):
    pass
class IssueClass(MysqlClass, rdbms_common.IssueClass):
    pass
class FileClass(MysqlClass, rdbms_common.FileClass):
    pass

#vim: set et
