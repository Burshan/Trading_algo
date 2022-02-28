import pymongo
import config
from datetime import datetime


class DataBase:
    def __init__(self):
        self.database_client = pymongo.MongoClient('mongodb://localhost:27017')
        self.database = self.database_client["Trading_Algorithm"]
        self.trade_symbol = config.TRADE_SYMBOL

    def insert_transaction(self, transaction):
        """
        Inserts transaction to database.
        """
        collection = self.database[self.trade_symbol]
        collection.insert_one(transaction)
        print("Successfully added the transaction into database")

    def save_transaction(self, symbol, side, quantity, last_price):
        """
        Organizes the transaction information.
        """
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
        """
        Searches for the last transaction in order to know if we are looking to buy or sell.
        """
        collection = self.database[self.trade_symbol]
        last_buy = collection.find().sort([('date', -1)]).limit(1)[0]
        if last_buy and last_buy['side'] == 'BUY':
            return last_buy
        return False

    def fake_transaction(self):
        """
        Inserts fake transaction for debugging and control.
        """
        collection = self.database[self.trade_symbol]
        transaction = {
                "symbol": 'ETHUSDT',
                "side": "BUY",
                "quantity": 1,
                "price": 2932,
                "date": datetime.now()
            }
        collection.insert_one(transaction)
