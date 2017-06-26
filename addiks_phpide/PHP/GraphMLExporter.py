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

from .functions import get_namespace_by_classname
from .PhpFileAnalyzer import PhpFileAnalyzer
from lxml import etree as xml

class GraphMLExporter:

    def __init__(self):
        self.xmlns_namespace = "http://graphml.graphdrawing.org/xmlns"
        self.xsi_namespace = "http://www.w3.org/2001/XMLSchema-instance"
        self.ygraphml_namespace = "http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd"
        self.y_namespace = "http://www.yworks.com/xml/graphml"
        self.nsmap = {None : self.xmlns_namespace}

        self.xmlns = "{%s}" % self.xmlns_namespace
        self.xsi   = "{%s}" % self.xsi_namespace
        self.y     = "{%s}" % self.y_namespace

    def exportClassGraphhToFile(
        self,
        plugin,
        storage,
        classes,
        filePath,
        depth=0,
        classesExcluded=[],
        options = {}
    ):

        ### FETCH NODES AND EDGES BY DEPTH

        allNodes = []
        allEdges = []

        cleanedClasses = []
        for className in classes:
            className = self.__clearClassName(className)
            cleanedClasses.append(className)
        classes = cleanedClasses

        cleanedClassesExcluded = []
        for className in classesExcluded:
            className = self.__clearClassName(className)
            cleanedClassesExcluded.append(className)
        classesExcluded = cleanedClassesExcluded

        if depth > 0:
            lastAddedClasses = classes
            while depth > 0:
                classesToAdd = []
                for className in lastAddedClasses:
                    if className not in classesExcluded:
                        nodes, edges = self._fetchRelatedEdges(className, plugin, storage, options)
                        allNodes += nodes
                        allEdges += edges
                        for node in nodes:
                            nodeClassName, nodeType = node.split('@')
                            classesToAdd.append(nodeClassName)
                classes += classesToAdd
                classes = list(set(classes))
                lastAddedClasses = list(set(classesToAdd))
                depth -= 1
            nodes = allNodes
            edges = allEdges

        else:
            nodes = []
            edges = [] # TODO: fill edges from nodes
            for nodeFullClassName in list(set(classes)):
                nodeNamespace, nodeClassName = get_namespace_by_classname(nodeFullClassName)
                classType = storage.get_class_type(nodeNamespace, nodeClassName)
                nodes.append(nodeFullClassName + "@" + classType)

        ### INIT XML

        # http://lxml.de/tutorial.html

        xmlns_namespace = "http://graphml.graphdrawing.org/xmlns"
        xsi_namespace = "http://www.w3.org/2001/XMLSchema-instance"
        ygraphml_namespace = "http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd"
        nsmap = {None : xmlns_namespace}

        xmlns = "{%s}" % xmlns_namespace
        xsi   = "{%s}" % xsi_namespace

        tree = xml.ElementTree()

        graphmlXml = xml.Element(self.xmlns + "graphml", nsmap=self.nsmap)
        graphmlXml.set(self.xsi + "schemaLocation", self.xmlns_namespace + " " + self.ygraphml_namespace)

        tree._setroot(graphmlXml)

        graphXml = xml.SubElement(graphmlXml, self.xmlns + "graph", edgedefault="directed")
        graphXml.set("id", "G")

        for keyAttributes in [
            {"for": "graph", "id": "d0", "attr.type": "string", "attr.name": "description"},
            {"for": "node",  "id": "d1", "attr.type": "string", "attr.name": "url"},
            {"for": "node",  "id": "d2", "attr.type": "string", "attr.name": "description"},
            {"for": "node",  "id": "d3", "yfiles.type": "nodegraphics"},
            {"for": "edge",  "id": "d4", "attr.type": "string", "attr.name": "url"},
            {"for": "edge",  "id": "d5", "attr.type": "string", "attr.name": "description"},
            {"for": "edge",  "id": "d6", "yfiles.type": "edgegraphics"}
        ]:
            keyXml = xml.Element("key")
            for key, value in keyAttributes.items():
                keyXml.set(key, value)
            graphmlXml.append(keyXml)

        ### WRITE NODES AND EDGES TO XML

        classToNodeIndexMap = {}
        counter = 0
        for node in nodes:
            fullClassName, classType = node.split("@")
            if fullClassName not in classToNodeIndexMap:
                classToNodeIndexMap[fullClassName] = counter
                namespace, className = get_namespace_by_classname(fullClassName)

                headerText = className + "\n" + namespace

                if classType != "class":
                    headerText = "<<" + classType + ">>\n" + headerText

                bodyText = ""

                if "contain_methods" not in options or options["contain_methods"]:
                    for methodName in storage.get_all_class_methods(namespace, className):
                        methodData = storage.get_method(namespace, className, methodName)
                        visibility, is_static, methodFilePath, line, column, doccomment = methodData
                        methodPrefix = "+"
                        if visibility == "protected":
                            methodPrefix = "#"
                        if visibility == "private":
                            methodPrefix = "-"
                        methodReturnTypeDef = ""
                        bodyText += methodPrefix + " " + methodName + methodReturnTypeDef + "()\n"

                if "contain_members" not in options or options["contain_members"]:
                    for memberName in storage.get_all_class_members(namespace, className):
                        memberData = storage.get_member(namespace, className, memberName)
                        visibility, is_static, memberFilePath, line, column, doccomment, typeHint = memberData
                        memberPrefix = "+"
                        if visibility == "protected":
                            memberPrefix = "#"
                        if visibility == "private":
                            memberPrefix = "-"
                        memberTypeDef = ""
                        if typeHint != None:
                            memberTypeDef = " : " + typeHint
                        bodyText += memberPrefix + " " + memberName + memberTypeDef + "\n"

                classFilePath, classLine, classColumn = storage.get_class_position(namespace, className)

                self._writeNodeXml(counter, headerText, bodyText, classType, graphXml, classFilePath)
                counter += 1

        edgeToIdMap = {}
        counter = 0
        for edge in edges:
            if edge not in edgeToIdMap:
                edgeToIdMap[edge] = counter
                sourceClassName, edgeType, targetClassName = edge.split("-")

                sourceIndex = classToNodeIndexMap[sourceClassName]
                targetIndex = classToNodeIndexMap[targetClassName]

                self._writeEdgeXml(counter, sourceIndex, targetIndex, edgeType, graphXml)
                counter += 1

        tree.write(filePath)

    def _writeNodeXml(self, index, headerText, bodyText, nodeType, graphXml, url=None):
        nodeXml = xml.SubElement(graphXml, "node")
        nodeXml.set("id", "n"+str(index))

        if url != None:
            urlDataXml = xml.Element("data", key="d1")
            urlDataXml.text = url
            nodeXml.append(urlDataXml)

        nodeXml.append(xml.Element("data", key="d2"))
        nodeGraphicsDataXml = xml.SubElement(nodeXml, "data", key="d3")

        lineCount = 0
        highestColumnCount = 0
        for line in headerText.split("\n"):
            lineCount += 1
            if len(line) > highestColumnCount:
                highestColumnCount = len(line)
        for line in bodyText.split("\n"):
            lineCount += 1
            if len(line) > highestColumnCount:
                highestColumnCount = len(line)

        yGenericNodeXml = xml.SubElement(
            nodeGraphicsDataXml,
            self.y + "GenericNode",
            configuration="com.yworks.entityRelationship.big_entity"
        )

        nodeWidth  = 10 + (highestColumnCount * 7)
        nodeHeight = 10 + (lineCount * 14)

        if nodeType == "interface":
            foregroundColor = "#E8F7F7"
            backgroundColor = "#B7E3E3"

        elif nodeType == "trait":
            foregroundColor = "#F2F7E8"
            backgroundColor = "#D3E3B7"

        else:
            foregroundColor = "#E8EEF7"
            backgroundColor = "#B7C9E3"

        yGeometryXml = xml.SubElement(
            yGenericNodeXml,
            self.y + "Geometry",
            height=str(nodeHeight),
            width=str(nodeWidth),
            x="0.0",
            y="0.0"
        )

        yFillXml = xml.SubElement(
            yGenericNodeXml,
            self.y + "Fill",
            color=foregroundColor,
            color2=backgroundColor,
            transparent="false"
        )

        yBorderStyleXml = xml.SubElement(
            yGenericNodeXml,
            self.y + "BorderStyle",
            color="#000000",
            type="line",
            width="1.0"
        )

        yNodeLabelHeaderXml = xml.SubElement(
            yGenericNodeXml,
            self.y + "NodeLabel",
            alignment="center",
            autoSizePolicy="content",
            backgroundColor=backgroundColor,
            configuration="com.yworks.entityRelationship.label.name",
            fontFamily="Monospace",
            fontSize="12",
            fontStyle="plain",
            hasLineColor="false",
            height="31.9375",
            modelName="internal",
            modelPosition="t",
            textColor="#000000",
            visible="true",
            width="137.880859375",
            x="16.5595703125",
            y="4.0"
        )

        yNodeLabelHeaderXml.text = headerText

        yNodeLabelBodyXml = xml.SubElement(
            yGenericNodeXml,
            self.y + "NodeLabel",
            alignment="left",
            autoSizePolicy="content",
            configuration="com.yworks.entityRelationship.label.attributes",
            fontFamily="Monospace",
            fontSize="12",
            fontStyle="plain",
            hasBackgroundColor="false",
            hasLineColor="false",
            height="4.0",
            modelName="custom",
            textColor="#000000",
            visible="true",
            width="4.0",
            x="2.0",
            y="43.9375"
        )

        yNodeLabelBodyXml.text = bodyText

        yLabelModelXml = xml.SubElement(
            yNodeLabelBodyXml,
            self.y + "LabelModel"
        )

        yErdAttributesNodeLabelModelXml = xml.SubElement(
            yLabelModelXml,
            self.y + "ErdAttributesNodeLabelModel"
        )

        yModelParameterXml = xml.SubElement(
            yNodeLabelBodyXml,
            self.y + "ModelParameter"
        )

        yErdAttributesNodeLabelModelParameterXml = xml.SubElement(
            yModelParameterXml,
            self.y + "ErdAttributesNodeLabelModelParameter"
        )

        yStylePropertiesXml = xml.SubElement(
            yGenericNodeXml,
            self.y + "StyleProperties"
        )

        yPropertyXml = xml.SubElement(
            yStylePropertiesXml,
            self.y + "Property",
            name="y.view.ShadowNodePainter.SHADOW_PAINTING",
            value="true"
        )
        yPropertyXml.set("class", "java.lang.Boolean")

    def _writeEdgeXml(self, index, sourceIndex, targetIndex, edgeType, graphXml):
        edgeXml = xml.SubElement(
            graphXml,
            "edge",
            id="e"+str(index),
            source="n"+str(sourceIndex),
            target="n"+str(targetIndex)
        )

        edgeXml.append(xml.Element("data", key="d4"))
        edgeXml.append(xml.Element("data", key="d5"))

        edgeGraphicsDataXml = xml.SubElement(edgeXml, "data", key="d6")

        yPolyLineEdgeXml = xml.SubElement(edgeGraphicsDataXml, self.y + "PolyLineEdge")

        if edgeType == "generalization":
            lineColor = "#000000"
            lineType = "line"
            sourceArrow = "none"
            targetArrow = "white_delta"

        elif edgeType == "implementation":
            lineColor = "#000000"
            lineType = "dashed"
            sourceArrow = "none"
            targetArrow = "white_delta"

        elif edgeType == "composition":
            lineColor = "#000000"
            lineType = "line"
            sourceArrow = "diamond"
            targetArrow = "none"

        else: # association
            lineColor = "#aaaaaa"
            lineType = "line"
            sourceArrow = "none"
            targetArrow = "short"

        yPathXml = xml.SubElement(
            yPolyLineEdgeXml,
            self.y + "Path",
            sx="0.0",
            sy="0.0",
            tx="0.0",
            ty="0.0"
        )
        yLineStyleXml = xml.SubElement(
            yPolyLineEdgeXml,
            self.y + "LineStyle",
            color=lineColor,
            type=lineType,
            width="1.0"
        )
        yArrowsXml = xml.SubElement(
            yPolyLineEdgeXml,
            self.y + "Arrows",
            source=sourceArrow,
            target=targetArrow
        )
        yBendStyleXml = xml.SubElement(
            yPolyLineEdgeXml,
            self.y + "BendStyle",
            smoothed="false"
        )

    def _calculateCoupling(self, nodes, edges):
        couplingByNode = {}
        for node in nodes:
            nodeClassName, nodeType = node.split('@')
            coupling = 0
            for edge in edges:
                edgeBaseClass, edgeTargetClass, edgeType = edge.split("-")
                if edgeBaseClass == nodeClassName or edgeTargetClass == nodeClassName:
                    coupling += 1
            couplingByNode[node] = coupling
        return couplingByNode

    def _fetchRelatedEdges(self, fullClassName, plugin, storage, options={}):
        nodes = []
        edges = []

        fullClassName = self.__clearClassName(fullClassName)

        namespace, className = get_namespace_by_classname(fullClassName)

        classes = [fullClassName]

        ### INTERFACES

        interfacesImplemented = []

        if "include_interfaces" not in options or options["include_interfaces"]:
            interfaces = storage.get_class_interfaces(namespace, className)
            for interface in interfaces:
                interface = self.__clearClassName(interface)
                interfacesImplemented.append(interface)
                classes.append(interface)
                edges.append(fullClassName + "-implementation-" + interface)

        ### PARENT / CHILDREN

        if "include_parental_inheritance" not in options or options["include_parental_inheritance"]:
            parentClassName = storage.get_class_parent(namespace, className)
            if parentClassName != None:
                parentClassName = self.__clearClassName(parentClassName)
                classes.append(parentClassName)
                edges.append(fullClassName + "-generalization-" + parentClassName)

        if "include_children_inheritance" not in options or options["include_children_inheritance"]:
            children = storage.get_class_children(fullClassName)
            for childClassName in children:
                childClassName = self.__clearClassName(childClassName)
                if childClassName not in interfacesImplemented:
                    classes.append(childClassName)
                    edges.append(childClassName + "-generalization-" + fullClassName)

        ### COMPOSITIONS & AGGREGATIONS

        if "include_has_a_composition" not in options or options["include_has_a_composition"]:
            members = storage.get_all_class_members(namespace, className)
            for memberName in members:
                memberData = storage.get_member(namespace, className, memberName)
                typeHint = memberData[6]
                if typeHint != None and len(typeHint) > 0:
                    typeHint = self.__clearClassName(typeHint)
                    classes.append(typeHint)
                    edges.append(fullClassName + "-composition-" + typeHint)

        if "include_is_part_of_composition" not in options or options["include_is_part_of_composition"]:
            members = storage.get_members_by_type_hint(namespace, className)
            for memberNamespace, memberClassname, memberName in members:
                memberFullClassname = memberNamespace + "\\" + memberClassname
                memberFullClassname = self.__clearClassName(memberFullClassname)
                classes.append(memberFullClassname)
                edges.append(memberFullClassname + "-composition-" + fullClassName)

        ### REFERENCES

        if "include_uses_references" not in options or options["include_uses_references"]:
            uses = storage.get_class_uses(fullClassName)
            for usingFilePath, line, column, usingClassName, functionName in uses:
                usingClassName = self.__clearClassName(usingClassName)
                classes.append(usingClassName)
                edges.append(usingClassName + "-association-" + fullClassName)

        if "include_usedby_references" not in options or options["include_usedby_references"]:
            uses = storage.get_class_uses_by_class(fullClassName)
            for usingFilePath, line, column, userClassName, functionName in uses:
                userClassName = self.__clearClassName(userClassName)
                classes.append(userClassName)
                edges.append(fullClassName + "-association-" + userClassName)

        ### BUILD NODES FROM CLASSES

        for nodeFullClassName in list(set(classes)):
            nodeNamespace, nodeClassName = get_namespace_by_classname(nodeFullClassName)
            classType = storage.get_class_type(nodeNamespace, nodeClassName)
            nodes.append(nodeFullClassName + "@" + classType)

        return [nodes, edges]

    def __clearClassName(self, className):
        if className != None and len(className) > 0 and className[0] != "\\":
            className = "\\" + className
        return className
