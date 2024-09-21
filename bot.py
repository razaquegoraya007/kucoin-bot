import time
from kucoin.client import Market, Trade
from datetime import datetime, timedelta
import pytz
from blessed import Terminal

# KuCoin API configuration
API_KEY = '66a782e0acd7ad00017ab3a2'
API_SECRET = '874ac514-c3c7-48d5-9b44-0a734423ea15'
API_PASSPHRASE = 'Brahim@1994'

market_client = Market(url='https://api.kucoin.com')
trade_client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE, url='https://api.kucoin.com')

# Trading strategy configuration
schedule = {
    0: "05:00",  # Monday
    1: "02:00",  # Tuesday
    2: "04:00",  # Wednesday
    3: "07:00",  # Thursday
    4: "06:00",  # Friday
    5: "01:00",  # Saturday
    6: "00:00"   # Sunday
}

initial_investment = 100  # Initial investment in USDT
profit_target_percentage = 0.001  # 0.1%
symbol = 'SOL-USDT'
term = Terminal()
total_sales = 0

def get_next_trade_time():
    now = datetime.now(pytz.utc)
    today_schedule = schedule[now.weekday()]
    next_trade_time = datetime.strptime(today_schedule, '%H:%M').replace(
        year=now.year, month=now.month, day=now.day, tzinfo=pytz.utc)

    if now >= next_trade_time:
        next_day = (now + timedelta(days=1)).weekday()
        next_trade_time = datetime.strptime(schedule[next_day], '%H:%M').replace(
            year=now.year, month=(now + timedelta(days=1)).month, day=(now + timedelta(days=1)).day, tzinfo=pytz.utc)

    return next_trade_time

def display_info(current_investment, target_price, next_trade_time, status, next_investment):
    now = datetime.now(pytz.utc)
    time_remaining = next_trade_time - now
    if time_remaining.total_seconds() < 0:
        next_trade_time = get_next_trade_time()
        time_remaining = next_trade_time - now

    info_table = [
        ["Current Time", now.strftime('%A: %H:%M:%S')],
        ["Time Remaining for Next Trade", str(time_remaining).split('.')[0]],
        ["Next Trade Time", next_trade_time.strftime('%A: %H:%M:%S')],
        ["Current Investment", f"{current_investment:.2f} USDT"],
        ["Next Trade Amount", f"{next_investment:.2f} USDT" if next_investment else "N/A"],
        ["Status", status],
        ["Total Sales", total_sales]
    ]
    print(term.move_y(0) + term.clear)
    for row in info_table:
        print(f"{row[0]:<30} | {row[1]}")
    time.sleep(1)  # Update every second

def trade():
    global total_sales
    current_investment = initial_investment

    while True:
        next_trade_time = get_next_trade_time()
        now = datetime.now(pytz.utc)
        time_until_next_trade = (next_trade_time - now).total_seconds()

        # Check every second if it's time to trade
        while time_until_next_trade > 0:
            status = f"Waiting for trade time ({next_trade_time.strftime('%A %H:%M:%S')})"
            display_info(current_investment, None, next_trade_time, status, None)
            time.sleep(1)
            now = datetime.now(pytz.utc)
            time_until_next_trade = (next_trade_time - now).total_seconds()

        # Time to trade
        try:
            # Buy SOL at market price
            order = trade_client.create_market_order(symbol, 'buy', funds=current_investment)
            sol_quantity = float(order.get('dealSize', 0))
            buy_price = float(order.get('price', 0))
            if sol_quantity <= 0:
                print("Error: SOL quantity is zero after purchase.")
                continue

            print(f"Purchased: {sol_quantity} SOL at {buy_price} USDT")

            # Update status after purchase
            status = "Waiting to sell..."
            target_price = buy_price * (1 + profit_target_percentage)
            print(f"Target price for selling: {target_price:.4f} USDT")

            # Monitor the price for selling
            while True:
                sol_current_price = float(market_client.get_ticker(symbol)['price'])
                current_value = sol_current_price * sol_quantity
                if current_value <= 0:
                    print("Error: Current value is zero after monitoring.")
                    break
                if sol_current_price <= 0:
                    print("Error: SOL price is zero after monitoring.")
                    break
                print(f"Current SOL price: {sol_current_price:.4f}, Current value: {current_value:.4f}, Target: {target_price:.4f}")

                # Check if the target profit percentage is met
                if sol_current_price >= target_price:
                    print("Target met. Selling...")
                    try:
                        sell_order = trade_client.create_market_order(symbol, 'sell', size=sol_quantity)
                        if 'orderId' in sell_order:
                            print(f"Sold: {sol_quantity} SOL at {sol_current_price} USDT")
                            total_sales += 1
                            current_investment = current_value
                            status = "Trade completed. Waiting to buy..."
                            break  # Exit the monitoring loop after successful sale
                        else:
                            print("Error during selling. Retrying...")
                            print(f"Sell Order Response: {sell_order}")
                            time.sleep(0.5)  # Brief delay before retrying the sale
                    except Exception as e:
                        print(f"Error during selling: {e}")
                        time.sleep(0.5)  # Brief delay before retrying the sale

                # Update display information
                display_info(current_investment, target_price, next_trade_time, status, current_investment)
                time.sleep(1)

        except Exception as e:
            status = f"Error during purchase: {e}"
            display_info(current_investment, None, next_trade_time, status, None)
            time.sleep(1)  # Pause before retrying after an error

if __name__ == "__main__":
    trade()
