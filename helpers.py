"""
 * Copyright (C) 2013  Gerrit Addiks.
 * This package (including this file) was released under the terms of the GPL-3.0.
 * You should have received a copy of the GNU General Public License along with this program.
 * If not, see <http://www.gnu.org/licenses/> or send me a mail so i can send you a copy.
 * 
 * @license GPL-3.0
 * @author Gerrit Addiks <gerrit@addiks.de>
 * @web http://addiks.net/
 * @version 1.0
"""

import os

def file_get_contents(filename):
    """ retrieves the contents of a file. """
    with open(filename, "r", encoding = "ISO-8859-1") as f:
        return f.read()

def file_put_contents(filePath, data):
    if not os.path.exists(os.path.dirname(filePath)):
        os.makedirs(os.path.dirname(filePath))
    with open(filePath, "w", encoding="ISO-8859-1") as f:
        f.write(data)

def group(lst, n):
    """group([0,3,4,10,2,3], 2) => [(0,3), (4,10), (2,3)]
    
    Group a list into consecutive n-tuples. Incomplete tuples are
    discarded e.g.
    
    >>> group(range(10), 3)
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]

    SOURCE: http://code.activestate.com/recipes/303060-group-a-list-into-sequential-n-tuples/

    """
    return zip(*[lst[i::n] for i in range(n)])

def intersect(a, b):
    return list(set(a) & set(b))

def get_namespace_by_classname(className):
    namespace = "\\"
    newClassName = className
    
    if className != None and className.find("\\") >= 0:
        classNameParts = className.split("\\")
        newClassName   = classNameParts.pop()
        namespace      = "\\".join(classNameParts)
        if len(namespace)<=0:
            namespace = "\\"

    return (namespace, newClassName)
 
