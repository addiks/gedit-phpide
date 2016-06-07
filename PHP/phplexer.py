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
import collections
import string

tokens = collections.OrderedDict()
tokens['T_AND_EQUAL']                = "&=" #
tokens['T_ARRAY_CAST']               = "\\(array\\)" #
#tokens['T_BAD_CHARACTER']            = "" ASCII < 32 TODO!
tokens['T_BOOLEAN_AND']              = "&&" #
tokens['T_BOOLEAN_OR']               = "\\|\\|" #
tokens['T_BOOL_CAST']                = "\\(bool(ean)?\\)" #
#tokens['T_CHARACTER']                = "" ???
tokens['T_CLASS_C']                  = "__CLASS__" #
tokens['T_CLOSE_TAG']                = "(\\?|\\%)\\>" #
tokens['T_DOC_COMMENT']              = "\\/\\*\\*.*?\\*\\/" #
tokens['T_COMMENT']                  = "(//[^\n]*?(?=\n|\\?\\>|\\%\\>)|\\#[^\n]*?(?=\n|\\?\\>|\\%\\>))|/\\*.*?\\*/" #
tokens['T_CONCAT_EQUAL']             = "\\.=" #
tokens['T_CONSTANT_ENCAPSED_STRING'] = "\"(?:[^\"\\\\]|\\\\.)*\"|\'(?:[^\'\\\\]|\\\\.)*\'" #
tokens['T_EXECUTE_STRING']           = "\`(?:[^\`\\\\]|\\\\.)*\`"
#tokens['T_CURLY_OPEN']               = "\\{\\$"
tokens['T_DEC']                      = "--" #
tokens['T_DIR']                      = "__DIR__" #
tokens['T_DIV_EQUAL']                = "/=" #
tokens['T_DNUMBER']                  = "\\d+\\.\\d+" #
#tokens['T_DOLLAR_OPEN_CURLY_BRACES'] = "\\$\\{"
tokens['T_DOUBLE_ARROW']             = "=>" #
tokens['T_DOUBLE_CAST']              = "\\((real|double|float)\\)" #
tokens['T_DOUBLE_COLON']             = "::" #
#tokens['T_ENCAPSED_AND_WHITESPACE']  = "\\'.*?\\'" ???
tokens['T_EXIT']                     = "(exit|die)" #
tokens['T_FILE']                     = "__FILE__" #
tokens['T_FUNCTION']                 = "c?function(?!\\w)" #
tokens['T_FUNC_C']                   = "__FUNCTION__" #
tokens['T_HALT_COMPILER']            = "__halt_compiler(\\w+)" #
tokens['T_HEREDOC']                  = "<<<\s*[\'\"]?(.*)[\'\"]?\\n.*?\\n\\1;?" #
tokens['T_INC']                      = "\\+\\+" #
tokens['T_INLINE_HTML']              = "\\0WILL#NEVER~PARSE" #
tokens['T_INT_CAST']                 = "\\(int(eger)?\\)" #
tokens['T_ISSET']                    = "isset(?!\\w)" #
tokens['T_IS_IDENTICAL']             = "===" #
tokens['T_IS_EQUAL']                 = "==" #
tokens['T_IS_GREATER_OR_EQUAL']      = ">=" #
tokens['T_IS_NOT_IDENTICAL']         = "!==" #
tokens['T_IS_NOT_EQUAL']             = "(\\!=|<>)" #
tokens['T_IS_SMALLER_OR_EQUAL']      = "<=" #
tokens['T_LINE']                     = "__LINE__" #
tokens['T_LNUMBER']                  = "(\d+|0x[0-9a-f]+)"
tokens['T_METHOD_C']                 = "__METHOD__" #
tokens['T_MINUS_EQUAL']              = "-=" #
tokens['T_MOD_EQUAL']                = "\\%=" #
tokens['T_MUL_EQUAL']                = "\\*=" #
tokens['T_NS_C']                     = "__NAMESPACE__" #
tokens['T_NS_SEPERATOR']             = "\\\\" #
#tokens['T_NUM_STRING']               = "" ???
tokens['T_OBJECT_CAST']              = "\\(object\\)" #
tokens['T_OBJECT_OPERATOR']          = "->" #
#tokens['T_OLD_FUNCTION']             = "" ???
tokens['T_OPEN_TAG']                 = "<(\\?php|\\%|\\?|\\?=)" #
tokens['T_OR_EQUAL']                 = "\\|=" #
tokens['T_PAAMAYIM_NEKUDOTAYIM']     = "::" #
tokens['T_PHP_START']                = "\0WILL#NEVER~PARSE" #
tokens['T_PLUS_EQUAL']               = "\\+=" #
tokens['T_SL']                       = "<<" #
tokens['T_SL_EQUAL']                 = "<<=" #
tokens['T_SR']                       = ">>" #
tokens['T_SR_EQUAL']                 = ">>=" #
tokens['T_STRING_CAST']              = "\\(string\\)" #
#tokens['T_STRING_VARNAME']           = "" ??? (something to do with '${somevar}')
tokens['T_SINGLE_CHAR']              = "\0WILL#NEVER~PARSE" #
tokens['T_UNSET_CAST']               = "\\(unset\\)" #
tokens['T_VARIABLE']                 = "\\$+[a-zA-Z_][a-zA-Z0-9_]*" #
tokens['T_WHITESPACE']               = "\\s+" #
tokens['T_XOR_EQUAL']                = "\\^=" #
#tokens['T_STRING']                   = "[a-zA-Z_\\\\][a-zA-Z0-9_\\\\]*"
tokens['T_STRING']                   = "[a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff\\\\]*" #

_token_name_cache = {}
_token_num_cache = {}

# get the name for given token-number
def token_name(num):
    result = None
    if num in _token_name_cache:
        result = _token_name_cache[num]
    else:
        tokenNum = -1
        for keyword in keywords:
            tokenNum += 1
            tokenId = 'T_'+keyword.upper()
            if tokenId == num:
                _token_name_cache[num] = tokenId
                result = tokenId
        for tokenId in tokens:
            tokenNum += 1
            if tokenNum == num:
                _token_name_cache[num] = tokenId
                result = tokenId
        if result == None:
            raise Exception("No token-name for #"+str(num)+" found!")
        _token_name_cache[num] = result
        _token_num_cache[result] = num
    return result

# get the number for given token-name
def token_num(needleTokenId):
    result = None
    if needleTokenId in _token_num_cache:
        result = _token_num_cache[needleTokenId]
    else:
        tokenNum = -1
        for keyword in keywords:
            tokenNum += 1
            tokenId = 'T_'+keyword.upper()
            if tokenId == needleTokenId:
                _token_num_cache[needleTokenId] = tokenNum
                result = tokenNum
        for tokenId in tokens:
            tokenNum += 1
            if tokenId == needleTokenId:
                _token_num_cache[needleTokenId] = tokenNum
                result = tokenNum
        if result == None:
            raise Exception("No token-num for '"+str(needleTokenId)+"' found!")
        _token_name_cache[result] = needleTokenId
        _token_num_cache[needleTokenId] = result
    return result

keywords = [
    'abstract', 'array', 'as', 'break', 'case', 
    'catch', 'class', 'clone', 'const', 'continue',
    'declare', 'default', 'do', 'echo', 'else',
    'elseif', 'empty', 'enddeclare', 'endfor', 
    'endforeach', 'endif', 'endswitch', 'endwhile',
    'eval', 'extends', 'final', 'for', 'foreach', 'function',
    'global', 'goto', 'if', 'implements', 'include',
    'include_once', 'instanceof', 'interface', 'isset',
    'isset', 'list', 'and', 'or', 'xor', 'new',
    'print', 'private', 'public', 'protected', 
    'require', 'require_once', 'return', 'static',
    'switch', 'throw', 'try', 'unset', 'use', 'var',
    'while'
]

specialChars = [
    '!==', '===',

    '<=', '>=', '!=', '==', 
    '+=', '-=', '*=', '/=',
    '^=', '|=', '%=', 

    '<', '>', '+', '-', '*', '/', '%', 
    '(', ')', '[', ']', '{', '}',
    ',', '.', ';', ':', '?', 
    '^', '~', '&', '|',

    '=', '!', '@', '$'
]

operators = {
    "&=":  token_num('T_AND_EQUAL'),
    "&&":  token_num('T_BOOLEAN_AND'),
    "||":  token_num('T_BOOLEAN_OR'),
    "/=":  token_num('T_DIV_EQUAL'),
    "=>":  token_num('T_DOUBLE_ARROW'),
    "==":  token_num('T_IS_EQUAL'),
    ">=":  token_num('T_IS_GREATER_OR_EQUAL'),
    "!=":  token_num('T_IS_NOT_EQUAL'),
    "<>":  token_num('T_IS_NOT_EQUAL'),
    "<=":  token_num('T_IS_SMALLER_OR_EQUAL'),
    "-=":  token_num('T_MINUS_EQUAL'),
    "%=":  token_num('T_MOD_EQUAL'),
    "*=":  token_num('T_MUL_EQUAL'),
    "<<":  token_num('T_SL'),
    ">>":  token_num('T_SR'),
    "::":  token_num('T_PAAMAYIM_NEKUDOTAYIM'),
    "->":  token_num('T_OBJECT_OPERATOR'),
    "^=":  token_num('T_XOR_EQUAL'),
    "++":  token_num('T_INC'),
    "--":  token_num('T_DEC'),
    ".=":  token_num('T_CONCAT_EQUAL'),
    "<<=": token_num('T_SL_EQUAL'),
    ">>=": token_num('T_SR_EQUAL'),
    "===": token_num('T_IS_IDENTICAL'),
    "!==": token_num('T_IS_NOT_IDENTICAL'),
}

directTokenMap = {
    '(unset)':         token_num('T_UNSET_CAST'),
    '(bool)':          token_num('T_BOOL_CAST'),
    '(boolean)':       token_num('T_BOOL_CAST'),
    '(array)':         token_num('T_ARRAY_CAST'),
    '(real)':          token_num('T_DOUBLE_CAST'),
    '(double)':        token_num('T_DOUBLE_CAST'),
    '(float)':         token_num('T_DOUBLE_CAST'),
    '(object)':        token_num('T_OBJECT_CAST'),
    '(int)':           token_num('T_INT_CAST'),
    '(integer)':       token_num('T_INT_CAST'),
    '(string)':        token_num('T_STRING_CAST'),
    'exit':            token_num('T_EXIT'),
    'die':             token_num('T_EXIT'),
    '__FILE__':        token_num('T_FILE'),
    '__FUNCTION__':    token_num('T_FUNC_C'),
    '__halt_compiler': token_num('T_HALT_COMPILER'),
    '__LINE__':        token_num('T_LINE'),
    '__METHOD__':      token_num('T_METHOD_C'),
    '__NAMESPACE__':   token_num('T_NS_C'),
    '__CLASS__':       token_num('T_CLASS_C'),
    '__DIR__':         token_num('T_DIR'),
    '\\':              token_num('T_NS_SEPERATOR'),
}

T_INLINE_HTML              = token_num('T_INLINE_HTML')
T_SINGLE_CHAR              = token_num('T_SINGLE_CHAR')
T_CONSTANT_ENCAPSED_STRING = token_num('T_CONSTANT_ENCAPSED_STRING')
T_COMMENT                  = token_num('T_COMMENT')
T_PHP_START                = token_num('T_PHP_START')
T_STRING                   = token_num('T_STRING')
T_VARIABLE                 = token_num('T_VARIABLE')
T_DNUMBER                  = token_num('T_DNUMBER')
T_CLOSE_TAG                = token_num('T_CLOSE_TAG')
T_CLOSE_TAG                = token_num('T_CLOSE_TAG')
T_HEREDOC                  = token_num('T_HEREDOC')
T_DOC_COMMENT              = token_num('T_DOC_COMMENT')

# new experimental _fast_ PHP lexer
def token_get_all(code, filePath):
    tokens = []
    comments = []

    row = 1
    col = 1

    isInPhp = False
    while len(code) > 0:
        if isInPhp:
            if code[0] in [' ', '\t', '\r']:
                col += 1
                code = code[1:]

            elif code[0] == '\n':
                col = 1
                row += 1
                code = code[1:]

            elif code[0] in '_\\' + string.ascii_letters:
                tokenText = code[0]
                index = 1
                while code[index] in '_\\' + string.ascii_letters + string.digits:
                    tokenText += code[index]
                    index += 1
                code, tokens, row, col = process_token(code, tokens, T_STRING, tokenText, row, col)

            elif code[0] in ['"', "'"]:
                tokenText = code[0]
                index = 1
                while index < len(code) and code[0] != code[index]:
                    tokenText += code[index]
                    if code[index] == '\\':
                        tokenText += code[index+1:index+2]
                        index += 1
                    index += 1
                if index < len(code):
                    tokenText += code[index]
                code, tokens, row, col = process_token(code, tokens, T_CONSTANT_ENCAPSED_STRING, tokenText, row, col)

            elif code[0:3] == '/**':
                endPos = code.find('*/') + 2
                tokenText = code[0:endPos]
                code, tokens, row, col = process_token(code, tokens, T_DOC_COMMENT, tokenText, row, col)
                comments.append([T_COMMENT, tokenText, row, col])

            elif code[0:2] == '/*':
                endPos = code.find('*/') + 2
                tokenText = code[0:endPos]
                code, tokens, row, col = process_token(code, tokens, T_COMMENT, tokenText, row, col)
                comments.append([T_COMMENT, tokenText, row, col])

            elif code[0:2] == '//' or code[0:1] == '#':
                endPos = code.find('\n')
                if endPos > 0:
                    tokenText = code[0:endPos + 1]
                    code, tokens, row, col = process_token(code, tokens, T_COMMENT, tokenText, row, col)
                    comments.append([T_COMMENT, tokenText, row, col])
                else:
                    comments.append([T_COMMENT, code, row, col])
                    code = ""

            elif code[0:3] == '<<<':
                tokenText = code[0:3]
                heredocName = ""
                index = 3
                while code[index] != "\n":
                    heredocName += code[index]
                    index += 1
                tokenText += heredocName
                heredocName = heredocName.strip()
                if heredocName[0] in ['"', "'"]:
                    heredocName = heredocName[1:len(heredocName)-2]
                while code[index:index+len(heredocName)+1] != '\n' + heredocName:
                    tokenText += code[index]
                    index += 1
                tokenText += '\n' + heredocName
                code, tokens, row, col = process_token(code, tokens, T_HEREDOC, tokenText, row, col)

            elif code[0:2] in operators:
                tokenText = code[0:2]
                tokenNum = operators[tokenText]
                code, tokens, row, col = process_token(code, tokens, tokenNum, tokenText, row, col)

            elif code[0:3] in operators:
                tokenText = code[0:2]
                tokenNum = operators[tokenText]
                code, tokens, row, col = process_token(code, tokens, tokenNum, tokenText, row, col)

            elif code[0:1] == '$' and code[1:2] in '_' + string.ascii_letters + string.digits:
                tokenText = code[0:2]
                index = 2
                while code[index] in '_' + string.ascii_letters + string.digits:
                    tokenText += code[index]
                    index += 1
                code, tokens, row, col = process_token(code, tokens, T_VARIABLE, tokenText, row, col)

            elif code[0] in string.digits:
                tokenText = code[0]
                index = 1
                while code[index] in string.digits + '.':
                    tokenText += code[index]
                    index += 1
                code, tokens, row, col = process_token(code, tokens, T_DNUMBER, tokenText, row, col)

            elif code[0:2] == '?>':
                code, tokens, row, col = process_token(code, tokens, T_CLOSE_TAG, code[0:2], row, col)
                isInPhp = False

            elif code[0] in specialChars:
                code, tokens, row, col = process_token(code, tokens, T_SINGLE_CHAR, code[0:1], row, col)

            else:
                isKeyword = False
                keyword = None
                for keyword in keywords:
                    if code[0:len(keyword)] == keyword:
                        isKeyword = True
                        break

                if isKeyword:
                    tokenNum = token_num('T_' + keyword.upper())
                    code, tokens, row, col = process_token(code, tokens, tokenNum, keyword, row, col)
                else:
                    isDirectToken = False
                    directToken = None
                    for directToken in directTokenMap:
                        if code[0:len(directToken)] == directToken:
                            isDirectToken = True
                            break

                    if isDirectToken:
                        tokenNum = directTokenMap[directToken]
                        code, tokens, row, col = process_token(code, tokens, tokenNum, directToken, row, col)
                    else:
                        code = code[1:]

        else: # not in php-code
            beginPosition = code.find('<?')
            if beginPosition >= 0:
                if beginPosition > 0:
                    tokenText = code[0:beginPosition]
                    code, tokens, row, col = process_token(code, tokens, T_INLINE_HTML, tokenText, row, col)

                tokenText = '<?'
                if code[0:5] == '<?php':
                    tokenText = '<?php'
                elif code[0:3] == '<?=':
                    tokenText = '<?='
                else:
                    tokenText = '<?'

                code, tokens, row, col = process_token(code, tokens, T_PHP_START, tokenText, row, col)
                isInPhp = True

            else:
                tokens.append([T_INLINE_HTML, code, row, col])
                code = ""

    return (tokens, comments, )

def process_token(code, tokens, tokenNum, tokenText, row, col):
    code = code[len(tokenText):]
    tokens.append([tokenNum, tokenText, row, col])
    row, col = increment_row_and_colum(tokenText, row, col)
    return [code, tokens, row, col]


def increment_row_and_colum(tokenText, row, col):
    rowDelta = tokenText.count("\n")
    row += rowDelta
    if rowDelta > 0:
        col = len(tokenText) - tokenText.rfind("\n")
    else:
        col += len(tokenText)
    return [row, col]





