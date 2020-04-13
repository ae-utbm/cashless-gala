import sys
import os

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import PyQt5.QtCore
import PyQt5.QtGui

from QNFC import *
from QUtils import *
from QItemTree import *

from Client import *

import json

import copy

import datetime  # En attendant que Cyl mette l'heure dans les réponse

# de transaction

#  Shared variables
PWD = os.getcwd() + "/"


#  Get item tree
# INITIALISATION

try:
    itemRegister = QItemRegister()

    config = MachineConfig()
    config.counterList = requestCounterList()
    for i in config.counterList:
        config.counterDict[i[1]] = i[0]

    try:
        with open("data/counter", "r") as file:
            line = file.readline().strip()
            if line in config.counterDict:
                config.counterID = config.counterDict[line]
            else:
                config.counterID = 1
    except:
        print('Unable to read the file "counter" in "data"')

    itemRegister.itemTree = requestCounterProduct(config.counterID)
    itemRegister.loadDict(itemRegister.itemTree)
except:
    print("Unable to download the item file")
    try:
        with open(config.defaultItemFileName, "r") as file:
            itemRegister.itemTree = json.load(file)
        itemRegister.loadDict(itemRegister.itemTree)
    except:
        itemRegister.itemTree = {}
        print("Local item file not found")


def setFont(Widget, Font):

    for child in Widget.children():
        try:
            child.setFont(Font)
            setFont(child, Font)
        except:
            pass
        # TODO: Find a better way to do this
        if isinstance(child, QTreeView):  # Dirty hack to correct oversizing
            child.resizeColumnToContents(0)


class QAutoCompleteLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = QCompleter()
        self.setCompleter(self.completer)
        self.model = QStringListModel()
        self.completer.setModel(self.model)


class QInfoNFC(QGroupBox):
    """Display some basics info about the NFC card """

    connector = QConnector()

    def __init__(self, parent=None):
        super().__init__(parent)

        observer = QCardObserver()

        # Definitions
        self.mainVBoxLayout = QVBoxLayout()
        self.RowInfo = QRowInfo()
        self.userInfoButton = QPushButton()

        # Link
        #        self.frameGroupBox.setLayout(self.mainVBoxLayout)
        self.setLayout(self.mainVBoxLayout)
        self.mainVBoxLayout.addWidget(self.RowInfo)
        self.mainVBoxLayout.addWidget(self.userInfoButton)
        self.connector.balanceInfoUpdated[float].connect(self.updateBalance)

        self.userInfoButton.clicked.connect(self.showUserHistory)
        self.userInfoTree = None

        # settings

        self.setTitle("Lecteur NFC")

        self.RowInfo.addRow("Solde", euro(0))
        self.RowInfo.addRow("UID", "00 00 00 00 00 00 00")

        self.userInfoButton.setText("Afficher historique utilisateur")

        try:
            balance = requestUserBalance(toHexString(observer.cardUID))
            balance = balance["user_balance"]
            self.RowInfo.setRow(0, 1, euro(balance))
        except:
            self.RowInfo.setRow(0, 1, euro(0))

        observer.cardInserted.connect(self.addCard)
        observer.cardRemoved.connect(self.removeCard)

    def addCard(self):
        observer = QCardObserver()
        if observer.cardUID[-2:] == [0x63, 0x00]:
            print("Erreur de lecture, veuillez réessayer")
        self.RowInfo.setRow(1, 1, toHexString(observer.cardUID))

        try:
            balance = requestUserBalance(toHexString(observer.cardUID))
            balance = balance["user_balance"]
            self.RowInfo.setRow(0, 1, euro(balance))
        except:
            self.RowInfo.setRow(0, 1, euro(0))

    def removeCard(self):
        observer = QCardObserver()
        self.RowInfo.setRow(1, 1, toHexString(observer.cardUID))
        self.RowInfo.setRow(0, 1, euro(0))

    def updateBalance(self, newBalance):
        self.RowInfo.setRow(0, 1, euro(newBalance))

    def showUserHistory(self):

        observer = QCardObserver()
        if observer.hasCard() is True:
            cardUID = observer.cardUID
            response = requestUserHistory(toHexString(cardUID), -1)  # Ask for the whole user's history
            self.userInfoTree = QUserHistory(["ID", "Prix"], response)
            self.userInfoTree.show()
            center(self.userInfoTree)


class QSearchBar(QWidget):
    """Fast Search Bar"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Definition
        self.mainHBoxLayout = QHBoxLayout()
        self.inputLine = QAutoCompleteLineEdit()
        self.pushButton = QPushButton()

        self.wordList = []

        # Link
        self.setLayout(self.mainHBoxLayout)
        self.mainHBoxLayout.addWidget(self.inputLine)
        self.mainHBoxLayout.addWidget(self.pushButton)

        # Settings

        # self.inputLine.resize(300,50)
        self.pushButton.setText("OK")

    def clearText(self):
        self.inputLine.setText("")


class QMultiUserDialog(QWidget):

    paid = pyqtSignal(str)

    def __init__(self, basket, numberUser, parent=None):
        super().__init__(parent)
        # Definition
        self.mainVBoxLayout = QVBoxLayout()
        self.totalPriceRowInfo = QRowInfo()
        self.validateOrder = QPushButton()
        self.amountPaid = 0

        self.userUIDLabel = []
        self.userUID = []

        self.userPriceLabel = []
        self.userPrice = []
        self.userPriceValue = []

        self.userBalanceLabel = []
        self.userBalance = []

        self.scanUserButton = []
        self.lineLayout = []

        self.progressBar = QProgressBar()
        self.firstEdit = True
        self.indexEdit = 0
        self.basket = basket

        iregister = QItemRegister()
        itemList = iregister.getItems()
        self.totalPrice = 0
        for i in basket:
            self.totalPrice += itemList[i]["currentPrice"] * basket[i]

        self.totalPriceRowInfo.addRow("Reste à payer", euro(self.totalPrice))
        self.totalPriceRowInfo.addRow("Total à payer", euro(self.totalPrice))

        self.mainVBoxLayout.addWidget(self.totalPriceRowInfo)

        for i in range(numberUser):
            # Definitions
            self.userUIDLabel.append(QLabel())
            self.userUID.append(QLabel())

            self.userPriceLabel.append(QLabel())
            self.userPrice.append(QAutoSelectLineEdit())

            self.userBalanceLabel.append(QLabel())
            self.userBalance.append(QLabel())

            self.scanUserButton.append(QPushButton())

            self.lineLayout.append(QHBoxLayout())

            # Settings

            self.userUIDLabel[i].setText("UID")
            self.userUID[i].setText("00 00 00 00 00 00 00")

            self.userPriceLabel[i].setText("paye")
            self.userPrice[i].setText(euro(0))
            self.userPrice[i].setEnabled(False)

            self.userBalanceLabel[i].setText("Solde")
            self.userBalance[i].setText(euro(0))

            self.scanUserButton[i].setText("Scanner")
            self.scanUserButton[i].clicked.connect(self.selectUserToScan)

            # Links
            self.lineLayout[i].addWidget(self.userUIDLabel[i])
            self.lineLayout[i].addWidget(self.userUID[i])

            self.lineLayout[i].addWidget(self.userPriceLabel[i])
            self.lineLayout[i].addWidget(self.userPrice[i])

            self.lineLayout[i].addWidget(self.userBalanceLabel[i])
            self.lineLayout[i].addWidget(self.userBalance[i])

            self.lineLayout[i].addWidget(self.scanUserButton[i])
            self.mainVBoxLayout.addLayout(self.lineLayout[i])

            self.userPrice[i].editingFinished.connect(self.balanceUpdate)

        # Settings
        self.setWindowTitle("Paiment séparé")
        self.setWindowIcon(QIcon("ressources/icones/group.png"))

        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

        self.validateOrder.setText("Valider et payer")

        # Link

        self.validateOrder.clicked.connect(self.payement)
        observer = QCardObserver()
        observer.cardInserted.connect(self.scanUsers)
        self.mainVBoxLayout.addWidget(self.progressBar)
        self.mainVBoxLayout.addWidget(self.validateOrder)
        self.setLayout(self.mainVBoxLayout)

    def scanUsers(self):
        if self.isVisible() is True:  # Ce widget foutait la merde en arrière plan, il faut le forcer à agir visible
            observer = QCardObserver()
            alreadyScannedUID = []

            N_user = len(self.userUID)

            for i in self.userUID:
                alreadyScannedUID.append(i.text())

            cardUID = toHexString(observer.cardUID)
            if self.firstEdit is True:
                if cardUID not in alreadyScannedUID:
                    response = requestUserBalance(cardUID)
                    if response:
                        self.userUID[self.indexEdit].setText(cardUID)
                        self.userBalance[self.indexEdit].setText(euro(response["user_balance"]))
                        if response["user_balance"] > self.totalPrice / N_user:
                            self.userPrice[self.indexEdit].setText(euro(self.totalPrice / N_user))
                        else:
                            self.userPrice[self.indexEdit].setText(euro(response["user_balance"]))

                        temp = float(self.userPrice[self.indexEdit].text().replace("€", "").replace(",", "."))
                        self.amountPaid += temp
                        self.totalPriceRowInfo.setRow(0, 1, euro(self.totalPrice - self.amountPaid))

                        self.userPrice[self.indexEdit].setEnabled(True)
                        self.balanceUpdate()
                        self.indexEdit += 1
                    else:
                        warningDialog = QErrorDialog("Erreur", "Utilisateur introuvable", "Veuillez enregistrer cette carte à la billeterie")
                        center(warningDialog)
                        warningDialog.exec()

                    if self.indexEdit == len(self.userUID):
                        self.firstEdit = False
            else:
                if cardUID not in alreadyScannedUID:
                    response = requestUserBalance(cardUID)
                    if response:
                        self.userUID[self.indexEdit].setText(cardUID)
                        self.userBalance[self.indexEdit].setText(euro(response["user_balance"]))
                        self.userPrice[self.indexEdit].setEnabled(True)
                    else:
                        warningDialog = QErrorDialog("Erreur", "Utilisateur introuvable", "Veuillez enregistrer cette carte à la billeterie")
                        center(warningDialog)
                        warningDialog.exec()

    def selectUserToScan(self):

        self.firstEdit = False
        for i in range(len(self.scanUserButton)):
            if self.sender() == self.scanUserButton[i]:
                self.indexEdit = i

    def balanceUpdate(self):
        sum = 0.0
        leftToPay = self.totalPrice
        for i in range(len(self.userUID)):
            try:
                currentPrice = self.userPrice[i].text().replace("€", "").replace(" ", "").replace(",", ".").strip()
                currentBalance = self.userBalance[i].text().replace("€", "").replace(" ", "").replace(",", ".").strip()
                print(float(currentPrice))
                if float(currentPrice) > 0:
                    if float(currentBalance) >= float(currentPrice):
                        self.userPrice[i].setText(currentPrice)
                    else:
                        self.userPrice[i].setText(currentBalance)
                    leftToPay -= float(self.userPrice[i].text())

                    if leftToPay < 0:
                        print(float(currentPrice), leftToPay)
                        temp = float(currentPrice)
                        self.userPrice[i].setText(str(float(currentPrice) + leftToPay))
                        leftToPay += temp

                    sum += float(self.userPrice[i].text())
                else:
                    self.userPrice[i].setText("0")

            except:
                warningDialog = QErrorDialog("Erreur format", "Erreur format invalide", "Veuillez saisir un nombre réel positif")
                center(warningDialog)
                warningDialog.exec()
                self.userPrice[i].blockSignals(True)
                self.userPrice[i].setText("0")
                self.userPrice[i].blockSignals(False)

        self.totalPriceRowInfo.setRow(0, 1, euro(leftToPay))
        sum = sum / self.totalPrice * 100
        self.progressBar.setValue(sum)
        self.formatInputLine()

    def formatInputLine(self):

        for inputLine in self.userPrice:
            currentText = inputLine.text()
            currentText = currentText.replace("€", "").replace(",", ".").replace(" ", "").strip()
            inputLine.blockSignals(True)
            try:
                inputLine.setText(euro(currentText))
            except:
                inputLine.setText(euro(0))

            inputLine.blockSignals(False)

    def payement(self):
        sum = 0
        machine = MachineConfig()

        for inputLine in self.userPrice:
            currentText = inputLine.text()
            currentText = currentText.replace("€", "").replace(",", ".").replace(" ", "").strip()
            sum += float(currentText)

        if sum == self.totalPrice:
            referenceUID = self.userUID[0]
            referencePrice = self.userPrice[0]
            responseList = []
            for i in range(1, len(self.userPrice)):
                price = float(self.userPrice[i].text().replace("€", "").replace(",", ".").replace(" ", "").strip())
                response = requestTransfert(self.userUID[i].text(), referenceUID.text(), price)
                responseList.append(response)
                if response:
                    print(response)

            # response=requestBuy(referenceUID.text(),machine.counterID,MAC,self.basket)
            if response:
                # Succes
                print("Achat multiple succes")
                self.paid.emit(referenceUID.text())
                self.disconnect()
                self.close()
            else:
                print("Achat multiple echec")

        elif sum < self.totalPrice:
            pass


class QCounter(QWidget):
    def __init__(self, parent=None):
        itemRegister = QItemRegister()
        super().__init__(parent)
        ###TOOLS###
        self.jsonFileName = "ItemModel.json"  # OBSOLETE

        ###Definition###
        self.warningDialog = None

        self.mainGridLayout = QGridLayout()
        # Order definition (left pannel)
        self.orderVBoxLayout = QVBoxLayout()
        self.orderGroupBox = QGroupBox()
        self.basketTree = QBasket(["Articles", "Quantité", "Prix total", ""])

        # ProductSelection definition (middle pannel)
        self.productSelectionVBoxLayout = QVBoxLayout()
        self.productSelectionGroupBox = QGroupBox()
        self.searchBar = QSearchBar()

        self.productTree = QItemSelector(["Articles", "Prix"], itemRegister.itemTree)

        # infoNFC definition (right pannel)

        self.paymentVBoxLayout = QVBoxLayout()
        self.infoNFC = QInfoNFC()
        self.groupBoxHistory = QGroupBox()
        self.historyTree = QBarHistory(["UID", "Prix"])
        self.NFCDialog = QNFCDialog()
        self.ButtonValidateOrder = QPushButton()

        self.multiUserOrder = QPushButton()
        self.multiUserQuantity = QSimpleNumberInputDialog("Combien de clients ?")
        self.multiUserDialog = QMultiUserDialog  # Not instancied on purpose

        ###Link###
        self.setLayout(self.mainGridLayout)

        # Order pannel

        self.orderVBoxLayout.addWidget(self.basketTree)
        self.orderGroupBox.setLayout(self.orderVBoxLayout)
        self.mainGridLayout.addWidget(self.orderGroupBox, 0, 0, 3, 1)

        # Product Selection pannel
        self.productSelectionVBoxLayout.addWidget(self.searchBar)
        self.productSelectionVBoxLayout.addWidget(self.productTree)
        self.productSelectionGroupBox.setLayout(self.productSelectionVBoxLayout)
        self.mainGridLayout.addWidget(self.productSelectionGroupBox, 0, 1, 3, 1)

        # self.productTree.setBasket(self.basketTree)

        self.searchBar.inputLine.returnPressed.connect(self.lineSelect)
        self.searchBar.pushButton.clicked.connect(self.lineSelect)

        self.productTree.treeView.doubleClicked[QModelIndex].connect(self.basketTree.selectItem)

        # Payment pannel

        self.groupBoxHistory.setLayout(self.historyTree.layout())

        self.paymentVBoxLayout.addWidget(self.infoNFC)
        self.paymentVBoxLayout.addWidget(self.groupBoxHistory, 2)
        self.mainGridLayout.addLayout(self.paymentVBoxLayout, 0, 2)
        self.mainGridLayout.addWidget(self.ButtonValidateOrder, 1, 2)
        self.mainGridLayout.addWidget(self.multiUserOrder, 2, 2)
        self.ButtonValidateOrder.clicked.connect(self.OpenNFCDialog)

        self.multiUserOrder.clicked.connect(self.OpenMultiUserQuantityDialog)
        self.multiUserQuantity.valueSelected[float].connect(self.OpenMultiUserDialog)

        self.NFCDialog.cardInserted.connect(self.payement)

        ###Settings###
        # Order pannel
        self.orderGroupBox.setTitle("Panier")

        # Product Selection pannel
        self.productSelectionGroupBox.setTitle("Sélection des articles")

        itemList = []
        for key in itemRegister.itemDict:
            itemList.append(key)
        #        self.searchBar.inputLine.model.setStringList(self.__getItemList())
        self.searchBar.inputLine.model.setStringList(itemList)

        # NFC & History space

        self.groupBoxHistory.setTitle("Historique")

        self.ButtonValidateOrder.setText("Valider et payer")
        self.ButtonValidateOrder.setFixedHeight(50)
        self.multiUserOrder.setText("Plusieurs acheteurs")
        self.multiUserOrder.setFixedHeight(50)

        # Payement
        self.NFCDialog.blockSignals(True)

    def OpenMultiUserQuantityDialog(self):
        if self.basketTree.basket != {}:
            self.multiUserQuantity.show()
            center(self.multiUserQuantity)
        else:
            print("Empty basket")
            self.warningDialog = QMessageBox(QMessageBox.Warning, "Panier vide", "Veuillez sélectionner des articles avant de valider la commande", QMessageBox.Ok)
            self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
            self.warningDialog.show()
            center(self.warningDialog)

    def OpenMultiUserDialog(self, quantity):

        if quantity.is_integer() and quantity > 0:
            self.multiUserDialog = QMultiUserDialog(self.basketTree.basket, int(quantity))
            self.multiUserDialog.paid[str].connect(self.payement)
            self.multiUserDialog.show()
            center(self.multiUserDialog)
        else:
            errorDialog = QErrorDialog("Erreur de saisie", "Erreur format", "Veuillez renseigner un nombre")
            errorDialog.exec()

    def lineSelect(self):  # Probably one of my ugliest functions... T_T
        itemName = self.searchBar.inputLine.text()
        basketModel = self.basketTree.treeModel
        productModel = self.productTree.treeModel

        n_row = basketModel.rootItem.childCount()
        index = -1
        for i in range(n_row):
            if basketModel.index(i, 0).internalPointer().data["uid"] == itemName.split(",", 1)[0]:
                index = i
                try:
                    currentValue = int(self.basketTree.quantityButtonList[i].quantityEditLine.text())
                    value = int(itemName.split(",", 1)[1])
                    self.basketTree.quantityButtonList[i].quantityEditLine.setText(str(currentValue + value))
                except:
                    self.basketTree.quantityButtonList[i].incQuantity()

        if index < 0:
            #                print(productModel.itemDict)
            try:
                itemName = itemName.split(",", 1)  # itemName is actualy an item ID
                #                    itemName=itemName.split('x',1)

                if len(itemName) > 1:
                    quantity = int(itemName[1])
                else:
                    quantity = 1

                itemName = itemName[0].strip()

                if quantity <= 0:
                    print('ERROR: quantity "' + str(quantity) + '" invalid')
                    QTimer.singleShot(10, self.searchBar.clearText)
                    # The timer is helpfull here because it ensure the text is set BEFORE clearing it
                    return None
                itemRegister = QItemRegister()
                itemRegister.getItems()[itemName]  # Trick to test if itemName exist
                basketModel.insertRow(0)
                child = basketModel.index(0, 1, QModelIndex())
                child.internalPointer().data["uid"] = itemName
                child.internalPointer().data["price"] = itemRegister.getItems()[itemName]["currentPrice"]
            except:
                print("ERROR: Item unknown")
                QTimer.singleShot(10, self.searchBar.clearText)
                # The timer is helpfull here because it ensure the text is set BEFORE clearing it
                return None

            delButton = QDelButton()
            # delButton.setText("x")
            delButton.setIcon(QIcon("ressources/icones/delete.png"))
            delButton.setIconSize(QSize(32, 32))
            delButton.setFixedSize(QSize(48, 48))

            quantityButton = QQuantity()
            #                currentQuantity=int(quantityButton.quantityEditLine.text())
            quantityButton.quantityEditLine.setText(str(quantity))

            self.basketTree.quantityButtonList.insert(0, quantityButton)
            self.basketTree.delButtonList.insert(0, delButton)

            quantityButton.quantityChanged.connect(self.basketTree.updateBasket)
            delButton.deleted[QToolButton].connect(self.basketTree.deleteItem)

            self.basketTree.treeView.setIndexWidget(child, quantityButton)
            self.basketTree.treeView.setIndexWidget(basketModel.index(0, 3), delButton)

            for column in range(basketModel.columnCount(QModelIndex())):  # TODO: This part a quiet DIRTY

                child = basketModel.index(0, column)
                if column == 0:
                    basketModel.setData(child, itemRegister.getItems()[itemName]["name"], Qt.EditRole)
                if column == 2:
                    basketModel.setData(child, euro(float(quantityButton.quantityEditLine.text()) * itemRegister.getItems()[itemName]["currentPrice"]), Qt.EditRole)

            self.basketTree.forceRefresh()

        QTimer.singleShot(10, self.searchBar.clearText)  # The timer is helpfull here because it ensure the text is set BEFORE clearing it
        self.basketTree.updateBasket()

    def OpenNFCDialog(self):
        if self.basketTree.basket != {}:
            cardHandler = QCardObserver()
            if not self.NFCDialog.isVisible():
                if not cardHandler.hasCard():
                    center(self.NFCDialog)
                    self.NFCDialog.blockSignals(False)
                    self.NFCDialog.show()
                else:
                    self.payement()
                    print("Carte déjà présente sur le lecteur")
            else:
                print("Widget déjà ouvert")
        else:
            print("Empty basket")
            self.warningDialog = QMessageBox(QMessageBox.Warning, "Panier vide", "Veuillez sélectionner des articles avant de valider la commande", QMessageBox.Ok)
            self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
            self.warningDialog.show()
            center(self.warningDialog)

    def payement(self, multiUserUID=None):

        if self.sender() == self.multiUserDialog:
            cardUID = multiUserUID
        else:
            observer = QCardObserver()
            cardUID = observer.cardUID

        try:
            cardUID = toHexString(cardUID)
        except:
            cardUID = str(cardUID)
        connector = QConnector()
        print("payement:", MAC, cardUID, self.basketTree.basket)
        if self.basketTree.basket != {}:
            response = requestBuy(cardUID, config.counterID, MAC, self.basketTree.basket)
            if response:
                print("Paiement effectué avec succès")
                connector.statusBarshowMessage("Paiement effectué")
                transaction = {"cardUID": cardUID, "basket": self.basketTree.basket, "price": self.basketTree.totalPrice, "time": datetime.datetime.now().strftime("%H:%M:%S")}
                self.historyTree.addTransaction(response["transaction_id"], transaction)
                connector.updateBalanceInfo(response["user_balance"])
                #            self.infoNFC.updateBalance(response['user_balance'])
                self.basketTree.clearBasket()
            else:
                print("Paiement refusé")
                connector.statusBarshowMessage("Solde insuffisant")
                self.warningDialog = QMessageBox(QMessageBox.Warning, "Solde insuffisant", "Veuillez recharger la carte", QMessageBox.Ok)
                self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                self.warningDialog.show()
                center(self.warningDialog)
        else:
            print("Empty basket")
            connector.statusBarshowMessage("Panier vide")
            self.warningDialog = QMessageBox(QMessageBox.Warning, "Panier vide", "Veuillez sélectionner des articles avant de valider la commande", QMessageBox.Ok)
            self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
            self.warningDialog.show()
            center(self.warningDialog)

    def multiUserPayement(self, userList, userPrice):

        observer = QCardObserver()
        cardUID = userList[0]
        connector = QConnector()

        print("payement:", MAC, toHexString(cardUID), self.basketTree.basket)
        if self.basketTree.basket != {}:
            response = requestBuy(toHexString(cardUID), config.counterID, MAC, self.basketTree.basket)
            if response:
                print("Paiement effectué avec succès")
                connector.statusBarshowMessage("Paiement effectué")
                transaction = {"cardUID": toHexString(cardUID), "basket": self.basketTree.basket, "price": self.basketTree.totalPrice, "time": datetime.datetime.now().strftime("%H:%M:%S")}
                self.historyTree.addTransaction(response["transaction_id"], transaction)
                connector.updateBalanceInfo(response["user_balance"])
                #            self.infoNFC.updateBalance(response['user_balance'])
                self.basketTree.clearBasket()
            else:
                print("Paiement refusé")
                connector.statusBarshowMessage("Solde insuffisant")
                self.warningDialog = QMessageBox(QMessageBox.Warning, "Solde insuffisant", "Veuillez recharger la carte", QMessageBox.Ok)
                self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                self.warningDialog.show()
                center(self.warningDialog)
        else:
            print("Empty basket")
            connector.statusBarshowMessage("Panier vide")
            self.warningDialog = QMessageBox(QMessageBox.Warning, "Panier vide", "Veuillez sélectionner des articles avant de valider la commande", QMessageBox.Ok)
            self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
            self.warningDialog.show()
            center(self.warningDialog)


class QUserInfo(QGroupBox):
    def __init__(self):
        super().__init__(self)

        # Definitons

        self.mainVBoxLayout = QVBoxLayout()
        self.rowInfo = QRowInfo()

        # Settings
        self.setTitle("USER")

        self.rowInfo.addRow("Solde", euro(0))
        self.rowInfo.addRow("UID", "00 00 00 00 00 00 00")

        # Link


# class QUserHistory(Q)


class QAbstractPayement(QGroupBox):

    credited = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Paiement par carte de crédit")
        self.warningDialog = None

    def credit(self):

        osbserver = QCardObserver()
        cardUID = osbserver.cardUID

        currentText = self.inputLine.text()
        currentText = currentText.replace("€", "").replace(",", ".").replace(" ", "").strip()

        mantissas = currentText.split(".")
        isFormatValid = True

        if len(mantissas) == 2:
            mantissas = mantissas[1]
            if len(mantissas) <= 2:
                isFormatValid = True  # useless but visual
            else:
                isFormatValid = False

                self.warningDialog = QMessageBox(QMessageBox.Warning, "Format invalide", "Format invalide, veuillez saisir au plus deux chiffres après la virgule", QMessageBox.Ok)
                self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                self.warningDialog.show()
                center(self.warningDialog)

        if isFormatValid is True:
            try:
                amount = float(currentText)
                self.inputLine.setText(euro(0))
                if amount > 0:
                    self.credited.emit(amount)
                else:
                    self.warningDialog = QMessageBox(QMessageBox.Warning, "Format invalide", "Format invalide, veuillez saisir un nombre strictement positif", QMessageBox.Ok)
                    self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                    self.warningDialog.show()
                    center(self.warningDialog)
            except:
                self.warningDialog = QMessageBox(QMessageBox.Warning, "Format invalide", "Format invalide, veuillez saisir un nombre", QMessageBox.Ok)
                self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                self.warningDialog.show()
                center(self.warningDialog)


class QCreditCardPayement(QAbstractPayement):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Definitions

        self.setTitle("Paiement par carte de crédit")

        self.mainVBoxLayout = QVBoxLayout()
        self.mainGridLayout = QGridLayout()

        self.label = QLabel()
        self.inputLine = QAutoSelectLineEdit()
        self.okButton = QPushButton()

        # Settings

        self.label.setText("Credit:")
        self.okButton.setText("OK")
        self.inputLine.setMaximumWidth(150)
        self.inputLine.setAlignment(Qt.AlignCenter)
        self.inputLine.setText(euro(0))

        # Link

        self.mainGridLayout.addWidget(self.label, 0, 0, Qt.AlignLeft)
        self.mainGridLayout.addWidget(self.inputLine, 0, 1, Qt.AlignLeft)
        self.mainGridLayout.addWidget(self.okButton, 1, 0, Qt.AlignLeft)

        self.mainVBoxLayout.addLayout(self.mainGridLayout)
        self.mainVBoxLayout.addStretch(1)

        self.setLayout(self.mainVBoxLayout)

        self.inputLine.editingFinished.connect(self.formatInputLine)
        self.okButton.clicked.connect(self.credit)
        self.inputLine.returnPressed.connect(self.credit)

    def formatInputLine(self):
        currentText = self.inputLine.text()
        currentText = currentText.replace("€", "").replace(",", ".").replace(" ", "").strip()
        self.inputLine.blockSignals(True)
        try:
            self.inputLine.setText(euro(currentText))
        except:
            self.inputLine.setText(euro(0))

        self.inputLine.blockSignals(False)


class QCashPayement(QAbstractPayement):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mainGridLayout = QGridLayout()
        self.mainVBoxLayout = QVBoxLayout()

        self.moneyInLabel = QLabel()
        self.moneyIn = QAutoSelectLineEdit()
        self.moneyBackLabel = QLabel()
        self.moneyBack = QLabel()

        self.setTitle("Paiement par espèce")

        self.label = QLabel()
        self.inputLine = QAutoSelectLineEdit()
        self.okButton = QPushButton()

        # Settings

        self.label.setText("Credit:")
        self.okButton.setText("OK")
        self.inputLine.setMaximumWidth(150)
        self.inputLine.setAlignment(Qt.AlignCenter)
        self.inputLine.setText(euro(0))
        self.moneyBack.setText(euro(0))
        self.moneyBack.setAlignment(Qt.AlignCenter)
        self.moneyBackLabel.setText("Argent à rendre:")
        self.moneyIn.setText(euro(0))
        self.moneyIn.setAlignment(Qt.AlignCenter)
        self.moneyInLabel.setText("Argent reçu:")

        # Link

        self.mainGridLayout.addWidget(self.label, 0, 0, Qt.AlignLeft)
        self.mainGridLayout.addWidget(self.inputLine, 0, 1, Qt.AlignLeft)
        self.mainGridLayout.addWidget(self.moneyInLabel, 1, 0, Qt.AlignLeft)
        self.mainGridLayout.addWidget(self.moneyIn, 1, 1, Qt.AlignLeft)
        self.mainGridLayout.addWidget(self.moneyBackLabel, 2, 0, Qt.AlignLeft)
        self.mainGridLayout.addWidget(self.moneyBack, 2, 1, Qt.AlignLeft)

        self.mainGridLayout.addWidget(self.okButton, 3, 0, Qt.AlignLeft)

        self.mainVBoxLayout.addLayout(self.mainGridLayout)
        self.mainVBoxLayout.addStretch(1)

        self.setLayout(self.mainVBoxLayout)

        self.inputLine.editingFinished.connect(self.formatInputLine)
        self.okButton.clicked.connect(self.credit)
        self.inputLine.returnPressed.connect(self.credit)

    def formatInputLine(self):
        currentText = self.inputLine.text()

        try:
            creditAmount = float(self.inputLine.text())
            currentTextMoneyIn = self.moneyIn.text()
            currentTextMoneyIn = currentTextMoneyIn.replace("€", "").replace(",", ".").replace(" ", "").strip()
            moneyInAmount = float(currentTextMoneyIn)
            self.moneyBack.setText(euro(moneyInAmount - creditAmount))
        except:
            creditAmount = 0
            currentTextMoneyIn = self.moneyIn.text()
            currentTextMoneyIn = currentTextMoneyIn.replace("€", "").replace(",", ".").replace(" ", "").strip()
            moneyInAmount = float(currentTextMoneyIn)
            self.moneyBack.setText(euro(moneyInAmount - creditAmount))

        currentText = currentText.replace("€", "").replace(",", ".").replace(" ", "").strip()
        self.inputLine.blockSignals(True)
        try:
            self.inputLine.setText(euro(currentText))
        except:
            self.inputLine.setText(euro(0))

        self.inputLine.blockSignals(False)

    def formatMoneyIn(self):
        currentText = self.moneyIn.text()
        currentText = currentText.replace("€", "").replace(",", ".").replace(" ", "").strip()
        self.moneyIn.blockSignals(True)
        try:
            self.MoneyIn.setText(euro(currentText))
        except:
            self.moneyIn.setText(euro(0))

        self.moneyIn.blockSignals(False)


class QAEPayement(QCreditCardPayement):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Paiement par compte AE")


class QNFCPayement(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Transfert entre cartes NFC")


class QOtherPayement(QCreditCardPayement):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Singularité")

    def credit(self):

        osbserver = QCardObserver()
        cardUID = osbserver.cardUID

        currentText = self.inputLine.text()
        currentText = currentText.replace("€", "").replace(",", ".").replace(" ", "").strip()

        mantissas = currentText.split(".")
        isFormatValid = True

        if len(mantissas) == 2:
            mantissas = mantissas[1]
            if len(mantissas) <= 2:
                isFormatValid = True  # useless but visual
            else:
                isFormatValid = False

                self.warningDialog = QMessageBox(QMessageBox.Warning, "Format invalide", "Format invalide, veuillez saisir au plus deux chiffres après la virgule", QMessageBox.Ok)
                self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                self.warningDialog.show()
                center(self.warningDialog)

        if isFormatValid is True:
            try:
                amount = float(currentText)
                self.inputLine.setText(euro(0))
                self.credited.emit(amount)
            except:
                self.warningDialog = QMessageBox(QMessageBox.Warning, "Format invalide", "Format invalide, veuillez saisir un nombre", QMessageBox.Ok)
                self.warningDialog.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                self.warningDialog.show()
                center(self.warningDialog)


class QTransaction(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Definitions

        # Payement type
        self.mainGridLayout = QGridLayout()

        self.payementTypeGroupBox = QGroupBox()
        self.payementTypeLayout = QVBoxLayout()

        self.cashRadio = QRadioButton()
        self.creditCardRadio = QRadioButton()
        self.aeAccountRadio = QRadioButton()
        self.nfcRadio = QRadioButton()
        self.otherRadio = QRadioButton()

        # Payement

        self.payementLayout = QStackedLayout()
        self.creditCardPayement = QCreditCardPayement()
        self.cashPayement = QCashPayement()
        self.nfcPayement = QNFCPayement()
        self.aePayement = QAEPayement()
        self.otherPayement = QOtherPayement()

        # History

        self.historyGroupBox = QGroupBox()
        self.historyLayout = QVBoxLayout()
        self.historyTree = QTransactionHistory(["UID", "Credit"])
        self.infoNFC = QInfoNFC()

        # settings

        # Payement type
        self.payementTypeGroupBox.setTitle("Moyen de paiement")
        self.cashRadio.setText("Espèces")
        self.creditCardRadio.setText("Carte de crédit")
        self.aeAccountRadio.setText("Compte AE")
        self.nfcRadio.setText("Transfert NFC")
        self.nfcRadio.setToolTip("Permet de transférer des fonds depuis une carte NFC vers une autre")
        self.otherRadio.setText("Non défini")
        self.otherRadio.setToolTip("Moyens de paiements indéfinis, créditation pure, offre promo, en nature avec lae bar(maid/man) <3, etc..")

        self.creditCardRadio.setChecked(True)

        # Payement

        # History

        self.historyGroupBox.setTitle("Historique")

        # Link

        # Payement type
        self.payementTypeLayout.addWidget(self.creditCardRadio)
        self.payementTypeLayout.addWidget(self.cashRadio)
        self.payementTypeLayout.addWidget(self.aeAccountRadio)
        self.payementTypeLayout.addWidget(self.nfcRadio)
        self.payementTypeLayout.addWidget(self.otherRadio)

        self.payementTypeGroupBox.setLayout(self.payementTypeLayout)

        self.mainGridLayout.addWidget(self.payementTypeGroupBox, 0, 0, 1, 1)

        # Payement
        self.payementLayout.addWidget(self.creditCardPayement)
        self.payementLayout.addWidget(self.cashPayement)
        self.payementLayout.addWidget(self.aePayement)
        self.payementLayout.addWidget(self.nfcPayement)
        self.payementLayout.addWidget(self.otherPayement)

        self.mainGridLayout.addLayout(self.payementLayout, 1, 0, 1, 1)

        self.creditCardPayement.credited[float].connect(self.credit)
        self.otherPayement.credited[float].connect(self.credit)
        self.aePayement.credited[float].connect(self.credit)
        # self.balanceInfoUpdated[float].connect(connector.updateBalanceInfo)

        # History
        self.historyLayout.addWidget(self.infoNFC)
        self.historyLayout.addWidget(self.historyGroupBox)
        self.historyGroupBox.setLayout(self.historyTree.layout())
        self.mainGridLayout.addLayout(self.historyLayout, 0, 1, 2, 1)

        self.setLayout(self.mainGridLayout)

        self.cashRadio.toggled.connect(self.selectCash)
        self.creditCardRadio.toggled.connect(self.selectCreditCard)
        self.aeAccountRadio.toggled.connect(self.selectAE)
        self.nfcRadio.toggled.connect(self.selectNFC)
        self.otherRadio.toggled.connect(self.selectOther)

    def selectCreditCard(self):
        if self.creditCardRadio.isChecked():
            self.payementLayout.setCurrentWidget(self.creditCardPayement)

    def selectCash(self):
        if self.cashRadio.isChecked():
            self.payementLayout.setCurrentWidget(self.cashPayement)

    def selectAE(self):
        if self.aeAccountRadio.isChecked():
            self.payementLayout.setCurrentWidget(self.aePayement)

    def selectNFC(self):
        if self.nfcRadio.isChecked():
            self.payementLayout.setCurrentWidget(self.nfcPayement)

    def selectOther(self):
        if self.otherRadio.isChecked():
            self.payementLayout.setCurrentWidget(self.otherPayement)

    def credit(self, amount):

        observer = QCardObserver()
        cardUID = observer.cardUID

        if observer.hasCard() is True:
            response = requestRefilling(toHexString(cardUID), config.counterID, MAC, amount)
            print("User {} has been credited of {}. New balance {}".format(response["user_UID"], euro(amount), euro(response["user_balance"])))
            self.infoNFC.updateBalance(response["user_balance"])
            # self.balanceInfoUpdated.emit(response["user_balance"])
            connector = QConnector()
            connector.updateBalanceInfo(response["user_balance"])
            transaction = {"cardUID": response["user_UID"], "price": amount}
            # TODO: NEED Transaction ID in response to avoid this dangerous id = ...
            id = requestComputerHistory(MAC, 1)[0]
            self.historyTree.addTransaction(id["id"], transaction)
        else:
            print("Please a card on the reader")


class QMainTab(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialization
        self.TabCounter = QCounter()
        self.TabStock = QTransaction()
        self.TabStat = QWidget()

        # Add tabs
        self.addTab(self.TabCounter, "Comptoir")
        self.addTab(self.TabStock, "Transactions")
        self.addTab(self.TabStat, "Stats")

        self.resize(1200, 800)


class QNFCDialog(QWidget):

    cardInserted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowIcon(QIcon(PWD + "ressources/logoCarte.png"))
        self.mainVBoxLayout = QVBoxLayout()

        Movie = QMovie(PWD + "ressources/Animation2.gif")

        self.card = QLabel()
        self.card.setMovie(Movie)
        Movie.start()

        self.LabelInstruction = QLabel()
        self.LabelInstruction.setText("Veuillez présenter la carte devant le lecteur")

        self.button = QPushButton()
        self.button.setText("Annuler")

        self.mainVBoxLayout.addWidget(self.card)
        self.mainVBoxLayout.addWidget(self.LabelInstruction)
        self.mainVBoxLayout.addWidget(self.button)
        self.setLayout(self.mainVBoxLayout)
        self.setWindowTitle("Paiement")

        self.button.clicked.connect(self.Cancel)

        cardObserver = QCardObserver()
        cardObserver.cardInserted.connect(self.Payement)

    def Cancel(self):
        # Do stuff...
        print("Annuler")
        self.close()

    def Payement(self):
        print("QNFCDialog: Carte détectée")
        self.cardInserted.emit()
        self.blockSignals(True)
        self.close()


class QFakeCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        cardObserver = QCardObserver()

        self.setWindowIcon(QIcon(PWD + "ressources/logoCarte.png"))
        self.mainVBoxLayout = QVBoxLayout()

        self.card = QLabel()
        self.card.setPixmap(QPixmap(PWD + "ressources/logoCarte.png"))

        self.GroupBoxFCEdit = QGroupBox()
        self.GroupBoxFCEdit.setTitle("UID en hexadécimal")
        hbox = QHBoxLayout()
        self.FCEdit = QLineEdit()
        self.FCEdit.setAlignment(PyQt5.QtCore.Qt.AlignCenter)
        self.FCEdit.resize(400, 50)
        hbox.addWidget(self.FCEdit)
        self.GroupBoxFCEdit.setLayout(hbox)

        self.buttonAddCard = QPushButton()
        self.buttonAddCard.setText("Présenter une carte sur le lecteur")
        self.buttonAddCard.clicked.connect(cardObserver.virtualCardInsert)

        self.buttonRemoveCard = QPushButton()
        self.buttonRemoveCard.setText("Enlever la carte du lecteur")
        self.buttonRemoveCard.clicked.connect(cardObserver.virtualCardRemove)

        self.mainVBoxLayout.addWidget(self.card)
        self.mainVBoxLayout.addWidget(self.GroupBoxFCEdit)
        self.mainVBoxLayout.addWidget(self.buttonAddCard)
        self.mainVBoxLayout.addWidget(self.buttonRemoveCard)
        self.setLayout(self.mainVBoxLayout)
        self.setWindowTitle("Simulation")

        self.NFCDialog = None

    def LinkWidget(self, Widget):
        self.LinkedWidget = Widget

    def CloseNFCDialog(self):
        self.LinkedWidget.Payement()


class QMainMenu(QMainWindow):
    def __init__(self):
        itemRegister.start()
        super().__init__()

        self.setWindowTitle("Gala.Manager.Core")
        self.resize(1200, 800)
        self.setWindowIcon(QIcon(PWD + "ressources/icon.ico"))

        center(self)
        self.MainTab = QMainTab()
        self.setCentralWidget(self.MainTab)

        # NFC

        self.CardMonitor = CardMonitor()
        self.CardObserver = QCardObserver()
        self.CardMonitor.addObserver(self.CardObserver)

        font = QFont()  # TODO: Dirty trick to set the whole app font size
        font.setPointSize(16)
        setFont(self, font)

        #  Menu
        mainMenu = self.menuBar()  # Built in function that hold actions

        # Definitions
        configMenu = mainMenu.addMenu("&Config")
        helpMenu = mainMenu.addMenu("&Aide")
        counterMenu = configMenu.addMenu("&Comptoir")
        counterActionList = []
        self.counterActionGroup = QActionGroup(self)
        for i in config.counterDict:
            action = QAction(i, self)
            action.setCheckable(True)
            counterActionList.append(action)
            self.counterActionGroup.addAction(action)
            counterMenu.addAction(action)
            if config.counterDict[i] == config.counterID:
                action.setChecked(True)
            action.triggered.connect(self.updateCounter)

        ipAction = QAction("&Adresse serveur", self)
        ipAction.triggered.connect(self.setServerAddress)

        configMenu.addAction(ipAction)

        self.ipDialog = QIpInputDialog("Veuillez saisir l'adresse du serveur")
        self.ipDialog.setWindowTitle("IP Serveur")

        #  Settings
        # Link

        # Toolbar
        self.statusBar()  # Built in function that show menu bar
        connector = QConnector()
        connector.statusBar = self.statusBar()

        self.counterLabel = QLabel()
        try:
            self.counterLabel.setText(self.counterActionGroup.checkedAction().text())
        except:
            print("No counter found")
        self.statusBar().addPermanentWidget(self.counterLabel)

    def ForceHistoryRefresh(self):
        pass

    def setServerAddress(self):
        self.ipDialog.show()
        center(self.ipDialog)

    def updateCounter(self):
        counterName = self.counterActionGroup.checkedAction().text()
        self.counterLabel.setText(counterName)
        try:
            with open("data/counter", "w") as file:
                file.write(counterName)
        except:
            print('Unable to write the file "counter" in "data"')
        config.counterID = config.counterDict[counterName]

        try:
            itemRegister.itemTree = requestCounterProduct(config.counterID)
            itemRegister.itemDict = {}
            itemRegister.loadDict(itemRegister.itemTree)
        except:
            print("Unable to download the item file")
            try:
                with open(config.defaultItemFileName, "r") as file:
                    itemRegister.itemTree = json.load(file)
                itemRegister.loadDict(itemRegister.itemTree)
            except:
                itemRegister.itemTree = {}
                print("Local item file not found")

        self.MainTab.TabCounter.productTree.treeModel.updateModel(itemRegister.itemTree)
        connector = QConnector()
        connector.statusBarshowMessage("Comptoir: " + self.counterActionGroup.checkedAction().text())
        # self.MainTab.TabCounter.productTree.treeModel.layoutChanged.emit()


class QFadingWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.Timer = QTimer()
        self.Duration = 250
        self.Interval = 2
        self.Timer.setInterval(self.Interval)
        self.Timer.setTimerType(PyQt5.QtCore.Qt.PreciseTimer)
        self.Timer.timeout.connect(self.Callback)
        self.setWindowOpacity(0)

        self.Timer.start()

        self.Opacity = 0
        self.Count = 0

    def Callback(self):
        self.Opacity = self.Count * self.Interval / self.Duration
        self.Count += 1
        # print(self.Opacity)
        if self.Opacity <= 1:
            self.setWindowOpacity(self.Opacity)
        else:
            self.setWindowOpacity(1)
            self.Timer.stop()