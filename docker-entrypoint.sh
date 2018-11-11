#!/bin/bash
if [ "$POLLER_CONFIG" = "cmc-poller/cmc.yml" ]; then
    python ./src/cmc-poller.py ./config/$POLLER_CONFIG
else
    python ./src/exchange-poller.py ./config/$POLLER_CONFIG
fi