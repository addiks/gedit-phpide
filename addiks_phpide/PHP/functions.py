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

import re

docCommentRegex = re.compile("\\@([\\\\a-zA-Z_-]+)(([\$ \ta-zA-Z0-9\?\\\\_-]+)*)")
whitespaceRegex = re.compile("\s+")

def get_annotations_by_doccomment(docComment):
    annotations = {}
    for match in docCommentRegex.finditer(docComment):
        key, value = match.groups()[0:2]

        if key not in annotations:
            annotations[key] = []

        tags = whitespaceRegex.split(value.strip())
        if len(tags)>0:
            annotations[key].append(tags)
        else:
            annotations[key].append(value)

    return annotations

def get_namespace_by_classname(className):
    if className != None and len(className)>0 and className[0] == "?":
        className = className[1:]

    namespace = "\\"
    newClassName = className

    if className != None and className.find("\\") >= 0:
        classNameParts = className.split("\\")
        newClassName   = classNameParts.pop()
        namespace      = "\\".join(classNameParts)
        if len(namespace)<=0:
            namespace = "\\"

    return (namespace, newClassName)
