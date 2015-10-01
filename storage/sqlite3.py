
import sqlite3

class Sqlite3Storage:
    
    def __init__(self, index_path):
        self._index_path = index_path
        self._connection = sqlite3.connect(index_path)
        self._connection.text_factory = str
        self._cursor = self._connection.cursor()
        self._insert_counter = 0

        self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        if self._cursor.rowcount < 5:
            self.__create_tables()

    def __create_tables(self):
        cursor = self._cursor
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS files("
                "file_path VARCHAR(256) PRIMARY KEY, "
                "namespace VARCHAR(256) NOT NULL DEFAULT '\\', "
                "mtime     INTEGER, "
                "hash      VARCHAR(128) "
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path   VARCHAR(256) NOT NULL, "
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
            "CREATE TABLE IF NOT EXISTS classes_interfaces_uses("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "class_id    INTEGER NOT NULL, "
                "name        VARCHAR(128)"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS classes_constants("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path   VARCHAR(256) NOT NULL, "
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
                "file_path   VARCHAR(256) NOT NULL, "
                "line        INTEGER, "
                "column      SMALLINT"
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
                "file_path   VARCHAR(256) NOT NULL, "
                "line        INTEGER, "
                "column      SMALLINT"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS functions("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path   VARCHAR(256) NOT NULL, "
                "namespace   VARCHAR(256) NOT NULL DEFAULT '\\', "
                "name        VARCHAR(128), "
                "doccomment  SMALLTEXT, "
                "line        INTEGER, "
                "column      SMALLINT"
            ")"
        );
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS constants("
                "id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
                "file_path   VARCHAR(256) NOT NULL, "
                "name        VARCHAR(128), "
                "line        INTEGER, "
                "column      SMALLINT"
            ")"
        );
        self._connection.commit()

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

    def get_class_position(self, namespace, className):
        cursor = self._cursor
        file_path, line, column = (None, None, None, )
        while namespace[0] == '\\':
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

    def get_class_children(self, className):
        cursor = self._cursor
        children = []
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
        return children

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

    ### METHODS ###

    def add_method(self, filePath, namespace, className, methodName, isStatic, visibility, docComment, line, column):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "INSERT INTO classes_methods (file_path, class_id, name, is_static, visibility, doccomment, line, column) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (filePath, classId, methodName, int(isStatic), visibility, docComment, line, column, )
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

    ### MEMBERS ###

    def add_member(self, filePath, namespace, className, memberName, line, column, isStatic, visibility, docComment):
        cursor = self._cursor
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "INSERT INTO classes_members (file_path, class_id, name, is_static, visibility, doccomment, line, column) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (filePath, classId, memberName, isStatic, visibility, docComment, line, column )
        )
        self.__commitAfterXInserts()

    def get_member(self, namespace, className, memberName):
        cursor = self._cursor
        visibility, is_static, line, column, doccomment = (None, None, None, None, None, )
        classId, filePath = self.get_class_id(namespace, className)
        cursor.execute(
            "SELECT visibility, is_static, line, column, doccomment "
            "FROM classes_members "
            "WHERE class_id=? and name=?",
            (classId, memberName, )
        )
        row = cursor.fetchone()
        if row != None:
            visibility, is_static, line, column, doccomment = row
        return (visibility, is_static, filePath, line, column, doccomment, )

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

    ### FUNCTIONS ###

    def add_function(self, filePath, namespace, functionName, docComment, line, column):
        cursor = self._cursor
        while len(namespace)>0 and namespace[0] == '\\':
            namespace = namespace[1:]
        cursor.execute(
            "INSERT INTO functions (file_path, namespace, name, doccomment, line, column) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (filePath, namespace, functionName, docComment, line, column, )
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
            "SELECT name "
            "FROM functions "
        )
        functions = []
        for name, in result:
            functions.append(name)
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
    
    ### FULLTEXT SEARCH ###

    def do_fulltext_search(self, searchTerms):
        cursor = self._cursor

        # searchResults: [[filePath, line, column, priority, title], ... ]
        searchResults = []

        typeDefs = [
            {   'typeName':      'File',
                'table':         'files',
                'searchColumns': ['file_path', "'file'"],
                'selectPart':    "files.file_path, 1, 1, files.file_path",
                'priority':      100
            },
            {   'typeName':      'Class',
                'table':         'classes',
                'searchColumns': ['namespace', 'name', "'class'"],
                'selectPart':    "file_path, line, column, namespace || '\\' || name",
                'priority':      400
            },
            {   'typeName':      'Class-Constant',
                'table':         'classes_constants',
                'searchColumns': ['name', 'value', "'class'", "'constant'"],
                'selectPart':    "file_path, line, column, (SELECT namespace || '\\' || name from classes WHERE class_id == id) || '::' || name",
                'priority':      300
            },
            {   'typeName':      'Method',
                'table':         'classes_methods',
                'searchColumns': ['name', "'method'"],
                'selectPart':    "file_path, line, column, (SELECT namespace || '\\' || name from classes WHERE class_id == id) || '->' || name || '()'",
                'priority':      300
            },
            {   'typeName':      'Member',
                'table':         'classes_members',
                'searchColumns': ['name', "'member'"],
                'selectPart':    "file_path, line, column, (SELECT namespace || '\\' || name from classes WHERE class_id == id) || '->' || name",
                'priority':      300
            },
            {   'typeName':      'Function',
                'table':         'functions',
                'searchColumns': ['name', "'function'"],
                'selectPart':    "file_path, line, column, name",
                'priority':      300
            },
            {   'typeName':      'Constant',
                'table':         'constants',
                'searchColumns': ['name', "'constant'"],
                'selectPart':    "file_path, line, column, name",
                'priority':      300
            }
        ]

        for typeDef in typeDefs:
            tableName  = typeDef['table']
            columns    = typeDef['searchColumns']
            selectPart = typeDef['selectPart']
            priority   = typeDef['priority']
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
                searchResults.append([path, line, column, priority - len(title), typeName, title])
        
        return searchResults

    ### HELPERS ###

    def __commitAfterXInserts(self):
        self._insert_counter+=1
        if self._insert_counter >= 3000:
            self._insert_counter = 0
            self._connection.commit()
        
    def sync(self):
        self._connection.commit()

    def removeFile(self, filePath):
        cursor = self._cursor
        result = cursor.execute("SELECT id FROM classes WHERE file_path = ?", (filePath, ))
        for classId, in result:
            cursor.execute("DELETE FROM classes_methods         WHERE class_id = ?", (classId, ))
            cursor.execute("DELETE FROM classes_interfaces_uses WHERE class_id = ?", (classId, ))
            cursor.execute("DELETE FROM classes_constants       WHERE class_id = ?", (classId, ))
        cursor.execute("DELETE FROM classes   WHERE file_path = ?", (filePath, ))
        cursor.execute("DELETE FROM functions WHERE file_path = ?", (filePath, ))
        cursor.execute("DELETE FROM files     WHERE file_path = ?", (filePath, ))
        #cursor.execute("VACUUM")
        self.__commitAfterXInserts()

    def empty(self):
        cursor = self._cursor
        cursor.execute("DROP TABLE IF EXISTS classes_members")
        cursor.execute("DROP TABLE IF EXISTS classes_methods")
        cursor.execute("DROP TABLE IF EXISTS classes_interfaces_uses")
        cursor.execute("DROP TABLE IF EXISTS classes_constants")
        cursor.execute("DROP TABLE IF EXISTS constants")
        cursor.execute("DROP TABLE IF EXISTS classes")
        cursor.execute("DROP TABLE IF EXISTS functions")
        cursor.execute("DROP TABLE IF EXISTS files")
        cursor.execute("VACUUM")
        self.__create_tables()
        self._connection.commit()

