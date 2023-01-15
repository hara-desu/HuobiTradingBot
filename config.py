# Huobi API keys

HUOBI_API_KEY = ''
HUOBI_SECRET_KEY = ''

# Period for calculation of ATR and RSI
'''
See formulas for ATR & RSI calc and why you need period var:
ATR : https://www.investopedia.com/terms/a/atr.asp
RSI : https://www.investopedia.com/terms/r/rsi.asp
'''
period = 15

# Multiplier for supertrend calculation
'''
See the formulas for RSI and why you need multiplier var:
https://www.tradingview.com/support/solutions/43000634738-supertrend/
'''

multiplier = 5

# Time-period for fetching OHLCV market data from Huobi
'''
I set time-period to hourly trade by default.
Huobi doesn't seem to provide yesterday's closing price through API.
Thus, trading on a daily basis seems pointless.

You can set it to 1 minute '1m', day '1d', month '1d' or year '1y'.
'''

time_period = '1h'
