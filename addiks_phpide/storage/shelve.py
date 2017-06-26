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

import sys
import os
import os.path
import time
import _bsddb
import shelve

class ShelveStorage:
    
    def __init__(self, index_path):
        self._index_path = index_path
        self._shelve = shelve.open(self._index_path, writeback=True)

    def getmtime(self, filePath):
        shelve = self._shelve
        indexedMTime = 0
        if 'mtime:'+entryPath in shelve:
            indexedMTime = shelve['mtime:'+entryPath]
        return indexedMTime

    def addFile(self, filePath, namespace, mtime):
        shelve = self._shelve
        shelve[filePath] = []
        shelve['mtime:'+filePath] = mtime

        if 'namespace:'+namespace not in shelve:
            shelve['namespace:'+namespace] = []

    def addClass(self, filePath, namespace, className, classType, parentName, interfaces, isFinal, isAbstract, line, column):
        shelve = self._shelve

        key = 'class:'+namespace + '\\' + className
        shelve[key] = [
            [filePath, line, column, 'class'],
            [className, namespace],
            parentName,
            interfaces,
            isFinal,
            isAbstract,
            classType,
        ]

        shelve[filePath].append(key)
        shelve['pos:'+filePath+":"+str(line)+":"+str(column)] = key
        shelve['namespace:'+namespace].append(key)

        if parentName != None:
            if 'parent:'+parentName not in shelve:
                shelve['parent:'+parentName] = []
            shelve['parent:'+parentName].append(key)

        for interface in interfaces:
            if 'implements:'+interface not in shelve:
                shelve['implements:'+interface] = []
            shelve['implements:'+interface].append(key)
        
    def addClassConstant(self, filePath, namespace, className, name, value, line, column):
        pass

    def addMethod(self, filePath, namespace, className, methodName, keywords, line, column):
        shelve = self._shelve

        key = 'method:' + namespace + '\\' + className + '::' + methodName
        shelve[key] = [
            [filePath, line, column, 'method'],
            [methodName, className, namespace],
            keywords
        ]

        if 'classMethods:'+classId not in shelve:
            shelve['classMethods:'+classId] = []

        shelve[filePath].append(key)
        shelve['pos:'+filePath+":"+str(line)+":"+str(column)] = key
        shelve['namespace:'+namespace].append(key)
        shelve['classMethods:' + classId].append(key)

    def addFunction(self, filePath, namespace, functionName, line, column):
        shelve = self._shelve

        key = 'function:'+functionName
        shelve[key] = [
            [filePath, line, column, 'function'],
            [functionName, namespace]
        ]
        
        shelve[filePath].append(key)
        shelve['pos:'+filePath+":"+str(line)+":"+str(column)] = key
        shelve['namespace:'+namespace].append(key)

    def sync(self):
        shelve = self._shelve
        shelve.sync()

    def removeFile(self, filePath):
        shelve = self._shelve

        if filePath in shelve:
            try:
                for key in shelve[filePath]:
                    
                    if key not in shelve:
                        if self._error_callback != None:
                            message = "Fault in index: key '"+key+"' registered for file '"+filePath+"' does not exist! Skipping..."
                            self._error_callback(message)
                        continue

                    data = shelve[key]

                    if len(data) < 1 or len(data[0]) < 4:
                        if self._error_callback != None:
                            message = "Fault in index: data-block has no type! Skipping..."
                            self._error_callback(message)
                        continue

                    line   = data[0][1]
                    column = data[0][2]
                    typeId = data[0][3]

                    if 'pos:'+filePath+":"+str(line)+":"+str(column) in shelve:
                        del shelve['pos:'+filePath+":"+str(line)+":"+str(column)]

                    namespace = None

                    if typeId == 'function':
                        functionName = data[1][0]
                        namespace    = data[1][1]
                        
                    elif typeId == 'method':
                        methodName = data[1][0]
                        className  = data[1][1]
                        namespace  = data[1][2]
                        classId  = namespace + '\\' + className
                        shelve['classMethods:' + classId].remove(key)
                                
                    elif typeId == 'class':
                        className  = data[1][0]
                        namespace  = data[1][1]
                        parentName = data[2]
                        interfaces = data[3]
                        if parentName != None:
                            shelve['parent:'+parentName].remove(key)
                        for interface in interfaces:
                            shelve['implements:'+interface].remove(key)
                        
                    shelve['namespace:'+namespace].remove(key)
                    if key in shelve:
                        del shelve[key]

                del shelve['mtime:'+filePath]
                del shelve[filePath]
            except (_bsddb.DBNotFoundError, KeyError, ValueError) as exception:
                type_, value_, traceback_ = sys.exc_info()
                if self._error_callback != None:
                    message = str(type_) + ": " + str(exception) + "\n" + "".join(traceback.format_tb(traceback_))
                    self._error_callback(message)
        shelve.sync()

    def empty(self):
        shelve = self._shelve
        shelve.close()
        os.remove(self._index_path)
        self._shelve = shelve.open(self._index_path, writeback=True)

