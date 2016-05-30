# Copyright (C) 2015 Gerrit Addiks <gerrit@addiks.net>
# https://github.com/addiks/gedit-window-management
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

import csv

class IndexPathManager:

    __filepath = None

    def __init__(self, filepath):
        self.__filepath = filepath

    def getPaths(self):
        result = []
        with open(self.__filepath, 'r') as handle:
            csvreader = csv.reader(handle, delimiter=',')
            for entryPath, entryType in csvreader:
                isExclude = entryType == "exclude"
                result.append([entryPath, isExclude])
        return result

    def addPath(self, path, isExclude=False):
        entryType = "include"
        if isExclude:
            entryType = "exclude"
        with open(self.__filepath, 'a') as handle:
            csvwriter = csv.writer(handle, delimiter=',')
            csvwriter.writerow([path, entryType])

    def clearPaths(self):
        with open(self.__filepath, 'w') as handle:
            pass

    def removePath(self, path):
        paths = self.getPaths()
        self.clearPaths()
        for entryPath, isExclude in paths:
            if path != entryPath:
                self.addPath(entryPath, isExclude)

    def togglePathType(self, path):
        paths = self.getPaths()
        self.clearPaths()
        for entryPath, isExclude in paths:
            if path == entryPath:
                isExclude = not isExclude
            self.addPath(entryPath, isExclude)

    def modifyPath(self, oldPath, newPath, newIsExclude = None):
        paths = self.getPaths()
        self.clearPaths()
        for entryPath, isExclude in paths:
            if oldPath == entryPath:
                entryPath = newPath
                if newIsExclude is not None:
                    isExclude = newIsExclude
            self.addPath(entryPath, isExclude)

    def shouldIncludePathInIndex(self, filePath):
        shouldInclude = True
        for entryPath, isExclude in self.getPaths():
            if filePath[0:len(entryPath)] == entryPath:
                shouldInclude = not isExclude
        return shouldInclude

