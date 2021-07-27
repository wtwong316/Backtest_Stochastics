#!/bin/bash
source ./venv/bin/activate
python backtest_stochastic.py -i $1 -s $2 -t $3

