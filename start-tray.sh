#!/bin/bash
source venv/bin/activate
python main.py --tray --port 7777 "$@"
