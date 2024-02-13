
import asyncio
import markdown
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Text
from langchain.document_loaders import NewsURLLoader
import re
import os
import openai
import pandas as pd
from openai import OpenAI
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model_name='gpt-4-0125-preview', temperature=0.7, openai_api_key = os.environ['OPENAI_API_KEY'],max_tokens=1000)

CSV_FILE_PATH = 'allowed_users.csv'

bot = Bot(token='6799661102:AAFPZS-sYon5h1XGymwILNV00Xhy4BabbSc')
dp = Dispatcher(bot)

data = {}
emoji_pattern = r"[\U0001F600-\U0001F64F]+"

# Ensure CSV file exists and initialize it if not
def init_csv():
    if not os.path.exists(CSV_FILE_PATH):
        df = pd.DataFrame(columns=[ "username"])
        df.to_csv(CSV_FILE_PATH, index=False)

# Add a user to the CSV file
def add_user_to_csv( username):
    df = pd.read_csv(CSV_FILE_PATH)
    df = df.append({ "username": username}, ignore_index=True)
    df.to_csv(CSV_FILE_PATH, index=False)

# Remove a user from the CSV file
def remove_user_from_csv(username):
    df = pd.read_csv(CSV_FILE_PATH)
    df = df[df.username != username]
    df.to_csv(CSV_FILE_PATH, index=False)

# Check if a user is allowed
def is_user_allowed(username):
    df = pd.read_csv(CSV_FILE_PATH)
    return not df[df['username'].astype(str) == str(username)].empty


def generate_with_gpt3(prompt):
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    response = llm.invoke(prompt).content
    return response


def split_message(text, max_length=4096):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def generate_post_content(choice, link, text, event, emojis):
    link_text = f'(Link - {link})' if choice == "link" else ''
    emoji_text = 'Thematic emojis are mandatory in the text. (3-4 emojis per paragraph).' if emojis else 'Emojis are not allowed in the text except for `▪️`.'
    if event:
        # Generating event post content
        return f'''
        Generate a post fully in Ukrainian based on this article {link_text}.
        Here is the article:
         ```{text}```
        Шаблон для подій:

        ​​🏤🏤🏤#МІСТО
        
        *назва події жирним шрифтом

        🗓️*дата *назва місяця ⏰*години проведення
        📍*адреса у вигляді гіперпосилання на googlemap
        
        🎫 квитки за посилання *гіпеопосилання на лінк з квитками *текст жиний
        
        *Опис події
        
        Here is an real example:
        
        ❌❌❌**#АМСТЕРДАМ**

        🍷**Дегустація натуральних вин з українськими стравами🇺🇦**

        🗓️**18 січня ⏰17:00-22:00**

        📍**Rebel Wines de Pijp**

        Van Woustraat 202A, 1073 NA Amsterdam, Netherlands

        🎫 **вхід 15€** *(входить дегустаційний набір вин)*

        🍇**Спробуйте натуральні вина** з Словаччини, Чехії, Австрії та інших країн Східної Європи, а також традиційні українські страви! 🥟**Вареники, чебуреки, налисники** та багато іншого чекають на вас!
        '''
    else:
        # Generating general post content
        return f'''
            Generate post fully in markdown format for telergam message in Ukrainian based on this article {link_text}.
            Here is the article:
            ```{text}```
            Use these rules:
                -  Never use period "." in the of sentence after emojis.
                Headline:
                    1. The title should convey the main idea of the post. (Maximum 5-10 words)
                    2. It is always bold(use markdown format "*<text>*").
                    3. 1-2 thematic emojis are always used at the beginning of the title.
                    4. A period is always placed at the end of the title.
                    5. The title should be in the very beginning of the post.

                Introduction:
                    1. There is always a blank line after the title.
                    2. Then there can be 1-2 sentences that mention an interesting fact from the material.
                    3. This text is written in italics(use markdown format "_<text>_"), and emojis are not used.

                Main Text:
                    1. This is a maximum of 200-300 characters.
                    2. The text can be divided into 2-3 paragraphs.
                    3. Important parts of the text and words are ALWAYS highlighted in bold("*<text>*").
                    4. {emoji_text}
                    5. At the end of a sentence, if there is an emoji, a period is not placed. Correct: "...the end✊". Incorrect: "...the end.✊".
                    6. If a list of something is enumerated, square emojis ▪️ are used in the beginning. Incorrect: "1. The beginning". Correct: "▪️The beginning".
                    7. The text never uses quotes “”, but instead uses «».
                    8. A period is always placed at the end of the main text.
            '''

# Menu buttons
text_button = InlineKeyboardButton('📝 Текст', callback_data='text')
link_button = InlineKeyboardButton('🔗 Посилання', callback_data='link')
emojis_button = InlineKeyboardButton('✨ З емодзі', callback_data='emojis')
no_emojis_button = InlineKeyboardButton('🚫 Без емодзі', callback_data='no_emojis')
no_event_button = InlineKeyboardButton('👉Звичайний пост', callback_data='no_event')
event_button = InlineKeyboardButton('🎉 Подія', callback_data='event')


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if not is_user_allowed(message.from_user.username) or message.from_user.username == 'ukraine_nl':
        await message.reply("You do not have permission to use this bot.")
        return
    keyboard_markup = InlineKeyboardMarkup().add( no_event_button,event_button)
    await message.reply("Welcome! You have permission to use this bot.")
    if message.from_user.username == 'ukraine_nl':
        await message.reply("To manage user's list use /add_user and /remove_user commands.")
    await bot.send_message(message.from_user.id, '🌟 Виберіть, чи буде ваша публікація пов’язана з подією:', reply_markup=keyboard_markup)

# Command to add a user
@dp.message_handler(commands=['add_user'], commands_prefix='!/')
async def add_user_command(message: types.Message):
    # Only allow a specific user to add others for security reasons
    if message.from_user.username != 'ukraine_nl':
        await message.reply("You don't have permission to use this command.")
        return
    
    args = message.get_args().split()
    if len(args) != 2:
        await message.reply("Usage: /add_user @username")
        return
    
    username = args
    add_user_to_csv(username.strip('@'))
    await message.reply(f"User {username} added successfully.")

# Command to remove a user
@dp.message_handler(commands=['remove_user'], commands_prefix='!/')
async def remove_user_command(message: types.Message):
    if message.from_user.username != 'ukraine_nl':
        await message.reply("You don't have permission to use this command.")
        return
    
    args = message.get_args().split()
    if len(args) != 1:
        await message.reply("Usage: /remove_user @username")
        return
    
    username = args[0].strip('@')
    remove_user_from_csv(username)
    await message.reply(f"User {username} removed successfully.")

# Handler for event selection
@dp.callback_query_handler(lambda callback_query: callback_query.data in ('event', 'no_event'))
async def get_event(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)
    data[callback_query.from_user.id] = {'event': (callback_query.data == 'event')}
    keyboard_markup = InlineKeyboardMarkup().add(text_button, link_button)
    await bot.send_message(callback_query.from_user.id, 'Виберіть, як ви хочете ввести інформацію для публікації:', reply_markup=keyboard_markup)

# Handler for text or link input type selection
@dp.callback_query_handler(lambda callback_query: callback_query.data in ('text', 'link'))
async def get_input_type(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)
    data[callback_query.from_user.id]['input_type'] = callback_query.data
    keyboard_markup = InlineKeyboardMarkup().add(emojis_button, no_emojis_button)
    await bot.send_message(callback_query.from_user.id, 'Будуть емодзі в публікації?', reply_markup=keyboard_markup)

# Handler for emoji selection
@dp.callback_query_handler(lambda callback_query: callback_query.data in ('emojis', 'no_emojis'))
async def get_emojis(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)
    data[callback_query.from_user.id]['emojis'] = (callback_query.data == 'emojis')
    await bot.send_message(callback_query.from_user.id, 'Введіть текст або посилання для публікації:')

# Handler for receiving the publication text or link
@dp.message_handler(lambda message: message.text)
async def get_text_for_publication(message: types.Message):
    user_data = data[message.from_user.id]
    if user_data['input_type'] == 'text':
        user_data['text'] = message.text
        user_data['link'] = ''
    else:
        user_data['link'] = message.text
        try:
            loader = NewsURLLoader(urls=[user_data['link']])
            article = loader.load()
            user_data['text'] = article[0].page_content

        except Exception as e:
            print(e)
            await bot.send_message(message.from_user.id, 'Помилка при завантаженні даних. Перевірте правильність посилання.')
            return
    output = generate_post_content(user_data['input_type'], user_data['link'], user_data['text'], user_data['event'], user_data['emojis'])
    data[message.from_user.id]['output'] = output
    if not user_data['emojis']:
        output = re.sub(emoji_pattern, '', output)

    await bot.send_message(message.from_user.id, 'Ось ваша публікація:')
    response = generate_with_gpt3(output) + f'\n\n▪️ [джерело]({user_data["link"]})'
    response = response.replace('**','*')
    await bot.send_message(message.from_user.id, response, parse_mode='Markdown')

# Run the bot
if __name__ == '__main__':
    executor.start_polling(dp)
