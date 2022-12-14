from __future__ import print_function

# GRPC modules
import grpc
from grpc import RpcError
import src.managers.com.com_pb2 as com_pb2
import src.managers.com.com_pb2_grpc as com_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp

# Help to convert google timestamp into QTime ...
import pytz
from datetime import datetime

from src.utils.Euro import *
from src.atoms.Atoms import *

# Cute print in the terminal
import logging

# 'packing' describes the fact of converting the UI atom
# into a grpc message

# 'unpacking' describes the fact of converting the grpc
# message into an atom that UI can use.


def packProduct(product: Product) -> com_pb2.BasketItem:
    pb_price = packMoney(product.getPrice())
    newPbProduct = com_pb2.BasketItem(
        product_id=product.getId(), quantity=product.getQuantity(), unit_price=pb_price
    )
    return newPbProduct


def unpackProduct(pb_product: com_pb2.Product) -> Product:

    happyHoursList = []
    pbHappyHoursList = pb_product.happy_hours
    for j in pbHappyHoursList:
        newHappyHour = HappyHours()
        newHappyHour.setStart(unpackTime(j.start))
        newHappyHour.setEnd(unpackTime(j.end))
        newHappyHour.setPrice(
            unpackMoney(j.price)
        )  # Since we choosed a securised money format we need to convert
        happyHoursList.append(newHappyHour)

    newProduct = Product()
    newProduct.setId(pb_product.id)
    newProduct.setName(pb_product.name)
    newProduct.setCode(pb_product.code)
    newProduct.setPrice(unpackMoney(pb_product.default_price))
    newProduct.setDefaultPrice(unpackMoney(pb_product.default_price))
    newProduct.setHappyHours(happyHoursList)
    newProduct.setCategory(pb_product.category)
    newProduct.setQuantity(1)
    return newProduct


def packMoney(euro: Eur) -> com_pb2.Money:
    money = com_pb2.Money(amount=str(euro.amount))
    return money


def unpackMoney(money: com_pb2.Money) -> Eur:
    return Eur(money.amount)


def packCounter(counter: Counter) -> com_pb2.CounterListReply.Counter:
    pass  # should not be usefull


def unpackCounter(pb_counter: com_pb2.CounterListReply.Counter) -> Counter:
    newCounter = Counter()
    newCounter.setId(pb_counter.id)
    newCounter.setName(pb_counter.name)
    return newCounter


def packDistribution(distrib: Distribution) -> [com_pb2.Payment]:
    paymentList = []
    for user in distrib.getUserList():
        amount = packMoney(distrib.getUserAmount(user))
        newPayement = com_pb2.Payment(customer_id=user, amount=amount)
        paymentList.append(newPayement)
    return paymentList


def unpackDistribution(payments: [com_pb2.Payment]) -> Distribution:
    distribution = Distribution()
    for payment in payments:
        distribution.addUser(payment.customer_id)
        distribution.addAmount(unpackMoney(payment.amount))
    return distribution


def unpackRefilling(pb_refilling: com_pb2.Refilling) -> Refilling:
    newRefilling = Refilling()
    newRefilling.setId(pb_refilling.id)
    newRefilling.setCustomerId(pb_refilling.customer_id)
    newRefilling.setCounterId(pb_refilling.counter_id)
    newRefilling.setAmount(unpackMoney(pb_refilling.amount))
    newRefilling.setRefounded(pb_refilling.cancelled)
    return newRefilling


def unpackBuying(pb_buying: com_pb2.Buying) -> Buying:
    buying = Buying()
    buying.setId(pb_buying.id)
    buying.setLabel(pb_buying.label)
    buying.setPrice(unpackMoney(pb_buying.price))
    buying.setRefounded(pb_buying.refounded)
    buying.setCounterId(pb_buying.counter_id)
    buying.setDate(unpackTime(pb_buying.date))
    buying.setDistribution(unpackDistribution(pb_buying.payments))

    return buying


def unpackTime(protoTime: com_pb2.Time) -> datetime:
    time = Timestamp.ToDatetime(protoTime.time)
    timezone = pytz.timezone(protoTime.timezone)
    return pytz.utc.localize(time).astimezone(timezone)
