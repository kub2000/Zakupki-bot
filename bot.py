import telebot
import requests
from datetime import datetime, timedelta

TOKEN = 'сюда вставь свой токен'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'run'])
def send_links(message):
    today = datetime.now()
    if today.weekday() == 6:  # если воскресенье
        target_date = today - timedelta(days=2)
    else:
        target_date = today - timedelta(days=1)

    date_str = target_date.strftime("%d.%m.%Y")
    
    url = f"http://zakupki.gov.kg/popp/viewTender/search.xhtml?dateFrom={date_str}&dateTo={date_str}&cpvCodesString=&searchByName=&lotCpvCodesString=&searchType=0&purchaseType=0&methodType=0&status=0&regionsString="

    response = requests.get(url)
    
    if response.status_code == 200:
        bot.send_message(message.chat.id, f"Ссылка на тендеры за {date_str}:\n{url}")
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к сайту.")

bot.infinity_polling()