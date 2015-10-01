from storage.sqlite3 import Sqlite3Storage
from phpfile import PhpFile

class Plugin:
    
    def __init__(self, storage):
        self.__phpfiles = {}
        self.__storage = storage

    def get_php_fileindex(self, filePath):
        if filePath not in self.__phpfiles:
            self.__phpfiles[filePath] = PhpFile(filePath, self, self.__storage)
        return self.__phpfiles[filePath]

storage = Sqlite3Storage("/usr/workspace/b24_magento_de_ce/.git/addiks.phpindex.sqlite3")

plugin = Plugin(storage)

fileIndex = PhpFile("/usr/workspace/b24_magento_de_ce/app/code/local/Brille24/FriendsForFriends/controllers/IndexController.php", plugin, storage)
print(repr(fileIndex.get_declared_position_by_position(27, 14))) 

fileIndex = PhpFile("/usr/workspace/b24_magento_de_ce/app/code/core/Mage/Core/Controller/Varien/Action.php", plugin, storage)
print(repr(fileIndex.get_declared_position_by_position(676, 34))) 

fileIndex = PhpFile("/usr/workspace/b24_magento_de_ce/app/code/core/Mage/Core/Controller/Response/Http.php", plugin, storage)
print(repr(fileIndex.get_declared_position_by_position(107, 18))) 
