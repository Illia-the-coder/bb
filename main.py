import logging
import pandas as pd
from aiogram import Bot, Dispatcher, types

# Ensure you have openpyxl installed for Excel operations
# pip install openpyxl

logging.basicConfig(level=logging.INFO)

# Replace with your actual bot token
bot_token = "6849178402:AAHTbdlUObF1boJZrkmVryZjLtUYtvmogtA"
bot = Bot(token=bot_token)
dp = Dispatcher(bot)

promos = pd.read_csv('promos.csv')

# Create an empty DataFrame to store user data
columns = ['user_id', 'phone_number', 'full_name', 'address', 'promo_code', 'promo_code_used']
user_data_df = pd.DataFrame(columns=columns)

# Excel file to store user data
excel_file_path = 'user_data.xlsx'

# Function to save user data to Excel file
def save_to_excel():
    user_data_df.to_excel(excel_file_path, index=False)

# Load existing user data from Excel file if it exists
try:
    user_data_df = pd.read_excel(excel_file_path)
except (FileNotFoundError, pd.errors.EmptyDataError, ValueError):
    user_data_df = pd.DataFrame(columns=columns)
    save_to_excel()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="Поділитися телефоном", request_contact=True),
            ],
        ],
        resize_keyboard=True,
    )
    await message.reply("Вас вітає компанія Global Trade UA! 🌍🛍️\nДля отримання персонального промо-коду на знижку 50% в нашому інтернет-магазині вкажіть контактну інформацію. 📱⬇", reply_markup=markup)

@dp.message_handler(content_types=types.ContentTypes.CONTACT)
async def process_contact(message: types.Message):
    user_id = message.chat.id
    phone_number = message.contact.phone_number
    if phone_number not in user_data_df['phone_number'].values:
        user_data_df.loc[user_id, 'user_id'] = user_id
        user_data_df.loc[user_id, 'phone_number'] = phone_number
        save_to_excel()
        await message.reply("Дякуємо! Тепер вкажіть, будь ласка, ваше Прізвище Ім’я По-батькові. 📝⬇", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.reply("Ви вже зареєстровані", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def process_text(message: types.Message):
    user_id = message.chat.id

    # Check if the user has provided a full name
    if 'full_name' not in user_data_df.columns or pd.isna(user_data_df.loc[user_id, 'full_name']):
        name = message.text
        user_data_df.loc[user_id, 'full_name'] = name
        save_to_excel()
        await message.reply("Дякуємо! Тепер вкажіть адресу магазину у форматі вулиця, місто, область. 🏠⬇")
    else:
        # Check if the user has provided an address
        if 'address' not in user_data_df.columns or pd.isna(user_data_df.loc[user_id, 'address']):
            address = message.text
            user_data_df.loc[user_id, 'address'] = address

            # Generate and send promo code
            promo_code = promos[promos['Used'] != None].sample()['Promo'].values[0]
            promos.loc[promos['Promo'] == promo_code, 'Used'] = '+'
            promos.to_csv('promos.csv', index=False)
            user_data_df.loc[user_id, 'promo_code'] = promo_code
            save_to_excel()

            await message.reply(f"Ваш промо-код: {promo_code}")
        else:
            await message.reply("Ви вже вказали адресу. Чекаємо на ваше замовлення!")

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
