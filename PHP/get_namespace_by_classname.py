
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

