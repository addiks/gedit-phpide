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
import PHP.phplexer
import operator

T_STRING      = token_num('T_STRING')
T_VARIABLE    = token_num('T_VARIABLE')
T_DOC_COMMENT = token_num('T_DOC_COMMENT')
T_COMMENT     = token_num('T_COMMENT')

def parse_php_tokens(tokens):

    blocks = []
    blockStack = []
    classes = []
    classconstants = []
    variables = []
    constants = []
    functions = []
    namespace = '\\'
    use_statements = {}
    use_statement_index = None
    uses = []

    # find blocks, classes and functions(/methods)
    tokenIndex = 0
    for token in tokens:

        if token[1] == 'namespace':
            if tokens[tokenIndex+1][0] == T_STRING:
                namespace = tokens[tokenIndex+1][1]
                if use_statement_index == None:
                    use_statement_index = tokenIndex+2;

        if token[1] == 'use' and len(blockStack) <= 0:
            if tokens[tokenIndex+1][0] == T_STRING:
                use_statement = tokens[tokenIndex+1][1]
                if use_statement[-1] != '\\':
                    use_statement = '\\' + use_statement
                use_parts = use_statement.split("\\")
                if tokens[tokenIndex+2][1] == 'as' and tokens[tokenIndex+3][0] == T_STRING:
                    use_alias = tokens[tokenIndex+3][1]
                else:
                    use_alias = use_parts[-1]
                use_statements[use_alias] = use_statement
                use_statement_index = tokenIndex+2;

        if token[1] in ['class', 'interface', 'trait']:
            classes.append(tokenIndex)

        if token[1] == 'function':
            functions.append(tokenIndex)

        if token[1] == 'const':
            classconstants.append(tokenIndex)

        if token[0] == T_VARIABLE:
            variables.append(tokenIndex)

        if token[1] == 'define':
            constants.append(tokenIndex)

        if token[1] == ";" and len(functions + classes) > 0: # for abstract methods
            blocks.append([tokenIndex, tokenIndex])

        if token[1] == "{":
            blockStack.append(tokenIndex)
        if token[1] == '}':
            if len(blockStack) == 0:
                raise Exception("Invalid '}' (in '"+str(token[2])+'|'+str(token[3])+"'#"+str(tokenIndex)+")")
            beginIndex = blockStack.pop()
            blocks.append([beginIndex, tokenIndex])

        if token[0] == T_STRING and token[1] not in PHP.phplexer.keywords and token[1] != "namespace" and tokens[tokenIndex-1][1] != "namespace":
            isOnClass = (tokens[tokenIndex-1][1] in ['->', '::'])
            isRoutine = (tokens[tokenIndex+1][1] == '(')
            isType = (tokens[tokenIndex+1][0] == T_VARIABLE) or tokens[tokenIndex-1][1] in ['use', 'extends', 'implements', 'new', 'instanceof']

            typeRef = "unknown"
            if isOnClass:
                if isRoutine:
                    typeRef = "method"
                else:
                    typeRef = "member"
            else:
                if isRoutine:
                    typeRef = "function"
                elif isType:
                    typeRef = "class"
                else:
                    typeRef = "constant"

            tokenText = token[1]
            if typeRef == "class" and '\\' in tokenText:
                tokenText = tokenText.split('\\')
                tokenText = tokenText[-1]

            if tokens[-2][1] not in ['$this', 'self'] and tokenText not in ['true', 'false', 'null']:
                uses.append([tokenIndex, token[2], token[3], tokenText, typeRef])
        tokenIndex += 1

    blocks.sort(key=operator.itemgetter(0))

    # assign classes to codeblocks
    for classIndex in classes:
        classBlockIndex = 0
        for block in blocks:
            if block[0] > classIndex and len(block)<=2:
                block.append('class')    #2
                block.append(classIndex) #3
                break
            classBlockIndex += 1

    # assign functions/methods to codeblocks
    for functionIndex in functions:
        functionBlockIndex = 0;
        for block in blocks:
            if block[0] > functionIndex and len(block)<=2:
                isMethod = False
                for parentBlock in reversed(blocks):
                    if parentBlock[0] < block[0] and parentBlock[1] > block[1]:
                        if len(parentBlock)>2 and parentBlock[2] == 'class':
                            isMethod = True
                        break
                if isMethod:
                    block.append('method')   #2
                else:
                    block.append('function') #2
                block.append(functionIndex)  #3
                break
            functionBlockIndex += 1

    # extract members from variables

    members = []
    for variableIndex in variables:
        isInClass  = False
        isInMethod = False
        for block in blocks:
            if len(block) > 2:
                if block[2] == 'class'  and variableIndex > block[0] and variableIndex < block[1]:
                    isInClass = True
                    isInMethod = False

                if block[2] == 'method' and variableIndex > block[3] and variableIndex < block[1] and isInClass:
                    isInMethod = True
        if isInClass and not isInMethod and tokens[variableIndex-1][1] in ['var', 'protected', 'public', 'private', 'static', 'abstract']:
            members.append(variableIndex)


    # enrich classes/functions

    for block in blocks:
        if len(block) > 2:

            if block[2] == 'class':
                tokenIndex  = block[3]
                classType   = tokens[tokenIndex][1]
                tokenIndex -= 1
                keywords = []
                while tokens[tokenIndex][1] in ['abstract', 'final']:
                    keywords.append(tokens[tokenIndex][0])
                    tokenIndex -= 1
                isAbstract = 'abstract' in keywords
                isFinal    = 'final'    in keywords

                docComment = ""
                if tokens[tokenIndex][0] in [T_DOC_COMMENT, T_COMMENT]:
                    docComment = tokens[tokenIndex][1]

                tokenIndex  = block[3]
                tokenIndex += 1
                className = tokens[tokenIndex][1]
                block[3] = tokenIndex

                parentClass = None
                if tokens[tokenIndex+1][1] == 'extends':
                    tokenIndex += 2
                    parentClass = tokens[tokenIndex][1]

                interfaces = []
                if tokens[tokenIndex+1][1] == 'implements':
                    tokenIndex += 2
                    doEnd = False
                    while not doEnd:
                        interfaces.append(tokens[tokenIndex][1])
                        if tokens[tokenIndex+1][1] == ',':
                            tokenIndex += 2
                        else:
                            doEnd = True

                thisclassMembers = []
                for memberIndex in members:
                    if memberIndex > block[0] and memberIndex < block[1]:
                        thisclassMembers.append(memberIndex)

                thisclassConstants = []
                for constantIndex in classconstants:
                    if constantIndex > block[0] and constantIndex < block[1]:
                        thisclassConstants.append(constantIndex)

                block.append(className)             # 4
                block.append(parentClass)           # 5
                block.append(interfaces)            # 6
                block.append(isAbstract)            # 7
                block.append(isFinal)               # 8
                block.append(classType)             # 9
                block.append(thisclassMembers)      # 10
                block.append(thisclassConstants)    # 11
                block.append(docComment)            # 12

            if block[2] == 'function':
                tokenIndex  = block[3]
                tokenIndex += 1

                functionName = None
                if tokens[tokenIndex][0] == T_STRING:
                    functionName = tokens[tokenIndex][1]

                block[3] = tokenIndex

                docComment = ""
                if tokens[tokenIndex-1][0] in [T_DOC_COMMENT, T_COMMENT]:
                    docComment = tokens[tokenIndex-1][1]

                arguments = []
                tokenIndex += 1
                if tokens[tokenIndex][1] == '(':
                    while True:
                        argument = []
                        tokenIndex += 1
                        if tokens[tokenIndex][1] == ')':
                            break
                        if tokens[tokenIndex][0] in [T_STRING]:
                            argument.append(tokens[tokenIndex][1])
                            tokenIndex += 1
                        else:
                            argument.append(None)
                        if tokens[tokenIndex][0] == T_VARIABLE:
                            argument.append(tokens[tokenIndex][1])
                            tokenIndex += 1
                        if tokens[tokenIndex][1] == '=':
                            defaultValue = ""
                            while tokens[tokenIndex][1] not in [',', ')']:
                                tokenIndex += 1
                                if tokens[tokenIndex][1] != ')':
                                    defaultValue += tokens[tokenIndex][1]
                                if tokens[tokenIndex][1] == '(':
                                    tokenIndex += 1
                                    defaultValue += tokens[tokenIndex][1] # ')'
                                    tokenIndex += 1
                            argument.append(defaultValue)
                        arguments.append(argument)
                        if tokens[tokenIndex][1] != ',':
                            break

                block.append(functionName)  # 4
                block.append(docComment)    # 5
                block.append(arguments)     # 6

    # enrich methods (needs enriched classes, thats why it's in own iteration)

    for block in blocks:
        if len(block) > 2:

            if block[2] == 'method':
                tokenIndex = block[3]

                keywords = []
                tokenIndex -= 1
                while tokens[tokenIndex][1] in ['static', 'abstract', 'final', 'public', 'protected', 'private']:
                    keywords.append(tokens[tokenIndex][1])
                    tokenIndex -= 1

                docComment = ""
                if tokens[tokenIndex][0] in [T_DOC_COMMENT, T_COMMENT]:
                    docComment = tokens[tokenIndex][1]

                tokenIndex = block[3]
                tokenIndex += 1
                methodName = tokens[tokenIndex][1]
                block[3] = tokenIndex

                arguments = []
                tokenIndex += 1
                if tokens[tokenIndex][1] == '(':
                    while True:
                        argument = []
                        tokenIndex += 1
                        if tokens[tokenIndex][1] == ')':
                            break
                        if tokens[tokenIndex][0] in [T_STRING]:
                            argument.append(tokens[tokenIndex][1])
                            tokenIndex += 1
                        else:
                            argument.append(None)
                        if tokens[tokenIndex][0] == T_VARIABLE:
                            argument.append(tokens[tokenIndex][1])
                            tokenIndex += 1
                        if tokens[tokenIndex][1] == '=':
                            defaultValue = ""
                            while tokens[tokenIndex][1] not in [',', ')']:
                                tokenIndex += 1
                                if tokens[tokenIndex][1] != ')':
                                    defaultValue += tokens[tokenIndex][1]
                                if tokens[tokenIndex][1] == '(':
                                    tokenIndex += 1
                                    defaultValue += tokens[tokenIndex][1] # ')'
                                    tokenIndex += 1
                            argument.append(defaultValue)
                        arguments.append(argument)
                        if tokens[tokenIndex][1] != ',':
                            break

                className = ""
                for parentBlock in reversed(blocks):
                    if parentBlock[0] < block[0] and parentBlock[1] > block[1]:
                        className = parentBlock[4]
                        break
                block.append(className)     # 4
                block.append(methodName)    # 5
                block.append(keywords)      # 6
                block.append(docComment)    # 7
                block.append(arguments)     # 8

    # assign uses to blocks

    blockIndex = 0
    for block in blocks:
        blockUses = []
        for tokenIndex, line, column, tokenText, typeRef in uses:
            blockBegin = block[0]
            if len(block) > 2 and block[2] in ['method', 'function']:
                blockBegin = block[3]
            if tokenIndex > blockBegin and tokenIndex < block[1]:
                blockUses.append([line, column, tokenText, typeRef])
        blocks[blockIndex].append(blockUses)
        blockIndex += 1

    return (blocks, namespace, use_statements, use_statement_index, constants)



