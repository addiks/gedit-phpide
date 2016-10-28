# Copyright (C) 2015 Gerrit Addiks <gerrit@addiks.net>
# https://github.com/addiks/gedit-phpide
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sqlite3

class Sqlite3Storage:

    def __init__(self, index_path):
        self._index_path = index_path
        self._connection = sqlite3.connect(index_path)
        self._connection.text_factory = str
        self._cursor = self._connection.cursor()
        self._insert_counter = 0
        self._is_transaction_active = False

        self._cursor.execute("PRAGMA main.synchronous = OFF")
        self._cursor.execute("PRAGMA main.count_changes = OFF")
        self._cursor.execute("PRAGMA main.journal_mode = MEMORY")
        self._cursor.execute("PRAGMA main.temp_store = MEMORY")
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        if self._cursor.rowcount < 5:
            self.__create_tables()

    def __create_tables(self):
        cursor = self._cursor
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS files("
                "file_path VARCHAR(512) PRIMARY KEY, "
                "namespace VARCHAR(256) NOT NULL DEFAULT '\\', "
                "mtime     INTEGER, "
                "hash      VARCHAR(128) "
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path   VARCHAR(512) NOT NULL, "
                "namespace   VARCHAR(256) NOT NULL DEFAULT '\\', "
                "name        VARCHAR(128) NOT NULL, "
                "type        VARCHAR(32)  NOT NULL, "
                "parent_name VARCHAR(128), "
                "is_final    TINYINT, "
                "is_abstract TINYINT, "
                "doccomment  SMALLTEXT, "
                "line        INTEGER, "
                "column      SMALLINT"
            ")"
        );
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS classes_namespace_name ON classes (namespace, name)"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes_interfaces_uses("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "class_id    INTEGER NOT NULL, "
                "name        VARCHAR(128)"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes_constants("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path   VARCHAR(512) NOT NULL, "
                "class_id    INTEGER NOT NULL, "
                "name        VARCHAR(128), "
                "value       VARCHAR(2048), "
                "doccomment  SMALLTEXT, "
                "line        INTEGER, "
                "column      SMALLINT"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes_methods("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "class_id    INTEGER NOT NULL, "
                "name        VARCHAR(128), "
                "is_static   TINYINT, "
                "visibility  VARCHAR(32), "
                "doccomment  SMALLTEXT, "
                "file_path   VARCHAR(512) NOT NULL, "
                "line        INTEGER, "
                "column      SMALLINT, "
                "arguments   SMALLTEXT "
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes_members("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "class_id    INTEGER NOT NULL, "
                "name        VARCHAR(128), "
                "is_static   TINYINT, "
                "visibility  VARCHAR(32), "
                "doccomment  SMALLTEXT, "
                "type_hint   VARCHAR(512), "
                "file_path   VARCHAR(512) NOT NULL, "
                "line        INTEGER, "
                "column      SMALLINT"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS functions("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path   VARCHAR(512) NOT NULL, "
                "namespace   VARCHAR(256) NOT NULL DEFAULT '\\', "
                "name        VARCHAR(128), "
                "doccomment  SMALLTEXT, "
                "line        INTEGER, "
                "column      SMALLINT, "
                "arguments   SMALLTEXT "
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS constants("
                "id           INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path    VARCHAR(512) NOT NULL, "
                "name         VARCHAR(128), "
                "line         INTEGER, "
                "column       SMALLINT"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes_method_uses("
                "id           INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path    VARCHAR(512) NOT NULL, "
                "name         VARCHAR(128), "
                "line         INTEGER, "
                "column       SMALLINT, "
                "className    VARCHAR(128), "
                "functionName VARCHAR(128)"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes_member_uses("
                "id           INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path    VARCHAR(512) NOT NULL, "
                "name         VARCHAR(128), "
                "line         INTEGER, "
                "column       SMALLINT, "
                "className    VARCHAR(128), "
                "functionName VARCHAR(128)"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS function_uses("
                "id           INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path    VARCHAR(512) NOT NULL, "
                "name         VARCHAR(128), "
                "line         INTEGER, "
                "column       SMALLINT, "
                "className    VARCHAR(128), "
                "functionName VARCHAR(128)"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes_uses("
                "id           INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path    VARCHAR(512) NOT NULL, "
                "name         VARCHAR(128), "
                "line         INTEGER, "
                "column       SMALLINT, "
                "className    VARCHAR(128), "
                "functionName VARCHAR(128)"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS constant_uses("
                "id           INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path    VARCHAR(512) NOT NULL, "
                "name         VARCHAR(128), "
                "line         INTEGER, "
                "column       SMALLINT, "
                "className    VARCHAR(128), "
                "functionName VARCHAR(128)"
            ")"
        );
        #self._connection.commit()

    ### FILES

    def add_file(self, filePath, namespace, mtime, hashValue):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        cursor.execute(
            "INSERT INTO files (file_path, namespace, mtime, hash) "
            "VALUES (?, ?, ?, ?)",
            (filePath, namespace, int(mtime), hashValue, )
        )
        self.__commitAfterXInserts()

    def gethash(self, filePath):
        cursor = self._cursor
        hashResult = None
        result = cursor.execute("SELECT hash FROM files WHERE file_path = ?", (filePath, ))
        for hashValue, in result:
            hashResult = hashValue
        return hashResult

    def getmtime(self, filePath):
        cursor = self._cursor
        mtimeResult = 0
        result = cursor.execute("SELECT mtime FROM files WHERE file_path = ?", (filePath, ))
        for mtime, in result:
            break
        return mtimeResult

    def get_all_files(self):
        cursor = self._cursor
        resultPaths = []
        result = cursor.execute("SELECT file_path FROM files", ())
        for filePath, in result:
            resultPaths.append(filePath)
        return resultPaths

    ### CLASSES ###

    def add_class(self, filePath, namespace, className, classType, parentName, interfaces, isFinal, isAbstract, docComment, line, column):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        cursor.execute(
            "INSERT INTO classes (file_path, namespace, name, type, parent_name, is_final, is_abstract, doccomment, line, column) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (filePath, namespace, className, classType, parentName, isFinal, isAbstract, docComment, line, column, )
        )
        classId = cursor.lastrowid
        for interface in interfaces:
            cursor.execute(
                "INSERT INTO classes_interfaces_uses (class_id, name) "
                "VALUES (?, ?)",
                (classId, interface, )
            )
            self.__commitAfterXInserts()
        self.__commitAfterXInserts()

    def get_class_type(self, namespace, className):
        cursor = self._cursor
        resultClassType = "class"
        if namespace[0] == '\\':
            namespace = namespace[1:]
        result = cursor.execute("SELECT name, type FROM classes WHERE namespace = ? AND name = ? LIMIT 1", (namespace, className))
        for className, classType in result:
            resultClassType = classType
        return resultClassType

    def get_class_position(self, namespace, className):
        cursor = self._cursor
        file_path, line, column = (None, None, None, )
        while len(namespace) > 0 and namespace[0] == '\\':
            namespace = namespace[1:]
        cursor.execute(
            "SELECT file_path, line, column "
            "FROM classes "
            "WHERE namespace=? AND name=?",
            (namespace, className, )
        )
        row = cursor.fetchone()
        if row != None:
            file_path, line, column = row
        return (file_path, line, column, )

    def get_class_id(self, namespace, className):
        cursor = self._cursor
        classId, file_path = (None, None, )
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        result = cursor.execute(
            "SELECT id, file_path "
            "FROM classes "
            "WHERE namespace=? AND name=?",
            (namespace, className, )
        )
        row = cursor.fetchone()
        if row != None:
            classId, file_path = row
        return (classId, file_path, )

    def get_class_parent(self, namespace, className):
        cursor = self._cursor
        parentName = None
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        cursor.execute(
            "SELECT id, parent_name "
            "FROM classes "
            "WHERE namespace=? AND name=?",
            (namespace, className, )
        )
        row = cursor.fetchone()
        if row != None:
            classId, parentName = row
        return parentName

    def get_class_children(self, className, includeInteraceImplementations=True):
        cursor = self._cursor
        children = []
        if className[0] != '\\':
            className = '\\' + className
        result = cursor.execute(
            "SELECT namespace, name "
            "FROM classes "
            "WHERE parent_name=?",
            (className, )
        )
        for namespace, name in result:
            if namespace[-1:] != '\\':
                namespace += "\\"
            children.append(namespace + name)
        if includeInteraceImplementations:
            result = cursor.execute(
                "SELECT c.namespace, c.name "
                "FROM classes_interfaces_uses i "
                "LEFT JOIN classes c ON(i.class_id = c.id) "
                "WHERE i.name=?",
                (className, )
            )
            for namespace, name in result:
                if namespace[-1:] != '\\':
                    namespace += "\\"
                children.append(namespace + name)
        return children

    def get_class_interfaces(self, namespace, className):
        cursor = self._cursor
        interfaces = []
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT i.id, i.name "
            "FROM classes_interfaces_uses i "
            "WHERE i.class_id=?",
            (classId, )
        )
        for rowId, interfaceName in result:
            interfaces.append(interfaceName)
        return interfaces

    def get_all_classnames(self, withNamespaces=True):
        cursor = self._cursor
        classNames = []
        result = cursor.execute(
            "SELECT namespace, name "
            "FROM classes ",
            ()
        )
        for namespace, name in result:
            className = name
            if withNamespaces:
                className = namespace + "\\" + name
            classNames.append(className)
        return classNames

    def get_class_doccomment(self, namespace, className):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT id, doccomment "
            "FROM classes "
            "WHERE namespace = ? AND name = ?",
            (namespace, className)
        )
        resultDocComment = None
        for class_id, docComment in result:
            resultDocComment = docComment
            break
        return resultDocComment

    def add_class_use(self, name, filePath, line, column, className, functionName):
        cursor = self._cursor
        if name[0] != '\\':
            name = '\\' + name
        cursor.execute(
            "INSERT INTO classes_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_class_uses(self, name):
        cursor = self._cursor
        if name[0] != '\\':
            name = '\\' + name
        result = cursor.execute(
            "SELECT file_path, line, column, className, functionName "
            "FROM classes_uses "
            "WHERE name = ? "
            "ORDER BY className, line, functionName DESC",
            (name, )
        )
        uses = []
        for file_path, line, column, className, functionName in result:
            uses.append([file_path, line, column, className, functionName])
        return uses

    def get_class_uses_by_class(self, className):
        cursor = self._cursor
        while len(className)>0 and className[0] == '\\':
            className = className[1:]
        result = cursor.execute(
            "SELECT file_path, line, column, name, functionName "
            "FROM classes_uses "
            "WHERE className = ? "
            "ORDER BY className, line, functionName DESC",
            (className, )
        )
        uses = []
        for file_path, line, column, name, functionName in result:
            uses.append([file_path, line, column, name, functionName])
        return uses

    ### CLASS-CONSTANT ###

    def add_class_constant(self, filePath, namespace, className, name, value, docComment, line, column):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "INSERT INTO classes_constants (file_path, line, column, class_id, doccomment, name, value) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filePath, line, column, classId, docComment, name, value)
        )

    def get_class_constants(self, namespace, className):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT name "
            "FROM classes_constants "
            "WHERE class_id=?",
            (classId, )
        )
        constNames = []
        for name, in result:
            constNames.append(name)
        return constNames

    def get_class_const_position(self, namespace, className, constantName):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "SELECT line, column "
            "FROM classes_constants "
            "WHERE class_id=? AND name=?",
            (classId, constantName, )
        )
        row = cursor.fetchone()
        if row != None:
            line, column = row
        return (filePath, line, column, )

    def get_class_constant_doccomment(self, namespace, className, constantName):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT id, doccomment "
            "FROM classes_constants "
            "WHERE class_id = ? AND name = ?",
            (classId, constantName)
        )
        resultDocComment = None
        for class_id, docComment in result:
            resultDocComment = docComment
            break
        return resultDocComment

    ### METHODS ###

    def add_method(self, filePath, namespace, className, methodName, isStatic, visibility, docComment, line, column, arguments):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "INSERT INTO classes_methods (file_path, class_id, name, is_static, visibility, doccomment, line, column, arguments) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (filePath, classId, methodName, int(isStatic), visibility, docComment, line, column, repr(arguments))
        )
        self.__commitAfterXInserts()

    def get_class_methods(self, namespace, className, visibility="public"):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT name "
            "FROM classes_methods "
            "WHERE class_id=? and visibility=? and is_static=0",
            (classId, visibility, )
        )
        methodNames = []
        for name, in result:
            methodNames.append(name)
        return methodNames

    def get_all_class_methods(self, namespace, className):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT name "
            "FROM classes_methods "
            "WHERE class_id=? and is_static=0",
            (classId, )
        )
        methodNames = []
        for name, in result:
            methodNames.append(name)
        return methodNames

    def get_static_class_methods(self, namespace, className, visibility="public"):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT name "
            "FROM classes_methods "
            "WHERE class_id=? and visibility=? and is_static=1",
            (classId, visibility, )
        )
        methodNames = []
        for name, in result:
            methodNames.append(name)
        return methodNames

    def get_method(self, namespace, className, methodName):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        visibility, is_static, line, column, doccomment = (None, None, None, None, None, )
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "SELECT visibility, is_static, line, column, doccomment "
            "FROM classes_methods "
            "WHERE class_id=? and name=?",
            (classId, methodName, )
        )
        row = cursor.fetchone()
        if row != None:
            visibility, is_static, line, column, doccomment = row
        return (visibility, is_static, filePath, line, column, doccomment, )

    def get_method_position(self, namespace, className, methodName):
        filePath, line, column = (None, None, None, )
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "SELECT line, column "
            "FROM classes_methods "
            "WHERE class_id=? AND name=?",
            (classId, methodName, )
        )
        row = cursor.fetchone()
        if row != None:
            line, column = row
        return (filePath, line, column, )

    def get_method_doccomment(self, namespace, className, methodName):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT id, doccomment "
            "FROM classes_methods "
            "WHERE class_id = ? AND name = ?",
            (classId, methodName)
        )
        resultDocComment = None
        for class_id, docComment in result:
            resultDocComment = docComment
            break
        return resultDocComment

    def get_method_arguments(self, namespace, className, methodName):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT id, arguments "
            "FROM classes_methods "
            "WHERE class_id = ? AND name = ?",
            (classId, methodName)
        )
        resultArguments = None
        for class_id, arguments in result:
            resultArguments = eval(arguments)
            break
        return resultArguments

    def add_method_use(self, name, filePath, line, column, className, functionName):
        cursor = self._cursor
        cursor.execute(
            "INSERT INTO classes_method_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_method_uses(self, name):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT file_path, line, column, className, functionName "
            "FROM classes_method_uses "
            "WHERE name = ? "
            "ORDER BY className, line, functionName DESC",
            (name, )
        )
        uses = []
        for file_path, line, column, className, functionName in result:
            uses.append([file_path, line, column, className, functionName])
        return uses

    ### MEMBERS ###

    def add_member(self, filePath, namespace, className, memberName, line, column, isStatic, visibility, docComment, typeHint=None):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "INSERT INTO classes_members (file_path, class_id, name, is_static, visibility, doccomment, line, column, type_hint) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (filePath, classId, memberName, isStatic, visibility, docComment, line, column, typeHint )
        )
        self.__commitAfterXInserts()

    def get_member(self, namespace, className, memberName):
        cursor = self._cursor
        visibility, is_static, line, column, doccomment, typeHint = (None, None, None, None, None, None)
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "SELECT visibility, is_static, line, column, doccomment, type_hint "
            "FROM classes_members "
            "WHERE class_id=? and name=?",
            (classId, memberName, )
        )
        row = cursor.fetchone()
        if row != None:
            visibility, is_static, line, column, doccomment, typeHint = row
        return (visibility, is_static, filePath, line, column, doccomment, typeHint)

    def get_class_members(self, namespace, className, visibility="public"):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT name "
            "FROM classes_members "
            "WHERE class_id=? and visibility=? and is_static=0",
            (classId, visibility, )
        )
        classMembers = []
        for name, in result:
            classMembers.append(name)
        return classMembers

    def get_all_class_members(self, namespace, className):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT name "
            "FROM classes_members "
            "WHERE class_id=? and is_static=0",
            (classId, )
        )
        classMembers = []
        for name, in result:
            classMembers.append(name)
        return classMembers

    def get_static_class_members(self, namespace, className, visibility="public"):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT name "
            "FROM classes_members "
            "WHERE class_id=? and visibility=? and is_static=1",
            (classId, visibility, )
        )
        classMembers = []
        for name, in result:
            classMembers.append(name)
        return classMembers

    def get_member_position(self, namespace, className, memberName):
        cursor = self._cursor
        line, column = (None, None, )
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "SELECT line, column "
            "FROM classes_members "
            "WHERE class_id=? AND name=?",
            (classId, memberName, )
        )
        row = cursor.fetchone()
        if row != None:
            line, column = row
        return (filePath, line, column, )

    def get_member_doccomment(self, namespace, className, memberName):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        result = cursor.execute(
            "SELECT id, doccomment "
            "FROM classes_members "
            "WHERE class_id = ? AND name = ?",
            (classId, memberName)
        )
        resultDocComment = None
        for class_id, docComment in result:
            resultDocComment = docComment
            break
        return resultDocComment

    def add_member_use(self, name, filePath, line, column, className, functionName):
        cursor = self._cursor
        cursor.execute(
            "INSERT INTO classes_member_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_member_uses(self, name):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT file_path, line, column, className, functionName "
            "FROM classes_member_uses "
            "WHERE name = ? "
            "ORDER BY className, line, functionName DESC",
            (name, )
        )
        uses = []
        for file_path, line, column, className, functionName in result:
            uses.append([file_path, line, column, className, functionName])
        return uses

    def get_members_by_type_hint(self, namespace, className):
        cursor = self._cursor
        typeHint = namespace + "\\" + className
        members = []
        result = cursor.execute(
            "SELECT c.namespace, c.name, cm.name "
            "FROM classes_members cm "
            "LEFT JOIN classes c ON(cm.class_id = c.id)"
            "WHERE cm.type_hint = ?",
            (typeHint, )
        )
        for namespace, className, memberName in result:
            members.append([namespace, className, memberName])
        return members

    ### FUNCTIONS ###

    def add_function(self, filePath, namespace, functionName, docComment, line, column, arguments):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        cursor.execute(
            "INSERT INTO functions (file_path, namespace, name, doccomment, line, column, arguments) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filePath, namespace, functionName, docComment, line, column, repr(arguments))
        )
        self.__commitAfterXInserts()

    def get_function(self, namespace, functionName):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        file_path, line, column, doccomment = (None, None, None, None, )
        cursor.execute(
            "SELECT file_path, line, column, doccomment "
            "FROM functions "
            "WHERE namespace=? and name=?",
            (namespace, functionName, )
        )
        row = cursor.fetchone()
        if row != None:
            file_path, line, column, doccomment = row
        return (file_path, line, column, doccomment, )

    def get_all_functions(self):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT namespace, name "
            "FROM functions "
        )
        functions = []
        for namespace, name in result:
            functions.append([namespace, name])
        return functions

    def get_function_position(self, namespace, functionName):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        file_path, line, column = (None, None, None, )
        cursor.execute(
            "SELECT file_path, line, column "
            "FROM functions "
            "WHERE namespace=? AND name=?",
            (namespace, functionName, )
        )
        row = cursor.fetchone()
        if row != None:
            file_path, line, column = row
        return (file_path, line, column, )

    def get_function_doccomment(self, namespace, functionName):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT id, doccomment "
            "FROM functions "
            "WHERE namespace = ? AND name = ?",
            (namespace, functionName)
        )
        resultDocComment = None
        for class_id, docComment in result:
            resultDocComment = docComment
            break
        return resultDocComment

    def get_function_arguments(self, namespace, functionName):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT id, arguments "
            "FROM functions "
            "WHERE namespace = ? AND name = ?",
            (namespace, functionName)
        )
        resultArguments = None
        for class_id, arguments in result:
            resultArguments = eval(arguments)
            break
        return resultArguments

    def add_function_use(self, name, filePath, line, column, className, functionName):
        cursor = self._cursor
        cursor.execute(
            "INSERT INTO function_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_function_uses(self, name):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT file_path, line, column, className, functionName "
            "FROM function_uses "
            "WHERE name = ? "
            "ORDER BY className, line, functionName DESC",
            (name, )
        )
        uses = []
        for file_path, line, column, className, functionName in result:
            uses.append([file_path, line, column, className, functionName])
        return uses

    ### CONSTANTS ###

    def add_constant(self, filePath, constantName, line, column):
        cursor = self._cursor
        cursor.execute(
            "INSERT INTO constants (file_path, name, line, column) "
            "VALUES (?, ?, ?, ?)",
            (filePath, constantName, line, column, )
        )
        self.__commitAfterXInserts()

    def get_constant_position(self, constantName):
        cursor = self._cursor
        file_path, line, column = (None, None, None, )
        cursor.execute(
            "SELECT file_path, line, column "
            "FROM constants "
            "WHERE name=?",
            (constantName, )
        )
        row = cursor.fetchone()
        if row != None:
            file_path, line, column = row
        return (file_path, line, column, )

    def get_all_constants(self):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT name "
            "FROM constants "
        )
        constants = []
        for name, in result:
            constants.append(name)
        return constants

    def get_constant_doccomment(self, constantName):
        return ''; # no doccomment in db yet

    def add_constant_use(self, name, filePath, line, column, className, functionName):
        cursor = self._cursor
        cursor.execute(
            "INSERT INTO constant_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_constant_uses(self, name):
        cursor = self._cursor
        result = cursor.execute(
            "SELECT file_path, line, column, className, functionName "
            "FROM constant_uses "
            "WHERE name = ? "
            "ORDER BY className, line, functionName DESC",
            (name, )
        )
        uses = []
        for file_path, line, column, className, functionName in result:
            uses.append([file_path, line, column, className, functionName])
        return uses

    ### FULLTEXT SEARCH ###

    def do_fulltext_search(self, searchTerms):
        cursor = self._cursor

        # searchResults: [[filePath, line, column, title], ... ]
        searchResults = []

        typeDefs = [
            {   'typeName':      'File',
                'table':         'files',
                'searchColumns': ['file_path', "'file'"],
                'selectPart':    "files.file_path, 1, 1, files.file_path",
            },
            {   'typeName':      'Class',
                'table':         'classes',
                'searchColumns': ['namespace', 'name', "'class'"],
                'selectPart':    "file_path, line, column, namespace || '\\' || name",
            },
            {   'typeName':      'Class-Constant',
                'table':         'classes_constants',
                'searchColumns': ['name', 'value', "'class'", "'constant'"],
                'selectPart':    "file_path, line, column, (SELECT namespace || '\\' || name from classes WHERE class_id == id) || '::' || name",
            },
            {   'typeName':      'Method',
                'table':         'classes_methods',
                'searchColumns': ['name', "'method'"],
                'selectPart':    "file_path, line, column, (SELECT namespace || '\\' || name from classes WHERE class_id == id) || '->' || name || '()'",
            },
            {   'typeName':      'Member',
                'table':         'classes_members',
                'searchColumns': ['name', "'member'"],
                'selectPart':    "file_path, line, column, (SELECT namespace || '\\' || name from classes WHERE class_id == id) || '->' || name",
            },
            {   'typeName':      'Function',
                'table':         'functions',
                'searchColumns': ['name', "'function'"],
                'selectPart':    "file_path, line, column, name",
            },
            {   'typeName':      'Constant',
                'table':         'constants',
                'searchColumns': ['name', "'constant'"],
                'selectPart':    "file_path, line, column, name",
            }
        ]

        for typeDef in typeDefs:
            tableName  = typeDef['table']
            columns    = typeDef['searchColumns']
            selectPart = typeDef['selectPart']
            typeName   = typeDef['typeName']

            sqlConditions = []
            for searchTerm in searchTerms:
                sqlTermConditions = []
                for columnName in columns:
                    if columnName[0] != "'":
                        columnName = tableName+"."+columnName
                    sqlTermConditions.append(columnName+" LIKE '%"+str(searchTerm)+"%'")
                sqlConditions.append("(" + " OR ".join(sqlTermConditions) + ")")

            sqlStatement = "SELECT "+selectPart+" FROM "+tableName+" WHERE "+ " AND ".join(sqlConditions)
            for path, line, column, title in cursor.execute(sqlStatement):
                titleLength = 0
                if title is str:
                    titleLength = len(title)
                searchResults.append([path, line, column, typeName, title])

        return searchResults

    ### HELPERS ###

    def __commitAfterXInserts(self):
        self._insert_counter+=1
        if self._insert_counter >= 3000:
            self._insert_counter = 0
#            self._connection.commit()

    def begin(self):
        pass

    def sync(self):
        self._connection.commit()

    def removeFile(self, filePath):
        cursor = self._cursor
        result = cursor.execute("SELECT id FROM classes WHERE file_path = ?", (filePath, ))
        for classId, in result:
            cursor.execute("DELETE FROM classes_methods         WHERE class_id = ?", (classId, ))
            cursor.execute("DELETE FROM classes_members         WHERE class_id = ?", (classId, ))
            cursor.execute("DELETE FROM classes_interfaces_uses WHERE class_id = ?", (classId, ))
            cursor.execute("DELETE FROM classes_constants       WHERE class_id = ?", (classId, ))
        cursor.execute("DELETE FROM classes                 WHERE file_path = ?", (filePath, ))
        cursor.execute("DELETE FROM functions               WHERE file_path = ?", (filePath, ))
        cursor.execute("DELETE FROM files                   WHERE file_path = ?", (filePath, ))
        cursor.execute("DELETE FROM classes_member_uses     WHERE file_path = ?", (filePath, ))
        cursor.execute("DELETE FROM classes_method_uses     WHERE file_path = ?", (filePath, ))
        cursor.execute("DELETE FROM classes_uses            WHERE file_path = ?", (filePath, ))
        cursor.execute("DELETE FROM function_uses           WHERE file_path = ?", (filePath, ))
        #cursor.execute("VACUUM")
        self.__commitAfterXInserts()

    def empty(self):
        cursor = self._cursor
        cursor.execute("DROP TABLE IF EXISTS classes_members")
        cursor.execute("DROP TABLE IF EXISTS classes_member_uses")
        cursor.execute("DROP TABLE IF EXISTS classes_methods")
        cursor.execute("DROP TABLE IF EXISTS classes_method_uses")
        cursor.execute("DROP TABLE IF EXISTS classes_interfaces_uses")
        cursor.execute("DROP TABLE IF EXISTS classes_namespace_name")
        cursor.execute("DROP TABLE IF EXISTS classes_constants")
        cursor.execute("DROP TABLE IF EXISTS constants")
        cursor.execute("DROP TABLE IF EXISTS classes")
        cursor.execute("DROP TABLE IF EXISTS classes_uses")
        cursor.execute("DROP TABLE IF EXISTS functions")
        cursor.execute("DROP TABLE IF EXISTS function_uses")
        cursor.execute("DROP TABLE IF EXISTS files")
        cursor.execute("VACUUM")
        self.__create_tables()
        self._connection.commit()
