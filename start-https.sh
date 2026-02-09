#!/bin/bash
source venv/bin/activate
python main.py --ssl --ssl-cert "/home/daria/.daria/ssl/cert.pem" --ssl-key "/home/daria/.daria/ssl/key.pem" --host 0.0.0.0 --port 7777 "$@"
