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

from PHP.phplexer import token_get_all
from PHP.phplexer import token_name
from PHP.phplexer import token_num
from PHP.phptokenparser import parse_php_tokens
import sys
import os
import os.path
import time
import operator
import traceback
import sqlite3
import csv
import hashlib

T_DOC_COMMENT = token_num("T_DOC_COMMENT")

class PhpIndex:

    def __init__(self, index_path, update_callback=None, error_callback=None, finished_callback=None, indexPathManager=None):
        self._parsers = {}
        self._index_path_manager = indexPathManager
        self._index_path = index_path
        self._update_callback = update_callback
        self._error_callback = error_callback
        self._finished_callback = finished_callback
        self._open_index()

    ### BUILD API

    def build(self, work_dir):

        try:
            while work_dir[-1:] == '/':
                work_dir = work_dir[:-1]

            self._open_index()
            self._storage.empty()

            self._all_files_count = 0
            self._done_files_count = 0

            self._index_internals()
            self._collect_directory(work_dir)
            self._index_directory(work_dir)

            if self._finished_callback != None:
                self._finished_callback()

        except sqlite3.OperationalError as exception:
            print(dir(exception))
            self._error_callback("Database error: "+exception.strerror)

    def update(self, work_dir):

        try:
            while work_dir[-1:] == '/':
                work_dir = work_dir[:-1]

            self._open_index()

            self._all_files_count = 0
            self._done_files_count = 0

            self._remove_deleted(work_dir)
            self._collect_directory(work_dir, True)
            self._update_directory(work_dir)

            if self._finished_callback != None:
                self._finished_callback()

        except sqlite3.Error as exception:
            self._error_callback("Database error: "+exception.args[0])

        except sqlite3.OperationalError as exception:
            self._error_callback("Database error: "+exception.strerror)

    def set_build_callback(self, callback):
        self._callback = callback

    ### INDEX ACCESS API

    ### HELPERS

    def _open_index(self):
        indexPath = self._index_path

        if indexPath == 'neo4j':
            from storage.neo4j import Neo4jStorage
            self._storage = Neo4jStorage()

        elif indexPath == 'dummy':
            from storage.dummy import DummyStorage
            self._storage = DummyStorage()

        elif indexPath.find(".sqlite3")>0:
            from storage.sqlite3 import Sqlite3Storage
            self._storage = Sqlite3Storage(indexPath)

        elif indexPath.find("/")>0:
            from storage.shelve import ShelveStorage
            self._storage = ShelveStorage(indexPath)

        else:
            raise Exception("Cannot open index '"+indexPath+"'!")

    def get_index(self):
        return self._storage

    ### BUILD HELPERS

    def _index_internals(self):
        storage = self._storage
        csvFilePath = os.path.dirname(__file__)+"/php.internals.csv"
        reader = csv.reader(open(csvFilePath, "r"), delimiter=",")
        for typeName, name, value in reader:
            docComment = ""
            namespace = "\\"

            if typeName == 'function':
                storage.add_function("INTERNAL", namespace, name, docComment, 0, 0)

            elif typeName in ['class', 'interface', 'trait']:
                className = name
                classType = typeName
                parentName = None
                interfaces = []
                isFinal = False
                isAbstract = False
                storage.add_class("INTERNAL", namespace, className, classType, parentName, interfaces, isFinal, isAbstract, docComment, 0, 0)

            elif typeName == 'member':
                #storage.add_member("INTERNAL", namespace, className, memberName, 0, 0, isStatic, visibility, docComment)
                pass

            elif typeName == 'method':
                #storage.add_method("INTERNAL", namespace, className, methodName, isStatic, visibility, docComment, 0, 0)
                pass

            elif typeName == 'variable':
                pass

            elif typeName == 'constant':
                storage.add_constant("INTERNAL", name, 0, 0)

    def _remove_deleted(self, directory):
        allFilesToCheck = self._storage.get_all_files()
        currentFileCount = 0
        for filePath in allFilesToCheck:
            self._update_callback(currentFileCount, len(allFilesToCheck), filePath)
            currentFileCount += 1
            if not self.__is_file_indexable(filePath):
                self._unindex_phpfile(filePath)

    def _collect_directory(self, directory, only_updates=False):
        for entry in os.listdir(directory):
            entryPath = directory+"/"+entry
            if os.path.isdir(entryPath):
                self._collect_directory(entryPath, only_updates)
            elif os.path.isfile(entryPath):
                if self.__is_file_indexable(entryPath):

                    currentMTime = int(os.path.getmtime(entryPath))
                    indexedMTime = int(self._storage.getmtime(entryPath))

                    if currentMTime > indexedMTime or not only_updates:
                        indexedHash = self._storage.gethash(entryPath)
                        currentHash = hashlib.sha256(open(entryPath, 'rb').read()).digest()

                        if currentHash != indexedHash:
                            self._all_files_count += 1

    def _index_directory(self, directory):
        for entry in os.listdir(directory):
            entryPath = directory+"/"+entry
            if os.path.isdir(entryPath):
                self._index_directory(entryPath)
            elif os.path.isfile(entryPath):
                if self.__is_file_indexable(entryPath):
                    self._done_files_count += 1
                    if self._update_callback != None:
                        self._update_callback(self._done_files_count, self._all_files_count, entryPath)
                    self._index_phpfile(entryPath)

    def _update_directory(self, directory):
        for entry in os.listdir(directory):
            entryPath = directory+"/"+entry
            if os.path.isdir(entryPath):
                self._update_directory(entryPath)
            elif os.path.isfile(entryPath):
                if self.__is_file_indexable(entryPath):

                    currentMTime = int(os.path.getmtime(entryPath))
                    indexedMTime = int(self._storage.getmtime(entryPath))

                    if currentMTime > indexedMTime:
                        indexedHash = self._storage.gethash(entryPath)
                        currentHash = hashlib.sha256(open(entryPath, 'rb').read()).digest()

                        if currentHash != indexedHash:
                            self._done_files_count += 1
                            if self._update_callback != None:
                                self._update_callback(self._done_files_count, self._all_files_count, entryPath)
                            self._unindex_phpfile(entryPath)
                            self._index_phpfile(entryPath)

    def __is_file_indexable(self, filePath):
        if filePath[-4:] == ".php" and self._index_path_manager.shouldIncludePathInIndex(filePath):
            return True
        else:
            return False

    def _index_phpfile(self, filePath):

        with open(filePath, "r", encoding = "ISO-8859-1") as f:
            code = f.read()
        tokens, comments = token_get_all(code)

        blocks, namespace, use_statements, use_statement_index, constants = parse_php_tokens(tokens)

        # add extracted data to index

        hashValue = hashlib.sha256(open(filePath, 'rb').read()).digest()
        self._storage.add_file(filePath, namespace, int(os.path.getmtime(filePath)), hashValue)

        for block in blocks:
            if len(block) > 2:
                if block[2] == 'class':
                    tokenIndex     = block[3]
                    className      = block[4]
                    parentName     = block[5]
                    interfaces     = block[6]
                    isFinal        = block[7]
                    isAbstract     = block[8]
                    classType      = block[9]
                    members        = block[10]
                    classconstants = block[11]
                    docComment     = block[12]
                    line   = tokens[tokenIndex][2]
                    column = tokens[tokenIndex][3]

                    if parentName in use_statements:
                        parentName = use_statements[parentName]

                    if parentName != None and parentName[0] != '\\':
                        if len(namespace) > 1:
                            parentName = "\\" + namespace + "\\" + parentName
                        else:
                            parentName = "\\" + parentName

                    for interface in interfaces:
                        if interface in use_statements:
                            interfaces.remove(interface)
                            interfaces.append(use_statements[interface])

                    self._storage.add_class(filePath, namespace, className, classType, parentName, interfaces, isFinal, isAbstract, docComment, line, column)

                    for constTokenIndex in classconstants:
                        constantName   = tokens[constTokenIndex+1][1]
                        constantValue  = tokens[constTokenIndex+3][1]
                        constantLine   = tokens[constTokenIndex][2]
                        constantColumn = tokens[constTokenIndex][3]
                        constantDocComment = ""
                        if tokens[constTokenIndex-1][0] == T_DOC_COMMENT:
                            constantDocComment = tokens[constTokenIndex-1][1]
                        self._storage.add_class_constant(filePath, namespace, className, constantName, constantValue, constantDocComment, constantLine, constantColumn)

                    for memberTokenIndex in members:
                        memberName   = tokens[memberTokenIndex][1]
                        memberLine   = tokens[memberTokenIndex][2]
                        memberColumn = tokens[memberTokenIndex][3]

                        isStatic     = False
                        visibility   = "public"
                        memberKeywordIndex = memberTokenIndex-1
                        while tokens[memberKeywordIndex][1] in ['public', 'protected', 'private', 'static']:
                            if tokens[memberKeywordIndex][1] == 'static':
                                isStatic = True
                            if tokens[memberKeywordIndex][1] in ['public', 'protected', 'private']:
                                visibility = tokens[memberKeywordIndex][1]
                            memberKeywordIndex-=1
    
                        memberDocComment = ""
                        if tokens[memberKeywordIndex][0] == T_DOC_COMMENT:
                            memberDocComment = tokens[memberKeywordIndex][1]

                        self._storage.add_member(filePath, namespace, className, memberName, memberLine, memberColumn, isStatic, visibility, memberDocComment)

                if block[2] == 'method':
                    tokenIndex = block[3]
                    className  = block[4]
                    methodName = block[5]
                    keywords   = block[6]
                    doccomment = block[7]
                    line   = tokens[tokenIndex][2]
                    column = tokens[tokenIndex][3]

                    isStatic = "static" in keywords
                    visibility = list(set(keywords) & set(['public', 'protected', 'private']))
                    if len(visibility) == 1:
                        visibility = visibility[0]
                    else:
                        visibility = 'public'

                    self._storage.add_method(filePath, namespace, className, methodName, isStatic, visibility, doccomment, line, column)

                if block[2] == 'function' and block[4] != None:
                    tokenIndex   = block[3]
                    functionName = block[4]
                    doccomment   = block[5]
                    line   = tokens[tokenIndex][2]
                    column = tokens[tokenIndex][3]

                    self._storage.add_function(filePath, namespace, functionName, doccomment, line, column)

        for constantIndex in constants:
            constantName   = tokens[constantIndex+2][1]
            constantLine   = tokens[constantIndex][2]
            constantColumn = tokens[constantIndex][3]
            self._storage.add_constant(filePath, constantName, constantLine, constantColumn)

        self._storage.sync()

    def _unindex_phpfile(self, filePath):
        self._storage.removeFile(filePath)



