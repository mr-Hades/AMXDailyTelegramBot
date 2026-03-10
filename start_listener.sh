#!/bin/bash
cd ~/AMXDailyTelegramBot-main
export TELEGRAM_BOT_TOKEN="8396281408:AAHOLRb6H2-ugXHjuUewfhxHOuoYXtbVSsc"
export TELEGRAM_CHAT_ID="-1003799558853"

# Kill any existing listener
pkill -f "bonds_news.py --listen" 2>/dev/null
sleep 1

# Start the listener (-u = unbuffered output)
nohup /usr/bin/python3 -u bonds_news.py --listen >> ~/bonds-listener.log 2>&1 &
echo "Listener started with PID: $!"
