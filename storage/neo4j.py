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

from py2neo import Graph
from py2neo.neo4j import WriteBatch

class Neo4jStorage:
    
    def __init__(self):
        self._graph = Graph()
        self._batch = WriteBatch(self._graph)
        self._mtimeCache = {}

    def getmtime(self, filePath):
        indexedMTime = 0

        if len(self._mtimeCache) <= 0:
            results = self._graph.cypher.execute("MATCH (f:File) RETURN f.path as path, f.mtime as mtime")
            for path, mtime in results:
                self._mtimeCache[str(path)] = mtime

        if filePath not in self._mtimeCache:
            results = self._graph.cypher.execute(
                "MATCH (f:File {path: '"+filePath+"'}) "
                "RETURN f.path as path, f.mtime as mtime "
                "LIMIT 1"
            )
            for path, mtime in results:
                self._mtimeCache[str(path)] = mtime
            
        if filePath in self._mtimeCache:
            indexedMTime = self._mtimeCache[filePath]

        return indexedMTime

    def addFile(self, filePath, namespace, mtime):
        graph = self._graph

#        fileNode      = batch.create(node(name="File"))
#        namespaceNode = batch.create(node(name="Namespace"))
#        batch.create(rel(fileNode, "HAS", namespaceCypher))

        namespaceCypher = namespace.replace('\\', '\\\\')
        graph.cypher.execute("CREATE (f:File {path: '"+filePath+"', mtime: "+str(mtime)+"})")
        graph.cypher.execute("MERGE (n:Namespace {namespace: '"+namespaceCypher+"'})")
        graph.cypher.execute(
            " MATCH (f:File {path: '"+filePath+"'}),"
            "       (n:Namespace {namespace: '"+namespaceCypher+"'})"
            " CREATE (f)-[:HAS]->(n)"
        )

    def addClass(self, filePath, namespace, className, classType, parentName, interfaces, isFinal, isAbstract, line, column):
        graph = self._graph
        namespaceCypher = namespace.replace('\\', '\\\\')

        graph.cypher.execute(
            "CREATE (c:Class {name: '"+className+"', type: '"+classType+"', "
                "isFinal: '"+str(isFinal)+"', isAbstract: '"+str(isAbstract)+"', "
                "line: '"+str(line)+"', column: '"+str(column)+"'"
            "})"
        )
        graph.cypher.execute(
            "MATCH "
                "(c:Class {name: '"+className+"'}), "
                "(f:File {path: '"+filePath+"'}), "
                "(n:Namespace {namespace: '"+namespaceCypher+"'}) "
            "CREATE (c)-[:IS_IN]->(f) "
            "CREATE (c)-[:IS_IN]->(n) "
        )

        if parentName != None:
            graph.cypher.execute(
                "MATCH (c:Class {name: '"+className+"'}) SET c.parentName='"+parentName+"'"
            )

        for interface in interfaces:
            graph.cypher.execute("MERGE (i:Interface {name: '"+interface+"'})")
            graph.cypher.execute(
                "MATCH "
                    "(c:Class {name: '"+className+"'}), "
                    "(i:Interface {name: '"+interface+"'}) "
                "CREATE (c)-[:IS_IN]->(i) "
            )
        
    def addClassConstant(self, filePath, namespace, className, name, value, line, column):
        pass

    def addMethod(self, filePath, namespace, className, methodName, keywords, line, column):
        graph = self._graph
        namespaceCypher = namespace.replace('\\', '\\\\')

        graph.cypher.execute(
            "CREATE (m:Method {name: '"+methodName+"', "
                "line: '"+str(line)+"', column: '"+str(column)+"', "
                "className: '"+className+"', "
                "keywords: \""+repr(keywords)+"\""
            "})"
        )

        graph.cypher.execute(
            "MATCH "
                "(m:Method {name: '"+methodName+"', className: '"+className+"'}), "
                "(c:Class {name: '"+className+"'}) -[:IS_IN]->"
                "(n:Namespace {namespace: '"+namespaceCypher+"'}) "
            "CREATE (m)-[:IS_IN]->(c) "
        )

    def addFunction(self, filePath, namespace, functionName, line, column):
        graph = self._graph
        namespaceCypher = namespace.replace('\\', '\\\\')
        
        graph.cypher.execute(
            "CREATE (f:Function {name: '"+functionName+"', "
                "line: '"+str(line)+"', column: '"+str(column)+"'"
            "})"
        )

        graph.cypher.execute(
            "MATCH "
                "(fn:Function {name: '"+functionName+"'}), "
                "(fl:File {path: '"+filePath+"'}), "
                "(ns:Namespace {namespace: '"+namespaceCypher+"'}) "
            "CREATE (fn)-[:IS_IN]->(fl) "
            "CREATE (fn)-[:IS_IN]->(ns) "
        )

    def sync(self):
        graph = self._graph
        graph.cypher.execute(
            "MATCH (c:Class), (p:Class) "
            "WHERE HAS(c.parentName) AND c.parentName = p.name "
            "CREATE (p)-[:IS_PARENT_OF]->(c) "
            "REMOVE c.parentName"
        )

    def removeFile(self, filePath):
        graph = self._graph
        graph.cypher.execute("MATCH (:File  {path: '"+filePath+"'})<--(:Class)-[r2]->(i:Interface)-[r]-() DELETE r2, r, i")
        graph.cypher.execute("MATCH (:File  {path: '"+filePath+"'})<--(:Class)<-[r2]-(m:Method)   -[r]-() DELETE r2, r, m")
        graph.cypher.execute("MATCH (:File  {path: '"+filePath+"'})<-[r2]-(c:Class)               -[r]-() DELETE r2, r, c")
        graph.cypher.execute("MATCH (:File  {path: '"+filePath+"'})<-[r2]-(f:Function)            -[r]-() DELETE r2, r, f")
        graph.cypher.execute("MATCH (f:File {path: '"+filePath+"'})                               -[r]-() DELETE     r, f")

    def empty(self):
        graph = self._graph
        graph.cypher.execute("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r")


