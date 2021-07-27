import requests
import json
import sys, getopt
from pprint import pprint

# get data from elasticsearch server 
def get_data(inputfile, symbol):
    url = 'http://localhost:9200/fidelity28_fund/_search?pretty'
    with open(inputfile) as f:
        payload = json.load(f)
    payload_json = json.dumps(payload)
    payload_json = payload_json % symbol
    headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
    r = requests.post(url, data=payload_json, headers=headers)
    return r.text

# get the command line parameters for the trading policy and the ticker symbol
def get_opt(argv):
    inputfile = 'backtest_stochastic.json'
    symbol = 'FDEV'
    sf_type = 'F_Type'
    try:
        opts, args = getopt.getopt(argv, "hi:s:t:")
    except getopt.GetoptError:
        print('backtest_stochstics -i <inputfile> -s <symbol> -t <fast/slow type>')
        print('example: backtest_stochastics -i backtest_stochastic.json -s FDEV -t F_Type/S_Type')
        sys.exit(-1)

    for opt, arg in opts:
        if opt == '-h':
            print('backtest_stochastics -i <inputfile> -s <symbol> -t <fast/slow type>')
            print('example: backtest_rsi -i backtest_stochastic.json -s FDEV -t F_Type/S_Type')
            sys.exit(0)
        elif opt in ('-i'):
            inputfile = arg
        elif opt in ('-s'):
            symbol = arg
        elif opt in ('-t'):
            sf_type = arg

    if inputfile == '':
        print("No input file!")
        sys.exit(-1)

    return inputfile, symbol, sf_type


# parse the response data and refine the buy/sell signal
def parse_data(resp, type):
    result = json.loads(resp)
    aggregations = result['aggregations']
    if aggregations and 'Backtest_Stochastic' in aggregations:
        Backtest_Stochastics = aggregations['Backtest_Stochastic']

    transactions = []
    hold = False
    if Backtest_Stochastics and 'buckets' in Backtest_Stochastics:
        for bucket in Backtest_Stochastics['buckets']:
            transaction = {}
            transaction['date'] = bucket['key_as_string']
            transaction['Daily'] = bucket['Daily']['value']
            # honor buy signal if there is no share hold
            if bucket[type]['value'] == -1:
                transaction['original'] = 'buy'
                if not hold:
                    transaction['buy_or_sell'] = 'buy'
                else:
                    transaction['buy_or_sell'] = 'hold'
                hold = True
            # honor sell signal if there is a share hold
            elif bucket[type]['value'] == 1:
                transaction['original'] = 'sell'
                if hold:
                    transaction['buy_or_sell'] = 'sell'
                else:
                    transaction['buy_or_sell'] = 'hold'
                hold = False
            # for other situations, just hold the action
            else:
                transaction['original'] = 'hold'
                transaction['buy_or_sell'] = 'hold'
            transactions.append(transaction)

    return transactions


def report(transactions, type):
    print('Transaction Sequence for : ' + type)
    print('-' * 80)
    pprint(transactions, width=120)
    print('-' * 80)
    print()

    profit = 0.0;
    num_of_buy = 0
    num_of_sell = 0
    buy_price = 0;
    win = 0
    lose = 0
    max_buy_price = 0
    for transaction in transactions:
        if transaction['buy_or_sell'] == 'buy':
           num_of_buy += 1
           buy_price = transaction['Daily']
           profit -= transaction['Daily']
           max_buy_price = transaction['Daily'] if max_buy_price < transaction['Daily'] else max_buy_price
        elif transaction['buy_or_sell'] == 'sell' and buy_price > 0:
           profit += transaction['Daily']
           if transaction['Daily'] > buy_price:
               win += 1
           else:
               lose += 1
           buy_price = 0
           num_of_sell += 1

    if buy_price > 0:
        profit += transactions[-1]['Daily']
        if transaction['Daily'] > buy_price:
            win += 1
        else:
            lose += 1

    print('number of buy:      %8d' % (num_of_buy))
    print('number of sell:     %8d' % (num_of_sell))
    print('number of win:      %8d' % (win))
    print('number of lose:     %8d' % (lose))
    print('total profit:       %8.2f' % (profit))
    if num_of_buy > 0:
        print('profit/transaction: %8.2f' % (profit/num_of_buy))
    print('maximum buy price:  %8.2f' % max_buy_price)
    if max_buy_price > 0:
        print('profit percent:     %8.2f%%' % (profit*100/max_buy_price))


def main(argv):
    inputfile, symbol, type = get_opt(argv) 
    resp = get_data(inputfile, symbol)
    transactions = parse_data(resp, type)
    report(transactions, type)


if __name__ == '__main__':
    main(sys.argv[1:])
