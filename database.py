import pymongo
import config
from datetime import datetime


class DataBase:
    def __init__(self):
        self.database_client = pymongo.MongoClient('mongodb://localhost:27017')
        self.database = self.database_client["Trading_Algorithm"]
        self.trade_symbol = config.TRADE_SYMBOL

    def insert_transaction(self, transaction):
        collection = self.database[self.trade_symbol]
        collection.insert_one(transaction)
        print("Successfully added the transaction into database")

    def save_transaction(self, symbol, side, quantity, last_price):
        print("Sending the transaction into database")
        transaction = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": last_price,
            "date": datetime.now()
        }
        self.insert_transaction(transaction)

    def get_last_bought(self):
        collection = self.database[self.trade_symbol]
        last_buy = collection.find().sort([('date', -1)]).limit(1)[0]
        if last_buy and last_buy['side'] == 'BUY':
            return last_buy
        return False

    def fake_transaction(self):
        collection = self.database[self.trade_symbol]
        transaction = {
                "symbol": 'ETHUSDT',
                "side": "BUY",
                "quantity": 1,
                "price": 2932,
                "date": datetime.now()
            }
        collection.insert_one(transaction)
