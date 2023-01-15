This program works by fetching data from huobi market exchange, then calculates supertrend and RSI indicators.
Based on these indicators it decides whether to buy or sell or hold crypto.
Basically, if indicators show a change to uptrend, the algorithm will place a buy order for base currency. 
If there's a change to downtrend, the algorithm will place a sell order and wait for an uptrend to buy again.

To run this algorithm you have to be a huobi account holder and get an API key.
Here's a guide on how to do it : https://account.huobi.com/support/en-us/detail/360000203002?invite_code=5fzi7

To start trading you only need enough amount in quote currency to place a buy order.
Also, you can configure variables for calculation in config.py file.

I plan to improve this project, fix bugs, run more tests and add new features in the future.

### I don't guarantee that you'll wield profits using this program. This is just my first study project.

# Prerequisites
- Account on huobi.com and API key
- Python 3.0 or above
- Quote currency balance > order amount
- Internet connection

# Running the app
1. Install dependencies 'pip install -r requirements.txt'
2. Add your huobi API key and secret key to config.py
3. If necessary add other changes to config.py
4. Run the script from command line : python3 main.py (args)

- args
  - Trading pair (ex. ETH/USDT where ETH - base currency, USDT - quote currency)
  - Trading amount in quote currency (float num)

- Example: python3 main.py BTC/USDT 11
  - means that you want to spend 11 USDT to buy BTC
  - sell amount of BTC will be calculated on the basis of quote amount and latest close price

# External modules used
- ccxt : connect to huobi exchange
- pandas : to store exchange and calc data
- schedule : to schedule tasks

# As for the rest of it, good luck (ﾉ≧ㅅ≦)ﾉ*:･ﾟ✧
