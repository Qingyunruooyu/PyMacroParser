# -*- coding: utf-8 -*-
"""
Created on Sun Dec 30 19:31:30 2018

@author: Jonathan_Lewis
"""
import logging
logging.basicConfig(level=logging.DEBUG, filename='output.log',)


# 全局变量，清除注释用，对能干扰清除注释的东西，进行判断
g_DictCommentSyms = {'"': '"',"'":"'", '/*': '*/', '//': '\n'}
# 全局变量，清除#后面的空格、tab
g_DictSharpSyms   = {'"': '"', "'":"'",'/*': '*/', '//': '\n','#':None}
# 全局变量，将tab换成空格用
g_DictTabSyms     = {'"': '"', "'":"'",'/*': '*/', '//': '\n','\t':None}
# 全局变量，合并CPP中"abc"  "def"这种字符串用（它的值是"abcdef"）
g_DictStringSyms  = {'"': '"', 'L"': '"'}
# 全局变量，解析CPP中的聚合用
g_SetBracedSyms = {'{', '}', ',', '"',"'"}

class PyMacroParser(object):
    __slots__=("m_strCppContent", "m_dictPreDefined", "m_strMacros", "m_dictCppDefined", "m_strPreDefine")

    def __init__(self):
        self.m_strCppContent = ""  # cpp文件的内容
        self.m_dictPreDefined = {}  # 预定义的内容
        self.m_strMacros = ('#ifdef', '#ifndef', '#else', '#endif', '#define', '#undef')#支持的宏
        self.m_dictCppDefined = {}  # cpp宏的原始内容（未解析成python），只在dumpDict的时候解析出来，保证dump出来的CPP原汁原味
        self.m_strPreDefine = ""  # 预定义的命令

    def load(self, f):
        with open(f, 'r') as ifCppFile:
            self.m_strCppContent = PyMacroParser.rpTabWithSpace(PyMacroParser.rmBlanksAfterSharps(PyMacroParser.rmCommentsInCFile(ifCppFile.read())))
            logging.debug(self.m_strCppContent)

    def preDefine(self, s):
        self.m_strPreDefine = s.replace(' ','')

    # 写入self.m_dictCppDefined,输出给用户时解析，但是当dump成cpp时，不解析
    def dumpDict(self, bParse = True):
        #预定义
        self.__clearDicts()
        if not self.m_strPreDefine == '':
            listMacros = self.m_strPreDefine.split(';')
            for m in [strMacro for strMacro in listMacros if strMacro != '']:
                self.m_dictPreDefined[m] = None
        #后续定义
        self.__solveCppSentences(0, len(self.m_strCppContent))
        dictMerged = {}
        if bParse: # 默认，外界调用dumpDict的时候，解析成python
            for k,v in self.m_dictCppDefined.iteritems():
                dictMerged[k] = self.__parseStr2Val(v)
        else: # dump函数调用dumpDict的时候，直接复制
            dictMerged = self.m_dictCppDefined.copy()
        dictMerged.update(self.m_dictPreDefined)
        logging.debug(dictMerged)
        return dictMerged

    # dump之前必须重新dumpDict一次，避免之前未写入self.m_dictCppDefined或者写入后又preDefine了
    def dump(self, f):
        dictAll = self.dumpDict(False)
        with open (f,'w') as ofCppFile:
            for k,v in dictAll.iteritems():
                if v == None:
                    ofCppFile.write('#define ' + k + '\n')
                else:
                    ofCppFile.write(r'#define ' + k + ' ' + v + '\n')

    #清理字典
    def __clearDicts(self):
        self.m_dictPreDefined.clear()
        self.m_dictCppDefined.clear()

    #寻找当前位置的合法#else
    def __findItsElsePos(self, fromPos):
        while(fromPos < len(self.m_strCppContent)):
            result = PyMacroParser.get1stSymPos(self.m_strCppContent,self.m_strMacros,fromPos)
            if result[1] == '#ifdef' or result[1] == '#ifndef':
                itsEndifPos = self.__findItsEndIfPos(self.m_strCppContent.find('\n', result[0]))
                fromPos = self.m_strCppContent.find('\n',itsEndifPos)
            elif result[1] == '#define' or result [1] == '#undef':
                fromPos = self.m_strCppContent.find('\n',result[0])
            elif result[1] == '#else':
                return result[0]
            else: #这种情况理论上不会出现，除非CPP文件本身有问题
                return -1
        return -1

    # 寻找当前位置的合法#endif
    def __findItsEndIfPos(self, fromPos):
        while(fromPos < len(self.m_strCppContent)):
            result = PyMacroParser.get1stSymPos(self.m_strCppContent,self.m_strMacros,fromPos)
            if result[1] == '#ifdef' or result[1] == '#ifndef':
                itsEndifPos = self.__findItsEndIfPos(self.m_strCppContent.find('\n', result[0]))
                fromPos = self.m_strCppContent.find('\n',itsEndifPos)
            elif result[1] == '#define' or result [1] == '#undef' or result[1] == '#else':
                fromPos = self.m_strCppContent.find('\n',result[0])
            elif result[1] == '#endif':
                return result[0]
            else: #这种情况理论上不会出现，除非CPP文件本身有问题
                return -1
        return -1

    # 判断s有没有被定义
    def __hasDefined(self, s):
        return s in self.m_dictPreDefined or s in self.m_dictCppDefined

    # 解析cpp字符串，将之变成对应的python值
    @staticmethod
    def __parseStr2Val(s):
        #None
        if s == None:
            return None

        bFoundSemicolon = False# 解决#define后面带分号的猫饼
        while (s[-1] == ';' if not bFoundSemicolon else s[-1] == ';' or s[-1] == ' '):
            s = s[:-1]#找到
        s = s.lstrip().rstrip()
        # 布尔型
        if s == 'false' or s == 'true':
            return False if s[0] == 'f' else True

        # 数字型
        elif ord('0') <= ord(s[0]) <= ord('9') or s[0] == '+' \
                or s[0] == '-' or s[0] == '.':
            return PyMacroParser.__solveDigit(s)

        # 字符型
        elif s[0] == "'":
            return PyMacroParser.__solveChar(s)

        # 字符串型
        elif s[0] == 'L' or s[0] == '"':
            return PyMacroParser.__solveString(s)

        # 聚合类型
        elif s[0] == '{':
            return PyMacroParser.__solveBracedInitializer(s[1:s.rfind('}')])
        return s


    # 将数字型字符串解析成对应的数字
    @staticmethod
    def __solveDigit(s):
        s = s.lower()#转成小写
        setForFloat = {'f','.','e'} #浮点型专有的符号
        # if '0x' in s:
        #     return PyMacroParser.__solveInt(s)
        for sym in setForFloat:
            if s.find(sym) != -1 and '0x' not in s: #十六进制也有e和f，所以要排除
                return PyMacroParser.__solveFloat(s)
        return PyMacroParser.__solveInt(s)


    # 将浮点型字符串解析成对应的数字
    @staticmethod
    def __solveFloat(s):
        setSuffix = {'f','l'}
        for sfx in setSuffix:
            if s.find(sfx) != -1:
                return float(s[:-len(sfx)])
        return float(s)

    # 将整型字符串解析成对应的数字
    @staticmethod
    def __solveInt(s):
        tupleSuffix = ('ui64','ull','lul','llu','i64','ul','lu','ll','u','l') #整型的后缀
        nBase = 10
        if s.find('0x') != -1:
            nBase = 16
        else:
            for d in s:
                if  ord('0') <= ord(d) <= ord('9'): # 第一个数字
                    if d == '0':
                        nBase = 8
                    break
        for sfx in tupleSuffix:
            if s.find(sfx) != -1:
                return int(s[:-len(sfx)], base = nBase)
        return int(s, base = nBase)

    # 将字符型字符串解析成对应的数字
    @staticmethod
    def __solveChar(s):
        sum = 0
        s = PyMacroParser.__solveString(s[1:-1].replace('\\"','"').replace('"','\\"')) #单引号里面可以有不转义的双引号
        if(type(s) == type(u'')):
            raise ValueError("说好的字符常量没有宽字符的呢")
        if type(s) == type('') and len(s) > 4:
            raise ValueError("字符常量中的字符太多")
        for d in s:
            sum = sum * 256 + ord(d)
        return sum

    # 将 cpp型字符串解析成python型字符串
    @staticmethod
    def __solveString(s): #考虑无效转义符
        dictEscapedChar = {'\\a': '\a', '\\b': '\b', '\\f': '\f', '\\n': '\n','\\r': '\r', '\\t': '\t',
                           '\\v': '\v', '\\\\': '\\', "\\'": "'", '\\"': '"'} #'\\0': '\0' 算在八进制内

        # 将字符串拼接起来 （比如CPP中#define s "abb" L"cdd" 这种情况，要拼合成 L"abbcdd"）
        bUnicodeFlag = False
        fromPos = 0
        # 先判断是宽字符还是窄字符
        while (0 <= fromPos < len(s)):
            result = PyMacroParser.get1stSymPos(s, g_DictStringSyms, fromPos)
            fromPos = result[0]
            if result[1] == None:
                break
            if result[1] == 'L"':
                bUnicodeFlag = True
                break
            if result[1] == '"':
                fromPos = PyMacroParser.__findItsCloseQuotePos(s, fromPos + 1) + 1  # 找到引号配对的后引号
        if bUnicodeFlag is True: #问题，我在命令行搞没有问题，在这里乱码了
            s = s.decode('gbk')

        fromPos = 0
        # 删掉""和 L指示符
        while(0 <= fromPos < len (s)):
            result = PyMacroParser.get1stSymPos(s,g_DictStringSyms,fromPos)
            fromPos = result[0]
            if result[1] == None:
                break
            if result[1] == 'L"':
                endQuotePos = PyMacroParser.__findItsCloseQuotePos(s, fromPos + 2)# 找到引号配对的后引号
                nextStrPos = PyMacroParser.get1stSymPos(s, g_DictStringSyms, endQuotePos + 1)[0]  # 下 一条字符串的起始位置
                if nextStrPos == -1:  # 去掉这对L""
                    s = s[:fromPos] + s[fromPos + 2:endQuotePos]
                else:
                    s = s[:fromPos] + s[fromPos + 2:endQuotePos] + s[nextStrPos:]
            if result[1] == '"':
                endQuotePos = PyMacroParser.__findItsCloseQuotePos(s, fromPos + 1)# 找到引号配对的后引号
                nextStrPos = PyMacroParser.get1stSymPos(s,g_DictStringSyms,endQuotePos+1)[0] # 下 一条字符串的起始位置
                if nextStrPos == -1:# 去掉这对双引号
                    s = s[:fromPos] + s[fromPos + 1:endQuotePos]
                else:
                    s = s[:fromPos] + s[fromPos+1:endQuotePos] + s[nextStrPos:]

        # 转义字符
        fromPos = 0
        while(fromPos < len(s)):
            backSlashPos = s.find('\\',fromPos)
            if 0 <= backSlashPos < len(s) - 1: #第一个到倒数第二个字符出现反斜杠，判断转义字符是否有效
                chEscaped = s[backSlashPos:backSlashPos + 2]
                if chEscaped in dictEscapedChar: # 转换
                    s = s[:backSlashPos] + dictEscapedChar[chEscaped] + s[backSlashPos + 2:]
                elif chEscaped == '\\x' or chEscaped == '\\u': #十六进制字符
                    setHex = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'}
                    hexFromPos = backSlashPos + 2 # 16进制开始的位置
                    hexToPos = hexFromPos
                    hexMaxLen = 4 if bUnicodeFlag or chEscaped == '\\u' else 2#宽字符可以有\xhhhh，窄字符\xhh，\uxxxx必须4位
                    while hexToPos < len(s) and s[hexToPos] in setHex:
                        hexMaxLen = hexMaxLen - 1
                        hexToPos = hexToPos + 1
                    if hexMaxLen < 0:
                        raise ValueError("十六进制字符长度太大！")
                    if hexToPos == hexFromPos:
                        raise ValueError("无效的十六进制字符！")
                    hexNum = '0x' + s[hexFromPos: hexToPos] #实际上没必要加前缀
                    hexChar = unichr(int(hexNum,16)) if bUnicodeFlag or chEscaped == '\\u' else chr(int(hexNum, 16))
                    s = s[:backSlashPos] + hexChar + s[hexToPos:]
                elif ord('0') <= ord(chEscaped[1]) <= ord('7'):  #  8进制字符
                    octFromPos = backSlashPos + 1
                    octToPos = octFromPos
                    octMaxLen = 3  #宽窄字符八进制都是三位数
                    while octToPos < len(s) and ord('0') <= ord(s[octToPos]) <= ord('7') and octMaxLen > 0:
                        octMaxLen = octMaxLen - 1
                        octToPos = octToPos + 1
                    octNum = '0' + s[octFromPos: octToPos] #实际上没必要加前缀
                    octChar = unichr(int(octNum, 8)) if bUnicodeFlag else chr(int(octNum, 8))
                    s = s[:backSlashPos] + octChar + s[octToPos:]
                else: # 无效转义，删掉反斜杠
                    s = s[:backSlashPos] + s[backSlashPos + 1:]
                fromPos = backSlashPos + 1
            else:
                break
        return s

    # 将{}聚合类型解析成tuple类型
    @staticmethod
    def __solveBracedInitializer(s):
        fromPos = 0
        elementFromPos = 0
        listBraces = []
        while(fromPos < len(s)):
            result = PyMacroParser.get1stSymPos(s, g_SetBracedSyms, fromPos)
            if result[0] == -1:
                if not s[elementFromPos:len(s)].isspace():
                    listBraces.append(s[elementFromPos:len(s)])
                break
            if result[1] == '{': #元素还是聚合
                closeBracedPos = PyMacroParser.__findItsCloseBracedPos(s, result[0] + 1)  # 找到他合法的}符号
                if closeBracedPos == -1:
                    raise ValueError("聚合的格式错误！")  #理论上这个异常不会出现
                listBraces.append(s[result[0]: closeBracedPos + 1])
                commaPos = s.find(',',closeBracedPos)
                if commaPos != -1: #找下一个逗号，也就是聚合的分隔符，这里可能存在问题
                    fromPos = commaPos + 1
                    elementFromPos = fromPos
                else:
                    break

            elif result[1] == ',':
                listBraces.append(s[elementFromPos:result[0]]) #截取起始到逗号的部分作为聚合的一个元素
                fromPos = result[0] + 1
                elementFromPos = fromPos

            elif result[1] == '"' or result[1] == "'":
                fromPos = PyMacroParser.__findItsCloseQuotePos(s, result[0] + 1, result[1]) + 1
                if(fromPos >= len(s)):
                    listBraces.append(s[elementFromPos:fromPos])
            else:
                raise ValueError("聚合的格式错误！")
        return tuple([PyMacroParser.__parseStr2Val(brace) for brace in listBraces])

    #找到聚合类型对应的}符号
    @staticmethod
    def __findItsCloseBracedPos(s, fromPos):
        while(fromPos < len(s)):
            result = PyMacroParser.get1stSymPos(s, g_SetBracedSyms, fromPos)
            if result[1] == '}': # 如果就是}，那就完事了
                return result[0]
            elif result[1] == '{': # 如果是{，那就得递归地找这个{的结束符，从这个结束符后面开始找
                closeBracedPos = PyMacroParser.__findItsCloseBracedPos(s, result[0] + 1)
                fromPos = closeBracedPos + 1
            elif result[1] == ',':
                fromPos = result[0] + 1
            elif result[1] == '"' or result[1] == "'":
                closeQuotePos = PyMacroParser.__findItsCloseQuotePos(s,result[0]+1,result[1])
                fromPos = closeQuotePos + 1
            else:
                raise ValueError("聚合的格式错误！(寻找}的过程中)") #理论上不会出现，除非CPP本身错误
        raise ValueError("聚合的格式错误！(寻找}的过程中)")

    #找到字符串合法的闭合"符号，因为字符串本身也可能有"符号  问题：单引号里面的双引号也不需要转义，这个还没写
    @staticmethod
    def __findItsCloseQuotePos(s, fromPos,cQuote = '"'):
        setQuote = {'"',"'"}
        if not cQuote in setQuote:
            raise ValueError(cQuote)
        itsCloseQuotePos = s.find(cQuote, fromPos)
        # 小于0表示没找到，等于0表示前面不可能有/符号，所以可以排除
        while (itsCloseQuotePos > 0 and s[itsCloseQuotePos - 1] == '\\'):
            bEscape = True #判断这个反斜杠自己是不是被转义的
            # 奇数个的话，反斜杠不被转义，引号是一个普通字符，偶数个的话，反斜杠被转义，引号是字符串引导符号
            backSlashPos = itsCloseQuotePos - 2
            while (backSlashPos >= 0 and s[backSlashPos] == '\\'):
                bEscape = not bEscape
                backSlashPos = backSlashPos -1
            if(bEscape):
                itsCloseQuotePos = s.find(cQuote, itsCloseQuotePos + 1)
            else:
                break
        return itsCloseQuotePos


    #将python值转换为cpp字符串
    @staticmethod
    def __parseVal2Str(s):

        return s


    #递归地解析CPP宏
    def __solveCppSentences(self, fromPos, toPos): #真正执行解析的函数（递归）
        while(0 <= fromPos < toPos):
            result = PyMacroParser.get1stSymPos(self.m_strCppContent,self.m_strMacros,fromPos)
            newLinePos = self.m_strCppContent.find('\n',result[0])
            if newLinePos == -1: #最后一行且没有换行符
                newLinePos = len(self.m_strCppContent)
            strDef = self.m_strCppContent[result[0]:newLinePos].rstrip() # #define等语句
            listDef = [s for s in strDef.split(' ') if not s == ''] # 各个元素
            if len(listDef) >= 3:
                listDef = listDef[:2]
                pos = strDef.find(listDef[0]) + len(result[1])
                pos = strDef.find(listDef[1], pos) + len(listDef[1])
                while strDef[pos] == ' ' or strDef[pos] == '\t':
                    pos = pos + 1
                listDef.append(strDef[pos:])

            if result[1] == '#ifndef':
                elsePos = self.__findItsElsePos(newLinePos)  # 找else
                endIfPos = self.__findItsEndIfPos(newLinePos) # 找endif
                if self.__hasDefined(listDef[1]): #如果已经定义了
                    if not elsePos == -1:  #如果有else，就解析else
                        self.__solveCppSentences(self.m_strCppContent.find('\n', elsePos) + 1, endIfPos - 1)
                else: #如果没定义
                    if not elsePos == -1:  #如果有else，就以else为结束符
                        self.__solveCppSentences(newLinePos, elsePos - 1)
                    else:
                        self.__solveCppSentences(newLinePos, endIfPos - 1)
                fromPos = self.m_strCppContent.find('\n',endIfPos)
            elif result[1] == '#ifdef': #跟上面的情况相反
                elsePos = self.__findItsElsePos(newLinePos) # 找else
                endIfPos = self.__findItsEndIfPos(newLinePos) # 找endif
                if not self.__hasDefined(listDef[1]): #如果没定义
                    if not elsePos == -1: #就要找else
                        self.__solveCppSentences(self.m_strCppContent.find('\n', elsePos) + 1, endIfPos - 1)
                else: #如果定义了
                    if not elsePos == -1: #如果有else，就以else为结束符
                        self.__solveCppSentences(newLinePos, elsePos - 1)
                    else:
                        self.__solveCppSentences(newLinePos, endIfPos - 1)
                fromPos = self.m_strCppContent.find('\n', endIfPos)
            elif result[1] == '#define':  #干正事
                if len(listDef) >= 3:
                    self.m_dictCppDefined[listDef[1]] = ' '.join(listDef[2:])
                elif len(listDef) == 2:
                    self.m_dictCppDefined[listDef[1]] = None
                else:
                    raise ValueError("#define格式错误:"+strDef)
                fromPos = newLinePos + 1
            elif result[1] == '#undef': #搞破坏
                if listDef[1] in self.m_dictCppDefined:
                    self.m_dictCppDefined.pop(listDef[1])
                elif listDef[1] in self.m_dictPreDefined:
                    self.m_dictPreDefined.pop(listDef[1])
                fromPos = newLinePos + 1
            elif result[1] == '#else': #读完一个分支，这个时候的else是不用管的，直接跳到endif后面
                itsEndifPos = self.__findItsEndIfPos(newLinePos + 1)
                fromPos = self.m_strCppContent.find('\n',itsEndifPos)
            elif result[1] == '#endif':
                fromPos = newLinePos + 1
            elif result[1] == None:
                return
    # 判断symbols的key中，最先出现的符号是哪个，并返回其所在位置以及该符号
    @staticmethod
    def get1stSymPos(s,symbols, fromPos = 0):
        listPos = [] #位置,符号
        for b in symbols:
            pos = s.find(b, fromPos) if b != '"'  and b != "'"\
                else PyMacroParser.__findItsCloseQuotePos(s, fromPos,b)# 特别注意字符串里面的"
            listPos.append((pos,b)) #插入位置以及结束符号
        minIndex = -1 #最小位置在listPos中的索引
        index = 0 #索引
        while index < len(listPos):
            pos = listPos[index][0] #位置
            if minIndex < 0 and pos >= 0: #第一个非负位置
                minIndex = index
            if 0 <= pos < listPos[minIndex][0]: #后面出现的更靠前的位置
                minIndex = index
            index = index+1
        if minIndex == -1: #没找到
            return (-1,None)
        else:
            return (listPos[minIndex])


    # 去掉cpp文件的注释，替换成一个空格
    @staticmethod
    def rmCommentsInCFile(s):
        if not isinstance(s, str):
            raise TypeError(s)
        fromPos = 0
        while(fromPos < len(s)):
            result = PyMacroParser.get1stSymPos(s, g_DictCommentSyms, fromPos)
            logging.debug(result)
            if result[0] == -1: #没有符号了
                return s
            else:
                # 问题，如果字符串里面有"这个符号怎么办（已修正）
                endPos = s.find(g_DictCommentSyms[result[1]], result[0] + len(result[1])) if (result[1] != '"')  \
                and (result[1] != "'") else \
                    PyMacroParser.__findItsCloseQuotePos(s, result[0] + len(result[1]), result[1])
                # while s[endPos - 1] == '\\':
                #     endPos = s.find(g_DictCommentSyms[result[1]], endPos + len(result[1]))
                if result[1] == '//': # 单行注释
                    if endPos == -1: #没有换行符也可以
                        endPos = len(s)
                    s = s.replace(s[result[0]:endPos],' ',1)
                    fromPos = result[0]
                elif result[1] == '/*': #区块注释
                    if endPos == -1: #没有结束符就报错
                        raise ValueError("块状注释未闭合")
                    s = s.replace(s[result[0]:endPos+2],' ',1)
                    fromPos = result[0]
                else: #字符串
                    if endPos == -1: #没有结束符就报错
                        raise ValueError("符号未闭合")
                    fromPos = endPos + len(g_DictCommentSyms[result[1]])
        return s


    # 去掉#后面的空格，注意不要影响注释、字符串里面的#
    @staticmethod
    def rmBlanksAfterSharps(s):
        if not isinstance(s, str):
            raise TypeError(s)
        fromPos = 0
        while(fromPos < len(s)):
            result = PyMacroParser.get1stSymPos(s, g_DictSharpSyms, fromPos)
            logging.debug(result)
            if result[0] == -1: #没有符号了
                return s
            elif result[1] == '#':
                blankEndPos = result[0]+1
                while(blankEndPos < len(s) and s[blankEndPos] == ' 'or s[blankEndPos] == '\t'):
                    blankEndPos = blankEndPos+1
                if(blankEndPos > result[0] + 1):
                    s = s[:result[0]+1] + s[blankEndPos:]
                fromPos = blankEndPos
            else:
                endPos = s.find(g_DictSharpSyms[result[1]], result[0] + len(result[1])) if result[1] != '"'  \
                    and result[1] != "'" else \
                    PyMacroParser.__findItsCloseQuotePos(s, result[0] + len(result[1]),result[1])
                if endPos == -1:  # 没有结束符直接结束
                    endPos = len(s)
                fromPos = endPos + len(g_DictSharpSyms[result[1]])
        return s


    # 将字符串以外的tab换成空格
    @staticmethod
    def rpTabWithSpace(s):
        if not isinstance(s, str):
            raise TypeError(s)
        fromPos = 0
        while(fromPos < len(s)):
            result = PyMacroParser.get1stSymPos(s, g_DictTabSyms, fromPos)
            logging.debug(result)
            if result[0] == -1: #没有符号了
                return s
            elif result[1] == '\t':
                tabEndPos = result[0]+1
                while(tabEndPos < len(s) and s[tabEndPos] == '\t'):
                    tabEndPos = tabEndPos+1
                s = s[:result[0]] + ' '+ s[tabEndPos:]
                fromPos = tabEndPos
            else:
                endPos = s.find(g_DictTabSyms[result[1]], result[0] + len(result[1])) if result[1] != '"'  \
                    and result[1] != "'"\
                    else PyMacroParser.__findItsCloseQuotePos(s, result[0] + len(result[1]), result[1])
                if endPos == -1:  # 没有结束符直接结束
                    endPos = len(s)
                fromPos = endPos + len(g_DictTabSyms[result[1]])
        return s



if __name__ == '__main__':
    #python 测试代码：
    a1 = PyMacroParser()
    a2 = PyMacroParser()
    a1.load("e.cpp")
    filename = "b.cpp"
    a1.dump(filename) #没有预定义宏的情况下，dump cpp
    a2.load(filename)
    print a2.dumpDict() == a1.dumpDict()
    #a1.preDefine("MC1;MC2") #指定预定义宏，再dump
    print a1.dumpDict()
    a1.dump("c.cpp")
