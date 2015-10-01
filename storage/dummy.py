
class DummyStorage:
    
    def __init__(self):
        pass

    def getmtime(self, filePath):
        pass

    def add_file(self, filePath, namespace, mtime):
        pass

    def add_class(self, filePath, namespace, className, classType, parentName, interfaces, isFinal, isAbstract, docComment, line, column):
        pass

    def add_class_constant(self, filePath, namespace, className, name, value, line, column):
        pass

    def add_method(self, filePath, namespace, className, methodName, keywords, doccomment, line, column):
        pass

    def add_function(self, filePath, namespace, functionName, line, column):
        pass

    def get_member(self, namespace, className, memberName):
        pass

    def get_class_position(self, namespace, className):
        pass

    def get_class_const_position(self, namespace, className, constantName):
        pass

    def get_method_position(self, namespace, className, methodName):
        pass

    def get_function_position(self, namespace, functionName):
        pass

    def get_constant_position(self, constantName):
        pass

    def get_member_position(self, namespace, className, memberName):
        pass

    def sync(self):
        pass

    def removeFile(self, filePath):
        pass

    def empty(self):
        pass


