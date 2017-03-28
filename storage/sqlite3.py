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
import queue
import threading
from _thread import start_new_thread

class Sqlite3Storage:

    def __init__(self, index_path, useWorkerThread=False):
        self._index_path = index_path
        self._insert_counter = 0
        self._is_transaction_active = False
        self._queue = queue.Queue()
        self._useWorkerThread = useWorkerThread
        self._lock = threading.Lock()

        if useWorkerThread:
            start_new_thread(self.__initWorker, (index_path, ))

        else:
            self.__initWorker(index_path)

    def __initWorker(self, index_path):
        self._connection = sqlite3.connect(index_path, check_same_thread = False)
        self._connection.text_factory = str
        self._cursor = self._connection.cursor()

        self._cursor.execute("PRAGMA main.synchronous = OFF")
        self._cursor.execute("PRAGMA main.count_changes = OFF")
        self._cursor.execute("PRAGMA main.journal_mode = MEMORY")
        self._cursor.execute("PRAGMA main.temp_store = MEMORY")
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        if self._cursor.rowcount < 5:
            self.__create_tables()

        if self._useWorkerThread:
            while True:
                queueItem = self._queue.get()
                if queueItem is None:
                    break
                statement, parameters, resultContainer = queueItem
                if parameters == None:
                    result = self._cursor.execute(statement)
                else:
                    result = self._cursor.execute(statement, parameters)
                resultCopy = []
                for row in result:
                    resultCopy.append(row)
                resultContainer.append([resultCopy, self._cursor.lastrowid])
                self._queue.task_done()

    def __query(self, statement, parameters=None):
        if self._useWorkerThread:
            query = self._queue
            resultContainer = []
            query.put([statement, parameters, resultContainer])
            query.join()
            return resultContainer.pop()

        else:
            resultCopy = []
            try:
                self._lock.acquire(True)
                if parameters == None:
                    result = self._cursor.execute(statement)
                else:
                    result = self._cursor.execute(statement, parameters)
                resultCopy = []
                for row in result:
                    resultCopy.append(row)
            finally:
                self._lock.release()
            return [resultCopy, self._cursor.lastrowid]

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
            "CREATE TABLE IF NOT EXISTS classes_trait_uses("
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
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        self.__query(
            "INSERT INTO files (file_path, namespace, mtime, hash) "
            "VALUES (?, ?, ?, ?)",
            (filePath, namespace, int(mtime), hashValue, )
        )
        self.__commitAfterXInserts()

    def gethash(self, filePath):
        hashResult = None
        result, lastrowid = self.__query("SELECT hash FROM files WHERE file_path = ?", (filePath, ))
        for hashValue, in result:
            hashResult = hashValue
        return hashResult

    def getmtime(self, filePath):
        mtimeResult = 0
        result, lastrowid = self.__query("SELECT mtime FROM files WHERE file_path = ?", (filePath, ))
        for mtime, in result:
            break
        return mtimeResult

    def get_all_files(self):
        resultPaths = []
        result, lastrowid = self.__query("SELECT file_path FROM files", ())
        for filePath, in result:
            resultPaths.append(filePath)
        return resultPaths

    ### CLASSES ###

    def add_class(self, filePath, namespace, className, classType, parentName, interfaces, traits, isFinal, isAbstract, docComment, line, column):
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        result, lastrowid = self.__query(
            "INSERT INTO classes (file_path, namespace, name, type, parent_name, is_final, is_abstract, doccomment, line, column) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (filePath, namespace, className, classType, parentName, isFinal, isAbstract, docComment, line, column, )
        )
        classId = lastrowid
        for interface in interfaces:
            self.__query(
                "INSERT INTO classes_interfaces_uses (class_id, name) "
                "VALUES (?, ?)",
                (classId, interface, )
            )
            self.__commitAfterXInserts()
        for trait in traits:
            self.__query(
                "INSERT INTO classes_trait_uses (class_id, name) "
                "VALUES (?, ?)",
                (classId, trait, )
            )
            self.__commitAfterXInserts()
        self.__commitAfterXInserts()

    def get_class_type(self, namespace, className):
        resultClassType = "class"
        if namespace[0] == '\\':
            namespace = namespace[1:]
        result, lastrowid = self.__query("SELECT name, type FROM classes WHERE namespace = ? AND name = ? LIMIT 1", (namespace, className))
        for className, classType in result:
            resultClassType = classType
        return resultClassType

    def get_class_position(self, namespace, className):
        file_path, line, column = (None, None, None, )
        while len(namespace) > 0 and namespace[0] == '\\':
            namespace = namespace[1:]
        result, lastrowid = self.__query(
            "SELECT file_path, line, column "
            "FROM classes "
            "WHERE namespace=? AND name=?",
            (namespace, className, )
        )
        for row in result:
            file_path, line, column = row
        return (file_path, line, column, )

    def get_class_id(self, namespace, className):
        classId, file_path = (None, None, )
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        result, lastrowid = self.__query(
            "SELECT id, file_path "
            "FROM classes "
            "WHERE namespace=? AND name=?",
            (namespace, className, )
        )
        for row in result:
            classId, file_path = row
        return (classId, file_path, )

    def get_class_parent(self, namespace, className):
        parentName = None
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        result, lastrowid = self.__query(
            "SELECT id, parent_name "
            "FROM classes "
            "WHERE namespace=? AND name=?",
            (namespace, className, )
        )
        for row in result:
            classId, parentName = row
        return parentName

    def get_class_children(self, className, includeInteraceImplementations=True):
        children = []
        if className[0] != '\\':
            className = '\\' + className
        result, lastrowid = self.__query(
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
            result, lastrowid = self.__query(
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
        interfaces = []
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
            "SELECT i.id, i.name "
            "FROM classes_interfaces_uses i "
            "WHERE i.class_id=?",
            (classId, )
        )
        for rowId, interfaceName in result:
            interfaces.append(interfaceName)
        return interfaces

    def get_class_traits(self, namespace, className, recursive=True):
        traits = []
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
            "SELECT t.id, t.name "
            "FROM classes_trait_uses t "
            "WHERE t.class_id=?",
            (classId, )
        )
        for rowId, traitName in result:
            traits.append(traitName)
            if recursive:
                pass # TODO
        return traits;

    def get_all_classnames(self, withNamespaces=True):
        classNames = []
        result, lastrowid = self.__query(
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
        result, lastrowid = self.__query(
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
        if name[0] != '\\':
            name = '\\' + name
        self.__query(
            "INSERT INTO classes_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_class_uses(self, name):
        if name[0] != '\\':
            name = '\\' + name
        result, lastrowid = self.__query(
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
        while len(className)>0 and className[0] == '\\':
            className = className[1:]
        result, lastrowid = self.__query(
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
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        self.__query(
            "INSERT INTO classes_constants (file_path, line, column, class_id, doccomment, name, value) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filePath, line, column, classId, docComment, name, value)
        )

    def get_class_constants(self, namespace, className):
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        self.__query(
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
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        self.__query(
            "INSERT INTO classes_methods (file_path, class_id, name, is_static, visibility, doccomment, line, column, arguments) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (filePath, classId, methodName, int(isStatic), visibility, docComment, line, column, repr(arguments))
        )
        self.__commitAfterXInserts()

    def get_class_methods(self, namespace, className, visibility="public"):
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        visibility, is_static, line, column, doccomment = (None, None, None, None, None, )
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
            "SELECT visibility, is_static, line, column, doccomment "
            "FROM classes_methods "
            "WHERE class_id=? and name=?",
            (classId, methodName, )
        )
        for row in result:
            visibility, is_static, line, column, doccomment = row
        return (visibility, is_static, filePath, line, column, doccomment, )

    def get_method_position(self, namespace, className, methodName):
        filePath, line, column = (None, None, None, )
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
            "SELECT line, column "
            "FROM classes_methods "
            "WHERE class_id=? AND name=?",
            (classId, methodName, )
        )
        for row in result:
            line, column = row
        return (filePath, line, column, )

    def get_method_doccomment(self, namespace, className, methodName):
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        self.__query(
            "INSERT INTO classes_method_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_method_uses(self, name):
        result, lastrowid = self.__query(
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
        classId, filePath = self.get_class_id(namespace, className)
        self.__query(
            "INSERT INTO classes_members (file_path, class_id, name, is_static, visibility, doccomment, line, column, type_hint) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (filePath, classId, memberName, isStatic, visibility, docComment, line, column, typeHint )
        )
        self.__commitAfterXInserts()

    def get_member(self, namespace, className, memberName):
        visibility, is_static, line, column, doccomment, typeHint = (None, None, None, None, None, None)
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
            "SELECT visibility, is_static, line, column, doccomment, type_hint "
            "FROM classes_members "
            "WHERE class_id=? and name=?",
            (classId, memberName, )
        )
        for row in result:
            visibility, is_static, line, column, doccomment, typeHint = row
        return (visibility, is_static, filePath, line, column, doccomment, typeHint)

    def get_class_members(self, namespace, className, visibility="public"):
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        line, column = (None, None, )
        classId, filePath = self.get_class_id(namespace, className)
        self.__query(
            "SELECT line, column "
            "FROM classes_members "
            "WHERE class_id=? AND name=?",
            (classId, memberName, )
        )
        for row in result:
            line, column = row
        return (filePath, line, column, )

    def get_member_doccomment(self, namespace, className, memberName):
        classId, filePath = self.get_class_id(namespace, className)
        result, lastrowid = self.__query(
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
        self.__query(
            "INSERT INTO classes_member_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_member_uses(self, name):
        result, lastrowid = self.__query(
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
        typeHint = namespace + "\\" + className
        members = []
        result, lastrowid = self.__query(
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
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        self.__query(
            "INSERT INTO functions (file_path, namespace, name, doccomment, line, column, arguments) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filePath, namespace, functionName, docComment, line, column, repr(arguments))
        )
        self.__commitAfterXInserts()

    def get_function(self, namespace, functionName):
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        file_path, line, column, doccomment = (None, None, None, None, )
        self.__query(
            "SELECT file_path, line, column, doccomment "
            "FROM functions "
            "WHERE namespace=? and name=?",
            (namespace, functionName, )
        )
        for row in result:
            file_path, line, column, doccomment = row
        return (file_path, line, column, doccomment, )

    def get_all_functions(self):
        result, lastrowid = self.__query(
            "SELECT namespace, name "
            "FROM functions "
        )
        functions = []
        for namespace, name in result:
            functions.append([namespace, name])
        return functions

    def get_function_position(self, namespace, functionName):
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        file_path, line, column = (None, None, None, )
        result, lastrowid = self.__query(
            "SELECT file_path, line, column "
            "FROM functions "
            "WHERE namespace=? AND name=?",
            (namespace, functionName, )
        )
        for row in result:
            file_path, line, column = row
        return (file_path, line, column, )

    def get_function_doccomment(self, namespace, functionName):
        result, lastrowid = self.__query(
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
        result, lastrowid = self.__query(
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
        self.__query(
            "INSERT INTO function_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_function_uses(self, name):
        result, lastrowid = self.__query(
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
        self.__query(
            "INSERT INTO constants (file_path, name, line, column) "
            "VALUES (?, ?, ?, ?)",
            (filePath, constantName, line, column, )
        )
        self.__commitAfterXInserts()

    def get_constant_position(self, constantName):
        file_path, line, column = (None, None, None, )
        self.__query(
            "SELECT file_path, line, column "
            "FROM constants "
            "WHERE name=?",
            (constantName, )
        )
        for row in result:
            file_path, line, column = row
        return (file_path, line, column, )

    def get_all_constants(self):
        result, lastrowid = self.__query(
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
        self.__query(
            "INSERT INTO constant_uses (name, file_path, line, column, className, functionName) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filePath, line, column, className, functionName)
        )

    def get_constant_uses(self, name):
        result, lastrowid = self.__query(
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
            for path, line, column, title in self.__query(sqlStatement)[0]:
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
        result, lastrowid = self.__query("SELECT id FROM classes WHERE file_path = ?", (filePath, ))
        for classId, in result:
            self.__query("DELETE FROM classes_methods         WHERE class_id = ?", (classId, ))
            self.__query("DELETE FROM classes_members         WHERE class_id = ?", (classId, ))
            self.__query("DELETE FROM classes_interfaces_uses WHERE class_id = ?", (classId, ))
            self.__query("DELETE FROM classes_trait_uses      WHERE class_id = ?", (classId, ))
            self.__query("DELETE FROM classes_constants       WHERE class_id = ?", (classId, ))
        self.__query("DELETE FROM classes                 WHERE file_path = ?", (filePath, ))
        self.__query("DELETE FROM functions               WHERE file_path = ?", (filePath, ))
        self.__query("DELETE FROM files                   WHERE file_path = ?", (filePath, ))
        self.__query("DELETE FROM classes_member_uses     WHERE file_path = ?", (filePath, ))
        self.__query("DELETE FROM classes_method_uses     WHERE file_path = ?", (filePath, ))
        self.__query("DELETE FROM classes_uses            WHERE file_path = ?", (filePath, ))
        self.__query("DELETE FROM function_uses           WHERE file_path = ?", (filePath, ))
        #self.__query("VACUUM")
        self.__commitAfterXInserts()

    def empty(self):
        self.__query("DROP TABLE IF EXISTS classes_members")
        self.__query("DROP TABLE IF EXISTS classes_member_uses")
        self.__query("DROP TABLE IF EXISTS classes_methods")
        self.__query("DROP TABLE IF EXISTS classes_method_uses")
        self.__query("DROP TABLE IF EXISTS classes_interfaces_uses")
        self.__query("DROP TABLE IF EXISTS classes_trait_uses")
        self.__query("DROP TABLE IF EXISTS classes_namespace_name")
        self.__query("DROP TABLE IF EXISTS classes_constants")
        self.__query("DROP TABLE IF EXISTS constants")
        self.__query("DROP TABLE IF EXISTS classes")
        self.__query("DROP TABLE IF EXISTS classes_uses")
        self.__query("DROP TABLE IF EXISTS functions")
        self.__query("DROP TABLE IF EXISTS function_uses")
        self.__query("DROP TABLE IF EXISTS files")
        self.__query("VACUUM")
        self.__create_tables()
        self._connection.commit()
