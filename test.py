import time, math, asyncio, json, threading
from datetime import datetime
from pocketoptionapi.stable_api import PocketOption
import pocketoptionapi.global_value as global_value
#import talib.abstract as ta
import numpy as np
import pandas as pd
global_value.loglevel = 'INFO'

# Session configuration
start_counter = time.perf_counter()

### REAL SSID Format::
#ssid = """42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"aa11b2345c67d89e0f1g23456h78i9jk\\";s:10:\\"ip_address\\";s:11:\\"11.11.11.11\\";s:10:\\"user_agent\\";s:111:\\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36\\";s:13:\\"last_activity\\";i:1234567890;}1234a5b678901cd2efghi34j5678kl90","isDemo":0,"uid":12345678,"platform":2}]"""
#demo = False

### DEMO SSID Format::
#ssid = """42["auth",{"session":"abcdefghijklm12nopqrstuvwx","isDemo":1,"uid":12345678,"platform":2}]"""
#demo = True

ssid = """42["auth",{"session":"3v53gql1jsok3jlchm47fu3csl","isDemo":1,"uid":101287768,"platform":2}]"""
demo = True

min_payout = 80
period = 30
expiration = 60
api = PocketOption(ssid,demo)

# Connect to API
api.connect()


def get_payout():
    try:
        d = global_value.PayoutData
        d = json.loads(d)
        for pair in d:
            # |0| |  1  |  |  2  |  |  3  | |4 | 5 |6 | 7 | 8| 9| 10 |11| 12| 13        | 14   | | 15,                                                                                                                                                                                     |  16| 17| 18        |
            # [5, '#AAPL', 'Apple', 'stock', 2, 50, 60, 30, 3, 0, 170, 0, [], 1743724800, False, [{'time': 60}, {'time': 120}, {'time': 180}, {'time': 300}, {'time': 600}, {'time': 900}, {'time': 1800}, {'time': 2700}, {'time': 3600}, {'time': 7200}, {'time': 10800}, {'time': 14400}], -1, 60, 1743784500],
            if len(pair) == 19:
                global_value.logger('id: %s, name: %s, typ: %s, active: %s' % (str(pair[1]), str(pair[2]), str(pair[3]), str(pair[14])), "DEBUG")
                #if pair[14] == True and pair[5] >= min_payout and "_otc" not in pair[1] and pair[3] == "currency":         # Get all non OTC Currencies with min_payout
                if pair[14] == True and pair[5] >= min_payout and "_otc" in pair[1]:                                       # Get all OTC Markets with min_payout
                #if pair[14] == True and pair[3] == "cryptocurrency" and pair[5] >= min_payout and "_otc" not in pair[1]:   # Get all non OTC Cryptocurrencies
                #if pair[14] == True:                                                                                       # Get All that online
                    p = {}
                    p['id'] = pair[0]
                    p['payout'] = pair[5]
                    p['type'] = pair[3]
                    global_value.pairs[pair[1]] = p
        return True
    except:
        return False


def get_df():
    try:
        i = 0
        for pair in global_value.pairs:
            i += 1
            df = api.get_candles(pair, period)
            global_value.logger('%s (%s/%s)' % (str(pair), str(i), str(len(global_value.pairs))), "INFO")
            time.sleep(1)
        return True
    except:
        return False


def buy(amount, pair, action, expiration):
    global_value.logger('%s, %s, %s, %s' % (str(amount), str(pair), str(action), str(expiration)), "INFO")
    result = api.buy(amount=amount, active=pair, action=action, expirations=expiration)
    i = result[1]
    result = api.check_win(i)
    if result:
        global_value.logger(str(result), "INFO")


def buy2(amount, pair, action, expiration):
    global_value.logger('%s, %s, %s, %s' % (str(amount), str(pair), str(action), str(expiration)), "INFO")
    result = api.buy(amount=amount, active=pair, action=action, expirations=expiration)


def make_df(df0, history):
    df1 = pd.DataFrame(history).reset_index(drop=True)
    df1 = df1.sort_values(by='time').reset_index(drop=True)
    df1['time'] = pd.to_datetime(df1['time'], unit='s')
    df1.set_index('time', inplace=True)
    # df1.index = df1.index.floor('1s')

    df = df1['price'].resample(f'{period}s').ohlc()
    df.reset_index(inplace=True)
    df = df.loc[df['time'] < datetime.fromtimestamp(wait(False))]

    if df0 is not None:
        ts = datetime.timestamp(df.loc[0]['time'])
        for x in range(0, len(df0)):
            ts2 = datetime.timestamp(df0.loc[x]['time'])
            if ts2 < ts:
                df = df._append(df0.loc[x], ignore_index = True)
            else:
                break
        df = df.sort_values(by='time').reset_index(drop=True)
        df.set_index('time', inplace=True)
        df.reset_index(inplace=True)

    return df




def strategie():
    for pair in global_value.pairs:
        if 'history' in global_value.pairs[pair]:
            history = []
            history.extend(global_value.pairs[pair]['history'])

            if 'dataframe' in global_value.pairs[pair]:
                df = make_df(global_value.pairs[pair]['dataframe'], history)
            else:
                df = make_df(None, history)

            if len(df) < 20:
                continue

            # Example indicator: Simple Moving Averages
            df['sma_fast'] = df['close'].rolling(window=5).mean()
            df['sma_slow'] = df['close'].rolling(window=10).mean()

            if df['sma_fast'].iloc[-2] < df['sma_slow'].iloc[-2] and df['sma_fast'].iloc[-1] > df['sma_slow'].iloc[-1]:
                # Crossover detected – BUY
                buy(amount=1, pair=pair, action="call", expiration=expiration)

            elif df['sma_fast'].iloc[-2] > df['sma_slow'].iloc[-2] and df['sma_fast'].iloc[-1] < df['sma_slow'].iloc[-1]:
                # Crossunder detected – PUT
                buy(amount=1, pair=pair, action="put", expiration=expiration)

    

def prepare_get_history():
    try:
        data = get_payout()
        if data: return True
        else: return False
    except:
        return False

def prepare():
    try:
        data = get_payout()
        if data:
            data = get_df()
            if data: return True
            else: return False
        else: return False
    except:
        return False


def wait(sleep=True):
    dt = int(datetime.now().timestamp()) - int(datetime.now().second)
    if period == 60:
        dt += 60
    elif period == 30:
        if datetime.now().second < 30: dt += 30
        else: dt += 60
        if not sleep: dt -= 30
    elif period == 15:
        if datetime.now().second >= 45: dt += 60
        elif datetime.now().second >= 30: dt += 45
        elif datetime.now().second >= 15: dt += 30
        else: dt += 15
        if not sleep: dt -= 15
    elif period == 10:
        if datetime.now().second >= 50: dt += 60
        elif datetime.now().second >= 40: dt += 50
        elif datetime.now().second >= 30: dt += 40
        elif datetime.now().second >= 20: dt += 30
        elif datetime.now().second >= 10: dt += 20
        else: dt += 10
        if not sleep: dt -= 10
    elif period == 5:
        if datetime.now().second >= 55: dt += 60
        elif datetime.now().second >= 50: dt += 55
        elif datetime.now().second >= 45: dt += 50
        elif datetime.now().second >= 40: dt += 45
        elif datetime.now().second >= 35: dt += 40
        elif datetime.now().second >= 30: dt += 35
        elif datetime.now().second >= 25: dt += 30
        elif datetime.now().second >= 20: dt += 25
        elif datetime.now().second >= 15: dt += 20
        elif datetime.now().second >= 10: dt += 15
        elif datetime.now().second >= 5: dt += 10
        else: dt += 5
        if not sleep: dt -= 5
    elif period == 120:
        dt = int(datetime(int(datetime.now().year), int(datetime.now().month), int(datetime.now().day), int(datetime.now().hour), int(math.floor(int(datetime.now().minute) / 2) * 2), 0).timestamp())
        dt += 120
    elif period == 180:
        dt = int(datetime(int(datetime.now().year), int(datetime.now().month), int(datetime.now().day), int(datetime.now().hour), int(math.floor(int(datetime.now().minute) / 3) * 3), 0).timestamp())
        dt += 180
    elif period == 300:
        dt = int(datetime(int(datetime.now().year), int(datetime.now().month), int(datetime.now().day), int(datetime.now().hour), int(math.floor(int(datetime.now().minute) / 5) * 5), 0).timestamp())
        dt += 300
    elif period == 600:
        dt = int(datetime(int(datetime.now().year), int(datetime.now().month), int(datetime.now().day), int(datetime.now().hour), int(math.floor(int(datetime.now().minute) / 10) * 10), 0).timestamp())
        dt += 600
    if sleep:
        global_value.logger('======== Sleeping %s Seconds ========' % str(dt - int(datetime.now().timestamp())), "INFO")
        return dt - int(datetime.now().timestamp())

    return dt


def start():
    while global_value.websocket_is_connected is False:
        time.sleep(0.1)
    time.sleep(2)
    saldo = api.get_balance()
    global_value.logger('Account Balance: %s' % str(saldo), "INFO")
    prep = prepare()
    if prep:
        while True:
            strategie()
            time.sleep(wait())


def start_get_history():
    while global_value.websocket_is_connected is False:
        time.sleep(0.1)
    time.sleep(2)
    saldo = api.get_balance()
    global_value.logger('Account Balance: %s' % str(saldo), "INFO")
    prep = prepare_get_history()
    if prep:
        i = 0
        for pair in global_value.pairs:
            i += 1
            global_value.logger('%s (%s/%s)' % (str(pair), str(i), str(len(global_value.pairs))), "INFO")
            if not global_value.check_cache(str(global_value.pairs[pair]["id"])):
                time_red = int(datetime.now().timestamp()) - 86400 * 7
                df = api.get_history(pair, period, end_time=time_red)


if __name__ == "__main__":
    start()
    end_counter = time.perf_counter()
    rund = math.ceil(end_counter - start_counter)
    # print(f'CPU-gebundene Task-Zeit: {rund} {end_counter - start_counter} Sekunden')
    global_value.logger("CPU-gebundene Task-Zeit: %s Sekunden" % str(int(end_counter - start_counter)), "INFO")

