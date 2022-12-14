from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from src.managers.QNFC import *


class QNFCManagerSingleton(type(QObject)):
    _instance = {}

    def __call__(cls):
        if cls not in cls._instance:
            cls._instance[cls] = super(QNFCManagerSingleton, cls).__call__()
        return cls._instance[cls]


class QNFCManager(QObject, metaclass=QNFCManagerSingleton):

    cardInserted = (
        pyqtSignal()
    )  # It's a copy of the cardObserver signal.. but wrapped in a manager
    cardRemoved = pyqtSignal()

    readerInserted = pyqtSignal()
    readerRemoved = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.cardMonitor = CardMonitor()
        self.cardObserver = QCardObserver()
        self.cardMonitor.addObserver(self.cardObserver)

        self.readermonitor = ReaderMonitor()
        self.readerUpdater = ReaderUpdater()
        self.readermonitor.addObserver(self.readerUpdater)

        self.cardObserver.cardInserted.connect(self.wrapperCardInserted)
        self.cardObserver.cardRemoved.connect(self.wrapperCardRemoved)

    def getCardUID(self):
        return self.cardObserver.getCardUID()

    def wrapperCardInserted(
        self,
    ):  # basicaly, it's just the same that the cardObserver event but wrapped here
        self.cardInserted.emit()

    def wrapperCardRemoved(self):
        self.cardRemoved.emit()

    def hasCard(self):
        return self.cardObserver.hasCard()

    def virtualCardInsert(self, uid):
        cardObserver = QCardObserver()
        cardObserver.cardUID = uid
        cardObserver.setCardState(True)
        cardObserver.cardInserted.emit()

    def virtualCardRemove(self):
        cardObserver = QCardObserver()
        cardObserver.cardUID = toHexString([0, 0, 0, 0])
        cardObserver.setCardState(False)
        cardObserver.cardRemoved.emit()
