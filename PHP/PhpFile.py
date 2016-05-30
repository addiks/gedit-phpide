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
from PHP.get_namespace_by_classname import get_namespace_by_classname
from PHP.phptokenparser import parse_php_tokens
import re

T_STRING   = token_num("T_STRING")
T_VARIABLE = token_num("T_VARIABLE")

docCommentRegex = re.compile("\\@([\\\\a-zA-Z_-]+)(([\$ \ta-zA-Z0-9\\\\_-]+)*)")
whitespaceRegex = re.compile("\s+")

class PhpFile:

    def __init__(self, code, plugin, storage):
        self.__plugin  = plugin
        self.__storage = storage
        self.update(code)

    def update(self, code):

        tokens, comments = token_get_all(code)

        blocks, namespace, use_statements, use_statement_index, constants = parse_php_tokens(tokens)

        self.__tokens              = tokens
        self.__comments            = comments
        self.__blocks              = blocks
        self.__namespace           = namespace
        self.__use_statements      = use_statements
        self.__use_statement_index = use_statement_index
        self.__constants           = constants

    def get_tokens(self):
        return self.__tokens

    def get_namespace(self):
        return self.__namespace

    def get_blocks(self):
        return self.__blocks

    def get_comments(self):
        return self.__comments

    def get_use_statements(self):
        return self.__use_statements

    def get_use_statement_index(self):
        return self.__use_statement_index

    def get_constants(self):
        return self.__constants

    ### GET DECLARATIONS

    def get_declared_position_by_position(self, line, column):
        declaration = self.get_declaration_by_position(line, column)

        filePath = None
        line     = None
        column   = None

        if declaration[0] == 'method':
            decType, methodName, className = declaration
            namespace, className = get_namespace_by_classname(className)
            filePath, line, column = self.__storage.get_method_position(namespace, className, methodName)
            while (line == None or column == None) and className != None:
                parentClass = self.__storage.get_class_parent(namespace, className)
                namespace, className = get_namespace_by_classname(parentClass)
                filePath, line, column = self.__storage.get_method_position(namespace, className, methodName)

        elif declaration[0] == 'function':
            namespace, functionName = get_namespace_by_classname(declaration[1])
            filePath, line, column = self.__storage.get_function_position(namespace, functionName)

        elif declaration[0] == 'member':
            decType, memberName, className = declaration
            namespace, className = get_namespace_by_classname(className)
            filePath, line, column = self.__storage.get_member_position(namespace, className, "$"+memberName)
            while (line == None or column == None) and className != None:
                parentClass = self.__storage.get_class_parent(namespace, className)
                namespace, className = get_namespace_by_classname(parentClass)
                filePath, line, column = self.__storage.get_member_position(namespace, className, "$"+memberName)

        elif declaration[0] == 'class-constant':
            decType, constantName, className = declaration
            namespace, className = get_namespace_by_classname(className)
            filePath, line, column = self.__storage.get_class_const_position(namespace, className, constantName)
            while (line == None or column == None) and className != None:
                parentClass = self.__storage.get_class_parent(namespace, className)
                namespace, className = get_namespace_by_classname(parentClass)
                filePath, line, column = self.__storage.get_class_const_position(namespace, className, constantName)

        elif declaration[0] == 'class':
            namespace, className = get_namespace_by_classname(declaration[1])
            filePath, line, column = self.__storage.get_class_position(namespace, className)

        elif declaration[0] == 'constant':
            constantName = declaration[1]
            filePath, line, column = self.__storage.get_constant_position(constantName)

        return (filePath, line, column, )

    def get_declaration_by_position(self, line, column):
        tokenIndex = self.get_token_index_by_position(line, column)
        return self.get_declaration_by_token_index(tokenIndex)

    def get_declaration_by_token_index(self, tokenIndex):
        tokens = self.__tokens
        declaration = [None, None, None]

        if tokens[tokenIndex][0] == T_STRING:
            if tokens[tokenIndex+1][1] == '(' and tokens[tokenIndex-1][1] != 'new':
                if tokens[tokenIndex-1][1] == '->':
                    className = self.get_type_by_token_index(tokenIndex-2)
                    declaration = ['method', tokens[tokenIndex][1], className]

                elif tokens[tokenIndex-1][1] == '::':
                    className = self.get_type_by_token_index(tokenIndex-2)
                    declaration = ['method', tokens[tokenIndex][1], className]

                else:
                    declaration = ['function', tokens[tokenIndex][1], None]

            elif tokens[tokenIndex-1][1] == '->':
                className = self.get_type_by_token_index(tokenIndex-2)
                declaration = ['member', tokens[tokenIndex][1], className]

            elif tokens[tokenIndex-1][1] == '::':
                className = self.get_type_by_token_index(tokenIndex-2)
                declaration = ['class-constant', tokens[tokenIndex][1], className]

            elif tokens[tokenIndex+1][1] in ['::', '->'] or tokens[tokenIndex-1][1] in ['new', 'class', 'interface', 'trait', 'extends', 'implements']:
                className = self.__map_classname_by_use_statements(tokens[tokenIndex][1], tokenIndex)
                declaration = ['class', className, None]

            else:
                declaration = ['constant', tokens[tokenIndex][1], None]

        elif tokens[tokenIndex][1] == ')':
            declaration = self.get_type_by_token_index(tokenIndex-1)
        return declaration

    ### TYPE DETERMINATION

    def get_member_type(self, memberName, className):
        typeId = None
        if memberName[0] != "$":
            memberName = "$" + memberName
        namespace, className = get_namespace_by_classname(className)
        visibility, is_static, filePath, line, column, docComment = self.__storage.get_member(namespace, className, memberName)
        if docComment != None and len(docComment)>0:
            typeId = self.__get_var_type_by_doccomment(docComment)
        typeId = self.__map_classname_by_use_statements(typeId)
        return typeId

    def get_method_return_type(self, methodName, className):
        typeId = None
        namespace, className = get_namespace_by_classname(className)
        visibility, is_static, filePath, line, column, docComment = self.__storage.get_method(namespace, className, methodName)
        if docComment != None and len(docComment)>0:
            typeId = self.__get_return_type_by_doccomment(docComment)
        if typeId == None:
            phpFileIndex = self.__plugin.get_php_fileindex(filePath)
            for block in phpFileIndex.__blocks:
                if len(block)>2 and block[2] == 'method' and block[4] == className and block[5] == methodName:
                    typeId = phpFileIndex.get_routine_return_type(block[0], block[1])
        typeId = self.__map_classname_by_use_statements(typeId)
        return typeId

    def get_function_return_type(self, functionName):
        namespace, functionName = get_namespace_by_classname(functionName)
        typeId = None
        filePath, line, column, docComment = self.__storage.get_function(namespace, functionName)
        if docComment!=None and len(docComment)>0:
            typeId = self.__get_return_type_by_doccomment(docComment)
        if typeId == None:# and filePath != None:
            phpFileIndex = self.__plugin.get_php_fileindex(filePath)
            for block in phpFileIndex.__blocks:
                if block[2] == 'function' and block[4] == className and block[5] == methodName:
                    typeId = phpFileIndex.get_routine_return_type(block[0], block[1])
        typeId = self.__map_classname_by_use_statements(typeId)
        return typeId

    def get_routine_return_type(self, beginTokenIndex, endTokenIndex):
        typeId = None
        tokens = self.__tokens;
        returnTypes = []
        tokenIndex = beginTokenIndex

        for tokenNum, phpcode, line, column in tokens[beginTokenIndex:endTokenIndex]:
            if phpcode == 'return':
                semicolonIndex = tokenIndex+1 # TODO: rework with syntax-tree (when we have a syntax-tree)
                for bTokenId, bPhpcode, bLine, bColumn in tokens[semicolonIndex:]:
                    if bPhpcode == ";":
                        break
                    semicolonIndex+=1
                returnedTypeId = self.get_type_by_token_index(semicolonIndex-1)
                if returnedTypeId != None:
                    returnTypes.append(returnedTypeId)
            tokenIndex+=1
        if len(returnTypes)>0:
            typeId = returnTypes[0]
        typeId = self.__map_classname_by_use_statements(typeId)
        return typeId

    def get_type_by_token_index(self, tokenIndex):
        tokens = self.__tokens
        typeId = None
        if tokens[tokenIndex][0] == T_STRING:
            if tokens[tokenIndex+1][1] == '(' and tokens[tokenIndex-1][1] != 'new':
                if tokens[tokenIndex-1][1] in ['->', '::']: # method-call
                    className = self.get_type_by_token_index(tokenIndex-2)
                    className = self.__map_classname_by_use_statements(className, tokenIndex)
                    if className != None:
                        typeId = self.get_method_return_type(tokens[tokenIndex][1], className)

                else: # function-call
                    typeId = self.get_function_return_type(tokens[tokenIndex][1])

            elif tokens[tokenIndex-1][1] == '->': # member-access
                className = self.get_type_by_token_index(tokenIndex-2)
                className = self.__map_classname_by_use_statements(className, tokenIndex)
                if className != None:
                    typeId = self.get_member_type(tokens[tokenIndex][1], className)

            elif tokens[tokenIndex+1][1] in ['::', '->'] or tokens[tokenIndex-1][1] in ['new', 'class', 'interface', 'trait', 'extends', 'implements']:
                typeId = tokens[tokenIndex][1] # classname

        elif tokens[tokenIndex][0] == T_VARIABLE:
            if tokens[tokenIndex-1][1] == '::': # static member-access
                className = self.get_type_by_token_index(tokenIndex-2)
                className = self.__map_classname_by_use_statements(className, tokenIndex)
                typeId = self.get_member_type(tokens[tokenIndex][1], className)

            else:
                typeId = self.get_type_by_variable(tokenIndex)

        elif tokens[tokenIndex][1] == ')':
            parenthesisIndex = tokenIndex-1
            parenthesisLevel = 1
            while parenthesisIndex>0:
                if tokens[parenthesisIndex][1]=='(':
                    if parenthesisLevel>1:
                        parenthesisLevel-=1
                    else:
                        break
                if tokens[parenthesisIndex][1]==')':
                    parenthesisLevel+=1
                parenthesisIndex-=1

            if tokens[parenthesisIndex-1][0] == T_STRING: # routine-call
                typeId = self.get_type_by_token_index(parenthesisIndex-1)

            else: # simple parenthesis
                typeId = self.get_type_by_token_index(tokenIndex-1)

        typeId = self.__map_classname_by_use_statements(typeId, tokenIndex)
        if typeId != None and typeId[0] != '\\':
            typeId = self.__namespace + "\\" + typeId
        return typeId

    def get_type_by_variable(self, tokenIndex):
        typeId = None
        tokens = self.__tokens
        needleVariableName = tokens[tokenIndex][1]

        if needleVariableName == '$this' and self.__is_in_method(tokenIndex):
            typeId = self.__get_class_is_in(tokenIndex)

        else:

            # find scope to search in
            scopeBeginIndex = 0
            scopeEndIndex = len(tokens)-1
            scopeBlock = None
            for block in self.__blocks:
                if len(block)>2 and block[0] < tokenIndex:
                    if block[2] in ['function', 'method']:
                        scopeBeginIndex = block[0]
                        scopeEndIndex   = block[1]
                        scopeBlock      = block

            # try to find declaration in comments ( // @var $foo \Bar)
            for tokenId, phpcode, line, column in self.__comments:
                if( line >= tokens[scopeBeginIndex][2] and line <= tokens[scopeEndIndex][2] ):
                    annotations = self.__get_annotations_by_doccomment(phpcode)
                    if "var" in annotations:
                        for variable, varTypeId, in annotations['var']:
                            if varTypeId[0] == '$':
                                tempVar   = variable
                                variable  = varTypeId
                                varTypeId = tempVar
                            if variable == needleVariableName:
                                typeId = varTypeId

            # try to resolve by assignment ($foo = new \Bar();)
            if typeId == None:
                scopeTokenId = scopeBeginIndex
                for tokenId, phpcode, line, column in tokens[scopeBeginIndex:scopeEndIndex]:
                    if tokenId == T_VARIABLE and phpcode == needleVariableName and tokens[scopeTokenId+1][1]=='=':
                        semicolonIndex = scopeTokenId+2 # TODO: rework with syntax-tree (when we have a syntax-tree)
                        for bTokenId, bPhpcode, bLine, bColumn in tokens[semicolonIndex:]:
                            if bPhpcode == ";":
                                break
                            semicolonIndex+=1
                        typeId = self.get_type_by_token_index(semicolonIndex-1)
                    scopeTokenId+=1

            # try to find in routine-arguments
            if typeId == None:
                routineNameTokenIndex = scopeBlock[3]
                if tokens[routineNameTokenIndex+1][1] == '(':
                    tokenIndex = routineNameTokenIndex+2
                    while True:
                        argumentTypeId = None
                        if tokens[tokenIndex][0] == T_STRING:
                            argumentTypeId = tokens[tokenIndex][1]
                            tokenIndex += 1
                        if tokens[tokenIndex][0] == T_VARIABLE:
                            if tokens[tokenIndex][1] == needleVariableName:
                                typeId = argumentTypeId
                                break
                            tokenIndex += 1
                        if tokens[tokenIndex][1] == ',':
                            tokenIndex += 1
                        else:
                            break

        typeId = self.__map_classname_by_use_statements(typeId, tokenIndex)
        return typeId

    def get_variables_in_scope(self, tokenIndex):
        variables = []
        tokens = self.__tokens

        scopeBeginIndex = 0
        scopeEndIndex = len(tokens)-1
        scopeBlock = None
        for block in self.__blocks:
            if len(block)>2 and block[0] < tokenIndex:
                if block[2] in ['function', 'method']:
                    scopeBeginIndex = block[0]
                    scopeEndIndex   = block[1]
                    scopeBlock      = block

        for token in tokens[scopeBeginIndex:scopeEndIndex]:
            if token[0] == T_VARIABLE:
                variables.append(token[1])

        return variables

    ### HELPER

    def get_token_index_by_position(self, line, column):
        tokenIndex = 0
        for token in self.__tokens:
            if token[2] > line or (token[2] == line and token[3] >= column):
                return tokenIndex-1
            tokenIndex += 1

    def __map_classname_by_use_statements(self, className, tokenIndex=None):

        if className in ['self', 'static', 'parent'] and tokenIndex != None:
            if className in ['self', 'static']:
                className = self.__get_class_is_in(tokenIndex)

            elif className == 'parent':
                className = self.__get_class_is_in(tokenIndex)
                namespace, className = get_namespace_by_classname(className)
                className = self.__storage.get_class_parent(namespace, className)

        elif className in self.__use_statements:
            className = self.__use_statements[className]

        return className

    def __get_return_type_by_doccomment(self, docComment):
        typeId = None
        annotations = self.__get_annotations_by_doccomment(docComment)
        if "return" in annotations and len(annotations["return"][0])>0:
            returnType = annotations["return"][0][0]
            if returnType not in ['void', 'bool', 'boolean', 'int', 'integer', 'float', 'double', 'string', 'array']:
                typeId = self.__map_classname_by_use_statements(returnType)
        return typeId

    def __get_var_type_by_doccomment(self, docComment):
        typeId = None
        annotations = self.__get_annotations_by_doccomment(docComment)
        if "var" in annotations and len(annotations["var"][0])>0:
            returnType = annotations["var"][0][0]
            if returnType not in ['void', 'bool', 'boolean', 'int', 'integer', 'float', 'double', 'string', 'array']:
                typeId = self.__map_classname_by_use_statements(returnType)
        return typeId

    def __is_in_method(self, tokenIndex):
        for block in self.__blocks:
            if len(block)>2 and block[2] == 'method' and block[0] < tokenIndex and block[1] > tokenIndex:
                return True
        return False

    def __get_class_is_in(self, tokenIndex):
        for block in self.__blocks:
            if block[2] == 'class' and block[0] < tokenIndex and block[1] > tokenIndex:
                return block[4]
        return None

    def __get_annotations_by_doccomment(self, docComment):
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

