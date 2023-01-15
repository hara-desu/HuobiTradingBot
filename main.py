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

# Create variable to access Huobi exchange
EXCHANGE = ccxt.huobi({
    "apiKey": config.HUOBI_API_KEY,
    "secret": config.HUOBI_SECRET_KEY})

# Config logging
logging.basicConfig(filename='main.log',
                    filemode='a',
                    format='\n%(asctime)s - %(levelname)s\n%(message)s\n',
                    level=logging.INFO)


# Fetch ohlcv from huobi, store in pandas dataframe.
def fetching_ohlcv(EXCHANGE, pair, time_period):
    try:
        EXCHANGE.load_markets()
        bars = EXCHANGE.fetch_ohlcv(pair, timeframe=time_period, limit=25)
        df = pd.DataFrame(
            bars[:-1],
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logging.info("fetching_ohlcv - success")
        return df
    except Exception:
        logging.error(f"fetching_ohlcv failed : {str(ccxt.errors.NetworkError)}")
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


# Calculate super trend indicator
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
    df['RSI'] = 100 - 100/(1 + df['RS'])

    logging.info("dataframe prep - success")

    return df


# Check if enough balance and order requirements are met
def checking(quote_balance, quote_amount, base_amt_min,
             base_amt_max, base_amount, initial_price):
    # Check if enough quote balance to buy
    if quote_balance >= quote_amount:
        pass
    else:
        logging.info("Quote amt exceeds quote balance -> SystemExit raised.")
        raise SystemExit(f'''
            Lacking quote balance.
            Your quote balance is {quote_balance}.
            But asked sell order amount is {quote_amount}.
            ''')

    # Check if min and max order requirements are met
    if base_amt_min < base_amount < base_amt_max:
        pass
    else:
        logging.info("Min/Max order amount requirements not met -> SystemExit raised.")
        raise SystemExit(f'''
            Your order amount doesn't meet Huobi exchange requirements.\n
            Check the following requirements and run the program again:\n
            Min/Max quote amt : 
            {base_amt_min*initial_price} / {base_amt_max*initial_price}\n
            Your quote amt : 
            {base_amount * initial_price}
            ''')


# Place sell / buy orders on huobi exchange
# Base - amt in buying curr (before /), quote - amt in selling curr (after /)
def sell_buy(EXCHANGE, df, pair, quote_amount):
    # Need the latest close -> fetch ohlcv with 1-minute timeframe
    ohlcv_minute = EXCHANGE.fetch_ohlcv(pair, timeframe='1m', limit=2)
    df_minute = pd.DataFrame(
        ohlcv_minute[:-1],
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    # Check acc balance for chosen pair
    acc_balance = EXCHANGE.fetch_balance()['free']
    quote_balance = float(acc_balance[pair.split('/')[1]])
    base_balance = float(acc_balance[pair.split('/')[0]])

    # Limits & precision requirements for pair
    market = EXCHANGE.market(pair)
    base_amt_min = float(market['limits']['amount']['min'])
    base_amt_max = float(market['limits']['amount']['max'])
    price_precis = float(market['precision']['price'])
    base_amnt_precis = float(market['precision']['amount'])

    # Rounding base balance for a sell order
    rounded_base_balance = float(Decimal(str(base_balance)).quantize(
        Decimal(str(base_amnt_precis)),
        rounding=ROUND_DOWN))

    # Rounding price according to requirements
    initial_price = float(df_minute.tail(1)['close'])
    rounded_price = float(Decimal(str(initial_price)).quantize(
        Decimal(str(price_precis)),
        rounding=ROUND_DOWN))

    # Rounding base amount according to requirements
    base_amount = quote_amount / initial_price
    round_base_amt = float(Decimal(str(base_amount)).quantize(
        Decimal(str(base_amnt_precis)),
        rounding=ROUND_DOWN))

    # Check if enough quote balance & min/max requirements
    checking(quote_balance, quote_amount, base_amt_min,
             base_amt_max, base_amount, initial_price)

    last = len(df.index) - 1        # Last row
    previous = last - 1             # Previous row

    logging.info(f"Dataframe:\n {str(df[['timestamp', 'in uptrend', 'RSI']].tail(3))}")
    if ((df['in uptrend'][last] != df['in uptrend'][previous])
            or (df['RSI'][last] > 70) or (df['RSI'][last] < 30)):
        # Create buy order.
        if df['in uptrend'][last] or (df['RSI'][last] > 70):
            logging.info(f'''
            Changed to uptrend -> buying!
            Quote/Base balance before buying: 
            {str(quote_balance)} / {str(base_balance)}
            ''')
            order_buy = EXCHANGE.create_order(
                pair,
                "market",
                "buy",
                round_base_amt,
                rounded_price)
            logging.info(f'''
                Buy order: {str(order_buy['info'])}, id is {str(order_buy['id'])}
            ''')
        # Create sell order.
        elif (not df['in uptrend'][last]) or (df['RSI'][last] < 30):
            logging.info(f'''
            Changed to downtrend -> selling!
            Quote/Base balance before sell: 
            {str(quote_balance)}/{str(base_balance)}
            ''')
            if base_balance > round_base_amt:
                order_sell = EXCHANGE.create_order(
                    pair,
                    "market",
                    "sell",
                    rounded_base_balance,
                    rounded_price)
                logging.info(f'''
                Sell order: {str(order_sell['info'])}, id is {str(order_sell['id'])}
                ''')
            else:
                logging.error('''
                Sorry, sell order canceled. Your balance isn't enough.\n
                Program continues to run until buy order placed.
                ''')


def main(pair,
         quote_amount,
         time_period=config.time_period,
         period=config.period,
         multiplier=config.multiplier):

    logging.info("Run started")

    fetch_data = fetching_ohlcv(EXCHANGE, pair, time_period)

    TR_ATR = tr_atr(fetch_data, period)

    str = supertrend(TR_ATR, pair, multiplier)

    RSI = rsi(str, period)

    order = sell_buy(EXCHANGE, RSI, pair, quote_amount)

    logging.info("End run")


if __name__ == '__main__':
    schedule.every(1).minutes.do(lambda: main(
        pair=str(sys.argv[1].upper()),
        quote_amount=float(sys.argv[2])))


while True:
    try:
        schedule.run_pending()
        time.sleep(2)
    except KeyboardInterrupt:
        sys.exit("\n\nThanks for using this app ^^\n\n")
