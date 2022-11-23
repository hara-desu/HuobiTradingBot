This is the first version of my first project. 
(So, now you know you have to be sceptical while using it :D )
The algorithm fetches data from huobi exchange, then calculates super trend and RSI indicators.
It uses hourly data for calculation, thus every hour it refreshes indicators and checks if it's time to buy or sell crypto.
If indicators show a change to uptrend, the algorithm will place a buy order. 
If indicators show a change to downtrend, it will place a sell order.

You can see all trading history for the current run in main.log file.

To run this algorithm you have to be a huobi account holder 
and, obviously, have enough balance in spot to buy or sell.

I plan to improve this project and add new features in the future.
If anyone ever discovers the project, please, feel free to make suggestions on how to improve the code.

# Prerequisites
- Account on huobi.com, Secret + API key
- Basic understanding of super trend and RSI indicators and their calculation

# Running the app
1. Install dependencies 'pip install -r requirements.txt'
2. Add your huobi API key and secret key to config.py
3. Run the script from command line : python3 main.py (args)
- Enter 2 arguments in the following order
  1. Trading pair (ex. ETH/USDT where ETH - base currency, USDT - quote currency)
  2. Trading amount in quote currency (float num)

  Example: python3 main.py BTC/USDT 3
  - means that you want to spend 3 USDT to buy BTC
  - sell amount of BTC will be calculated on the basis of quote amount and latest close price

# External modules used
- ccxt : connect to huobi exchange
- pandas : to store exchange and calc data
- schedule : to schedule tasks

