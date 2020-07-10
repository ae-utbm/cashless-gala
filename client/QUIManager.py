import os

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon
from Console import *
#copy is mandatory because of the init of path
#indeed ... A= [X,Y]
#           B=A 
# A and B are now sharing the same memory !
import copy
class QUIManagerSingleton(type(QObject)):
    _instance = {}

    def __call__(cls):
        if cls not in cls._instance:
            cls._instance[cls] = super(QUIManagerSingleton, cls).__call__()
        return cls._instance[cls]


class QUIManager(QObject, metaclass=QUIManagerSingleton):
    def __init__(self):
        self.theme = "default"
        self.themeRelPath =["ressources","themes",self.theme]
        self.iconRelPath = copy.deepcopy (self.themeRelPath)
        self.windowIconRelPath = copy.deepcopy(self.themeRelPath)

        self.iconRelPath.append("ui-icons")
        self.windowIconRelPath.append("window-icons")

    def getIcon(self, iconName):
        """Return the QIcon according to 'iconName'. None if no icon is found"""
        iconPath = self.__relPath(self.iconRelPath)
        fileList = os.listdir(iconPath)
        icon = None
        for file in fileList:
            name = file.split('.')[0] # [name, extention]
            if name == iconName:
                try:
                    icon = QIcon(iconPath+file)
                except:
                    printE("Unable to load the ressource {}".format(file))
            
        return icon

    def getWindowIcon(self, iconName):
        """Return the QIcon according to 'iconName'. None if no icon is found"""
        iconPath = self.__relPath(self.windowIconRelPath)
        fileList = os.listdir(iconPath)
        icon = None
        for file in fileList:
            name = file.split('.')[0] # [name, extention]
            if name == iconName:
                try:
                    icon = QIcon(iconPath+file)
                except:
                    printE("Unable to load the ressource {}".format(file))
            
        return icon



    def __relPath(self,pathList):
        #print(pathList)
        path = ""
        for i in pathList:
            path += i+"/"
        return path