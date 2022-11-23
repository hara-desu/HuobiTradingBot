from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import logging
import os
import sys
import time
import warnings
import ccxt
import pandas as pd
import schedule
import config

# Settings for pandas dataframe
warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', None)

# Variable exchange used for buy / sell orders
EXCHANGE = ccxt.huobi({
    "apiKey": config.HUOBI_API_KEY,
    "secret": config.HUOBI_SECRET_KEY})

# Configuring logging.
logging.basicConfig(filename='main.log',
                    filemode='w',
                    format='\n%(asctime)s - %(process)d - %(levelname)s\n%(message)s\n',
                    level=logging.INFO)


# Fetch ohlcv from huobi, store in pandas dataframe.
def fetching_ohlcv(EXCHANGE, pair, time_period):
    try:
        EXCHANGE.load_markets()
        bars = EXCHANGE.fetch_ohlcv(pair, timeframe=time_period, limit=100)
        df = pd.DataFrame(
            bars[:-1],
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception:
        logging.error(str(ccxt.errors.NetworkError))
        raise SystemExit("Please, check your Internet connection.")


# Calculate true range and average true range.
def tr_atr(df, period):
    df['previous close'] = df['close'].shift(1)
    df['high - low'] = df['high'] - df['low']
    df['high - Cp'] = abs(df['high'] - df['previous close'])
    df['low - Cp'] = abs(df['low'] - df['previous close'])
    tr = df[['high - low', 'high - Cp', 'low - Cp']].max(axis=1)

    df['TR'] = tr
    df['ATR'] = df['TR'].rolling(period).mean()

    return df


# Calculate super trend indicator.
def supertrend(df, pair, multiplier):
    high_low_sum = ((df['high'] + df['low'])/2)
    multiplied_atr = (multiplier * df['ATR'])
    df['upper band'] = high_low_sum + multiplied_atr
    df['lower band'] = high_low_sum - multiplied_atr
    df['in uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        # Add True / False to "in uptrend" column
        if df['close'][current] > df['upper band'][previous]:
            df['in uptrend'][current] = True
        elif df['close'][current] < df['lower band'][previous]:
            df['in uptrend'][current] = False
        else:
            df['in uptrend'][current] = df['in uptrend'][previous]

            if (df['in uptrend'][current]
                    and df['lower band'][current] < df['lower band'][previous]):
                df['lower band'][current] = df['lower band'][previous]
            if not (df['in uptrend'][current]
                    and df['upper band'][current] > df['upper band'][previous]):
                df['upper band'][current] = df['upper band'][previous]
    return df


# Calculate RSI indicator.
def rsi(df, period):
    df['chng'] = df['close'] - df['previous close']
    df['U'] = None
    df['D'] = None
    for row in range(1, len(df.index)):
        if df['chng'][row] > 0:
            df['U'][row] = df['chng'][row]
            df['D'][row] = 0
        elif df['chng'][row] < 0:
            df['U'][row] = 0
            df['D'][row] = abs(df['chng'][row])
        else:
            df['U'][row] = 0
            df['D'][row] = 0

    df['AvgU'] = df['U'].rolling(period).mean()
    df['AvgD'] = df['D'].rolling(period).mean()

    df['RS'] = df['AvgU'] / df['AvgD']
    df['RSI'] = 100 - 100/(1+df['RS'])

    return df


# Place sell / buy orders on huobi exchange.
def sell_buy(EXCHANGE, df, pair, quote_amount):
    # Need the latest close -> fetch ohlcv with 1-minute timeframe.
    ohlcv_minute = EXCHANGE.fetch_ohlcv(pair, timeframe='1m', limit=2)
    df_minute = pd.DataFrame(
        ohlcv_minute[:-1],
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    # Check acc balance for chosen pair.
    acc_balance = EXCHANGE.fetch_balance()['free']
    quote_balance = float(acc_balance[pair.split('/')[1]])
    base_balance = float(acc_balance[pair.split('/')[0]])

    # Limits & precision requirements for pair.
    market = EXCHANGE.market(pair)
    base_amt_min = float(market['limits']['amount']['min'])
    base_amt_max = float(market['limits']['amount']['max'])
    price_precis = float(market['precision']['price'])
    base_amnt_precis = float(market['precision']['amount'])

    # Rounding base balance for a sell order.
    rounded_base_balance = float(Decimal(str(base_balance)).quantize(
        Decimal(str(base_amnt_precis)),
        rounding=ROUND_DOWN))

    # Rounding price according to requirements.
    initial_price = float(df_minute.tail(1)['close'])
    rounded_price = float(Decimal(str(initial_price)).quantize(
        Decimal(str(price_precis)),
        rounding=ROUND_DOWN))

    # Rounding base amount according to requirements.
    base_amount = quote_amount / initial_price
    round_base_amt = float(Decimal(str(base_amount)).quantize(
        Decimal(str(base_amnt_precis)),
        rounding=ROUND_DOWN))

    last = len(df.index) - 1        # Last row
    previous = last - 1             # Previous row

    logging.info("Dataframe: " + str(df[['timestamp', 'in uptrend', 'RSI']].tail(3)))
    if ((df['in uptrend'][last] != df['in uptrend'][previous])
            or (df['RSI'][last] > 70) or (df['RSI'][last] < 30)):
        # Create buy order.
        if df['in uptrend'][last] or (df['RSI'][last] > 70):
            logging.info("Changed to uptrend -> buying!")
            logging.info("Quote balance before buying: " + str(quote_balance))
            if ((quote_balance >= quote_amount) and
                    (base_amt_min < round_base_amt < base_amt_max)):
                order_buy = EXCHANGE.create_order(
                    pair,
                    "market",
                    "buy",
                    round_base_amt,
                    rounded_price)
                logging.info("Buy order: " + str(order_buy))
                logging.info("Quote balance after buying: " + str(quote_balance))
            else:
                raise SystemExit("""
                Something went wrong with buy order.
                Make sure you have enough balance.
                If enough balance, check base amount limitations.
                Then try to run the program again.
                """)
        # Create sell order.
        elif (not df['in uptrend'][last]) or (df['RSI'][last] < 30):
            logging.info("Changed to downtrend -> selling!")
            logging.info("Base balance before selling: " + str(rounded_base_balance))
            if ((base_balance > 0) and
                    (base_amt_min < rounded_base_balance < base_amt_max)):
                order_sell = EXCHANGE.create_order(
                    pair,
                    "market",
                    "sell",
                    rounded_base_balance,
                    rounded_price)
                logging.info("Sell order: " + str(order_sell))
                logging.info("Base balance after selling: " + str(rounded_base_balance))
            else:
                logging.error(str("Sorry, sell order canceled. Your balance isn't enough."))


def main(pair, quote_amount, time_period='1h', period=15, multiplier=5):
    fetch_data = fetching_ohlcv(EXCHANGE, pair, time_period)

    TR_ATR = tr_atr(fetch_data, period)

    str = supertrend(TR_ATR, pair, multiplier)

    RSI = rsi(str, period)

    order = sell_buy(EXCHANGE, RSI, pair, quote_amount)


if __name__ == '__main__':
    schedule.every(1).hours.do(lambda: main(
        pair=str(sys.argv[1].upper()),
        quote_amount=float(sys.argv[2])))


while True:
    try:
        schedule.run_pending()
        time.sleep(2)
    except KeyboardInterrupt:
        sys.exit("\n\nThanks for using this app ^^\n\n")
