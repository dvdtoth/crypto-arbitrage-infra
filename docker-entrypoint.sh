#!/bin/bash
python ./src/$(head -1 ./config/$CONFIG |cut -d" " -f2) ./config/$CONFIG