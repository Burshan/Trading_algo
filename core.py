import config
import requests
import websocket
import json
import talib
import numpy
import time
import datetime
import pandas as pd
from datetime import datetime
from binance.client import Client
from binance.enums import *
from database import DataBase


class Core:
    def __init__(self):
        self.socket = config.SOCKET
        self.database = DataBase()
        self.client = Client(config.API_KEY, config.API_SECRET)
        self.is_initialized = False
        self.is_in_position = False
        self.closes = []
        self.bought_price = 0
        self.sold_price = 0
        self.gain = 0
        self.minimum_gain = config.MINIMUM_GAIN
        self.trade_symbol = config.TRADE_SYMBOL
        self.trade_quantity = config.TRADE_QUANTITY
        self.rsi_period = config.RSI_PERIOD
        self.rsi_overbought = config.RSI_OVERBOUGHT
        self.rsi_oversold = config.RSI_OVERSOLD
        self.macd_fast = config.MACD_FAST
        self.macd_slow = config.MACD_SLOW
        self.macd_signal_speed = config.MACD_SIGNALPEDIOD
        self.macd_start = self.macd_slow + self.macd_signal_speed
        self.telegram_bot_token = config.TELEGRAM_TOKEN
        self.telegram_chat_id = config.TELEGRAM_ID

    def order(self, side, quantity, symbol, last_price, order_type=ORDER_TYPE_MARKET):
        """
        Sets an order request (either but or sell for the Binance API)
        """
        print("Sending an order...")
        try:
            order = self.client.create_order(
                symbol=symbol, side=side, type=order_type, quantity=quantity)
            self.database.save_transaction(symbol, side, quantity, last_price)

        except Exception as e:
            print("an exception occured - {}".format(e))
            return False
        return True

    def telegram_send(self, bot_message):
        """
        Sends a massage to our telegram bot.
        """
        bot_message = bot_message + f" ({self.trade_symbol})"
        send_text = 'https://api.telegram.org/bot' + self.telegram_bot_token + \
                    '/sendMessage?chat_id=' + self.telegram_chat_id + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
        return response.json()

    def calculate_gain(self, close_price):
        """
        TODO: understand this method.
        """
        diff = close_price - self.bought_price
        return float("{:.2f}".format((diff / self.bought_price) * 100))

    @staticmethod
    def clear_array(d_array):
        """
        Clears the candles array and returns him.
        """
        if len(d_array) > 1000:
            data = d_array[-100:]
            return data
        return d_array

    def on_open(self, ws):
        """
        Called when the socket connection opened.
        """
        message = "opened connection"
        print(message)

    def on_close(self, ws):
        """
        Called when the socket connection closed.
        """
        print('closed connection')
        print('opening connection again')
        self.telegram_send('opening connection again')
        self.open_socket()

    def get_historical_data(self):
        """
        Gets historical data from Binance API and organize it in data frame.
        """
        print("Called historical data...")
        candles = self.client.get_historical_klines(self.trade_symbol,
                                                    self.client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
        data_frame = pd.DataFrame(candles)
        df_edit = data_frame.drop([0, 5, 6, 7, 8, 9, 10, 11], axis=1)
        df_final = df_edit.drop(df_edit.tail(1).index)
        df_final.columns = ['O', 'H', 'L', 'C']
        lst = df_final['C'].tolist()
        self.closes.extend((lst[-self.macd_start-1:]))

    def calculate_rsi(self, np_closes):
        """
        RSI Indicator.
        """
        rsi = talib.RSI(np_closes, self.rsi_period)
        last_rsi = rsi[-1]
        return last_rsi

    def calculate_macd(self, np_closes):
        """
        MACD Indicator.
        """
        if len(self.closes) > self.macd_start:
            macd, macdsignal, macdhist = talib.MACD(
                np_closes, self.macd_fast, self.macd_slow, self.macd_signal_speed)
            macd = self.clear_array(macd)
            macdsignal = self.clear_array(macdsignal)
            macdhist = self.clear_array(macdhist)
        else:
            macd, macdsignal, macdhist = (10, 0, 10)
        last_macdhist = macdhist[-1]
        return last_macdhist

    # def calculate_bollinger_bands(self, np_closes):
    #     upper, middle, lower = talib.BBANDS(np_closes, matype=MA_Type.T3)
    #     return upper, middle, lower

    def on_message(self, ws, message):
        """
        Called whenever we get new socket from Binance.
        """
        if not self.is_initialized:
            self.get_historical_data()
            self.is_initialized = True
        try:
            last_buy = self.database.get_last_bought()
        except Exception as e:
            print(f"an exception occured - {e}")
            last_buy = ""

        if last_buy:
            self.is_in_position = True
            self.bought_price = last_buy['price']

        json_message = json.loads(message)
        candle = json_message['k']
        is_candle_closed = candle['x']
        close = float(candle['c'])
        if is_candle_closed:
            self.closes.append(float(close))
            if len(self.closes) > self.rsi_period:
                np_closes = numpy.array(self.closes, dtype=float)
                last_rsi = self.calculate_rsi(np_closes)
                last_macdhist = self.calculate_macd(np_closes)
                print("the current RSI is {}, MACD is {}".format(
                    last_rsi, last_macdhist))
                if last_rsi >= self.rsi_overbought and (-1.1 <= last_macdhist <= 1.1):
                    if self.is_in_position:
                        gain = self.calculate_gain(close)
                        if gain >= self.minimum_gain:
                            print(f"{self.trade_symbol} overbought! Sell!")
                            self.telegram_send(f"{self.trade_symbol} Is overbought! Sell!")
                            # quantity = last_buy['quantity'] - 0.5
                            order_succeeded = self.order(
                                "SELL", self.trade_quantity, self.trade_symbol, close)
                            time.sleep(1)
                            if order_succeeded:
                                self.bought_price = 0
                                print(f"{self.trade_symbol} was sold")
                                self.telegram_send(f"{self.trade_symbol} was sold")
                        else:
                            print(f"{self.trade_symbol} Is overbought, but not profitable.")
                    else:
                        print(f"{self.trade_symbol} Is overbought, but we don't own any.")

                if last_rsi <= self.rsi_oversold and (-1.1 <= last_macdhist <= 1.1):
                    if not self.is_in_position:
                        print(f"{self.trade_symbol} Is oversold! Buy!")
                        self.telegram_send(f"{self.trade_symbol} Is oversold! Buy!")
                        # quantity = round(float(TRADE_MONEY_PER_BUY) / float(close))
                        order_succeeded = self.order(
                            "BUY", self.trade_quantity, self.trade_symbol, close)
                        time.sleep(1)
                        if order_succeeded:
                            self.bought_price = close
                            print(f"{self.trade_symbol} was Bought")
                            self.telegram_send(f"{self.trade_symbol} was Bought")
                    else:
                        print(f"{self.trade_symbol} Is oversold, but you already own it.")
                self.clear_array(np_closes)
                self.clear_array(self.closes)

    def open_socket(self):
        ws = websocket.WebSocketApp(
            self.socket, on_open=self.on_open, on_close=self.on_close, on_message=self.on_message)
        ws.run_forever()


while True:
    manager = Core()
    manager.open_socket()
    # time.sleep(60)
