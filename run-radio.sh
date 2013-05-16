#!/bin/bash

cd /home/pi/PiRadio
#exec python2 -u run-radio.py > /home/pi/RpiRadio/logs/radio.log 2>&1
exec python -u run-radio.py > /dev/null 2>&1
