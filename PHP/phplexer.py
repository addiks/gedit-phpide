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

keywords = [
    'abstract', 'array', 'as', 'break', 'case', 
    'catch', 'class', 'clone', 'const', 'continue',
    'declare', 'default', 'do', 'echo', 'else',
    'elseif', 'empty', 'enddeclare', 'endfor', 
    'endforeach', 'endif', 'endswitch', 'endwhile',
    'eval', 'extends', 'final', 'for', 'foreach',
    'global', 'goto', 'if', 'implements', 'include',
    'include_once', 'instanceof', 'interface', 
    'isset', 'list', 'and', 'or', 'xor', 'new',
    'print', 'private', 'public', 'protected', 
    'require', 'require_once', 'return', 'static',
    'switch', 'throw', 'try', 'unset', 'use', 'var',
    'while'
]

tokens = collections.OrderedDict()
tokens['T_AND_EQUAL']                = "&="
tokens['T_ARRAY_CAST']               = "\\(array\\)"
#tokens['T_BAD_CHARACTER']            = "" ASCII < 32 TODO!
tokens['T_BOOLEAN_AND']              = "&&"
tokens['T_BOOLEAN_OR']               = "\\|\\|"
tokens['T_BOOL_CAST']                = "\\(bool(ean)?\\)"
#tokens['T_CHARACTER']                = "" ???
tokens['T_CLASS_C']                  = "__CLASS__"
tokens['T_CLOSE_TAG']                = "(\\?|\\%)\\>"
tokens['T_DOC_COMMENT']              = "\\/\\*\\*.*?\\*\\/"
tokens['T_COMMENT']                  = "(//[^\n]*?(?=\n|\\?\\>|\\%\\>)|\\#[^\n]*?(?=\n|\\?\\>|\\%\\>))|/\\*.*?\\*/"
tokens['T_CONCAT_EQUAL']             = "\\.="
tokens['T_CONSTANT_ENCAPSED_STRING'] = "\"(?:[^\"\\\\]|\\\\.)*\"|\'(?:[^\'\\\\]|\\\\.)*\'"
tokens['T_EXECUTE_STRING']           = "\`(?:[^\`\\\\]|\\\\.)*\`"
#tokens['T_CURLY_OPEN']               = "\\{\\$"
tokens['T_DEC']                      = "--"
tokens['T_DIR']                      = "__DIR__"
tokens['T_DIV_EQUAL']                = "/="
tokens['T_DNUMBER']                  = "\\d+\\.\\d+"
#tokens['T_DOLLAR_OPEN_CURLY_BRACES'] = "\\$\\{"
tokens['T_DOUBLE_ARROW']             = "=>"
tokens['T_DOUBLE_CAST']              = "\\((real|double|float)\\)"
tokens['T_DOUBLE_COLON']             = "::"
#tokens['T_ENCAPSED_AND_WHITESPACE']  = "\\'.*?\\'" ???
tokens['T_EXIT']                     = "(exit|die)"
tokens['T_FILE']                     = "__FILE__"
tokens['T_FUNCTION']                 = "c?function(?!\\w)"
tokens['T_FUNC_C']                   = "__FUNCTION__"
tokens['T_HALT_COMPILER']            = "__halt_compiler(\\w+)"
tokens['T_HEREDOC']                  = "<<<\s*[\'\"]?(.*)[\'\"]?\\n.*?\\n\\1;?"
tokens['T_INC']                      = "\\+\\+"
tokens['T_INLINE_HTML']              = "\\0WILL#NEVER~PARSE"
tokens['T_INT_CAST']                 = "\\(int(eger)?\\)"
tokens['T_ISSET']                    = "isset(?!\\w)"
tokens['T_IS_IDENTICAL']             = "==="
tokens['T_IS_EQUAL']                 = "=="
tokens['T_IS_GREATER_OR_EQUAL']      = ">="
tokens['T_IS_NOT_IDENTICAL']         = "!=="
tokens['T_IS_NOT_EQUAL']             = "(\\!=|<>)"
tokens['T_IS_SMALLER_OR_EQUAL']      = "<="
tokens['T_LINE']                     = "__LINE__"
tokens['T_LNUMBER']                  = "(\d+|0x[0-9a-f]+)"
tokens['T_METHOD_C']                 = "__METHOD__"
tokens['T_MINUS_EQUAL']              = "-="
tokens['T_MOD_EQUAL']                = "\\%="
tokens['T_MUL_EQUAL']                = "\\*="
tokens['T_NS_C']                     = "__NAMESPACE__"
tokens['T_NS_SEPERATOR']             = "\\\\"
#tokens['T_NUM_STRING']               = "" ???
tokens['T_OBJECT_CAST']              = "\\(object\\)"
tokens['T_OBJECT_OPERATOR']          = "->"
#tokens['T_OLD_FUNCTION']             = "" ???
tokens['T_OPEN_TAG']                 = "<(\\?php|\\%|\\?|\\?=)"
tokens['T_OPEN_TAG_WITH_ECHO']       = "<(\\?|\\%)="
tokens['T_OR_EQUAL']                 = "\\|="
tokens['T_PAAMAYIM_NEKUDOTAYIM']     = "::"
tokens['T_PLUS_EQUAL']               = "\\+="
tokens['T_SL']                       = "<<"
tokens['T_SL_EQUAL']                 = "<<="
tokens['T_SR']                       = ">>"
tokens['T_SR_EQUAL']                 = ">>="
tokens['T_STRING_CAST']              = "\\(string\\)"
#tokens['T_STRING_VARNAME']           = "" ??? (something to do with '${somevar}')
tokens['T_SINGLE_CHAR']              = "\0WILL#NEVER~PARSE"
tokens['T_UNSET_CAST']               = "\\(unset\\)"
tokens['T_VARIABLE']                 = "\\$+[a-zA-Z_][a-zA-Z0-9_]*"
tokens['T_WHITESPACE']               = "\\s+"
tokens['T_XOR_EQUAL']                = "\\^="
#tokens['T_STRING']                   = "[a-zA-Z_\\\\][a-zA-Z0-9_\\\\]*"
tokens['T_STRING']                   = "[a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff\\\\]*"

# compile all regexes
regexes = collections.OrderedDict()
for name, pattern in tokens.items():
    try:
        regexes[name] = re.compile(pattern, re.MULTILINE | re.DOTALL)
    except:
        print("Invalid pattern '"+pattern+"' for "+name)
        raise

if hasattr(regexes, "iteritems"):
    regexesIterator = regexes.iteritems()
else:
    regexesIterator = regexes.items()

# special regex to find opening tag when in T_INLINE_HTML
regexOpenTag = re.compile("\\<(\\?php|\\%|\\?)")

_token_name_cache = {}

# get the name for given token-number
def token_name(num):
    if num in _token_name_cache:
        return _token_name_cache[num]
    tokenNum = -1
    for keyword in keywords:
        tokenNum += 1
        tokenId = 'T_'+keyword.upper()
        if tokenId == num:
            _token_name_cache[num] = tokenId
    for tokenId in regexes:
        tokenNum += 1
        if tokenNum == num:
            _token_name_cache[num] = tokenId
            return tokenId
    raise Exception("No token-name for #"+num+" found!")

_token_num_cache = {}

# get the number for given token-name
def token_num(needleTokenId):
    if needleTokenId in _token_num_cache:
        return _token_num_cache[needleTokenId]
    tokenNum = -1
    for keyword in keywords:
        tokenNum += 1
        tokenId = 'T_'+keyword.upper()
        if tokenId == needleTokenId:
            _token_num_cache[needleTokenId] = tokenNum
    for tokenId in regexes:
        tokenNum += 1
        if tokenId == needleTokenId:
            _token_num_cache[needleTokenId] = tokenNum
            return tokenNum
    raise Exception("No token-num for '"+str(needleTokenId)+"' found!")

# actual php-lexer, gets token-set for given php-code
def token_get_all(code):

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

    row = 1
    col = 1
    tokens = []
    comments = []
    match = True
    inPhp = False # everything before <? or <% is T_INLINE_HTML
    while len(code) > 0:
        lenCode = len(code)
        if inPhp:
            tokenNum = -1
            found = False
            for keyword in keywords:
                tokenNum += 1
                firstChar = code[len(keyword):len(keyword)+1]
                if code[:len(keyword)] == keyword and not (firstChar.isalnum() or firstChar == '_'):
                    found = True
                    match = keyword
                    tokens.append([tokenNum, keyword, row, col])
                    code = code[len(keyword):]
                    col += len(keyword)
            if found == False:
                for tokenId in regexes:
                    regex = regexes[tokenId]
                    tokenNum += 1
                    match = regex.match(code)
                    if match != None:
                        found = True
                        tokenText = match.group()
                        code = code[len(tokenText):]
                        if tokenId == 'T_COMMENT':
                            tokens.append([tokenNum, tokenText, row, col])
                            comments.append([tokenNum, tokenText, row, col])
                        elif tokenId != 'T_WHITESPACE':
                            tokens.append([tokenNum, tokenText, row, col])
                        rowDelta = tokenText.count("\n")
                        row += rowDelta
                        if rowDelta > 0:
                            col = len(tokenText) - tokenText.rfind("\n")
                        else:
                            col += len(tokenText)
                        if tokenId == "T_CLOSE_TAG":
                            inPhp = False
                        break
            if code[0:1] in specialChars and not found:
                tokens.append([token_num('T_SINGLE_CHAR'), code[0:1], row, col])
                code = code[1:]
                col += 1
                continue
        else:
            match = regexOpenTag.search(code)

            if match == None:
                tokens.append([token_num("T_INLINE_HTML"), code, row, col])
                break # breaks the while

            elif match.start() > 0:
                tokenText = code[0:match.start()]
                code = code[match.start():]
                tokens.append([token_num("T_INLINE_HTML"), tokenText, row, col])
                rowDelta = tokenText.count("\n")
                row += rowDelta
                if rowDelta > 0:
                    col = len(tokenText) - tokenText.rfind("\n")
                else:
                    col += len(tokenText)
            inPhp = True

            if match.start() == 0:
                continue

        if len(code) == lenCode or match == None:
            mesgPart = "Cannot lex code"
            codePart = " (code: \""+code[:10]+"\")"
            linePart = " at line " + str(row)
            colmPart = " in column " + str(col)
            toknPart = ""
            toknPart = "\n Tokens so far: " + repr(tokens)
            raise Exception(mesgPart+linePart+colmPart+codePart+toknPart)

    return (tokens, comments, )

