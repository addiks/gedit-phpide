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

class DummyStorage:
    
    def __init__(self):
        pass

    def getmtime(self, filePath):
        pass

    def add_file(self, filePath, namespace, mtime):
        pass

    def add_class(self, filePath, namespace, className, classType, parentName, interfaces, isFinal, isAbstract, docComment, line, column):
        pass

    def add_class_constant(self, filePath, namespace, className, name, value, line, column):
        pass

    def add_method(self, filePath, namespace, className, methodName, keywords, doccomment, line, column):
        pass

    def add_function(self, filePath, namespace, functionName, line, column):
        pass

    def get_member(self, namespace, className, memberName):
        pass

    def get_class_position(self, namespace, className):
        pass

    def get_class_const_position(self, namespace, className, constantName):
        pass

    def get_method_position(self, namespace, className, methodName):
        pass

    def get_function_position(self, namespace, functionName):
        pass

    def get_constant_position(self, constantName):
        pass

    def get_member_position(self, namespace, className, memberName):
        pass

    def sync(self):
        pass

    def removeFile(self, filePath):
        pass

    def empty(self):
        pass


