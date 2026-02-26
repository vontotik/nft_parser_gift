import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from logging_config import setup_logger
from urllib.parse import urljoin
import html
import random
import json
import time
import logging
from typing import Dict, List, Optional, Tuple

logger = setup_logger('parcer')
logger.setLevel(logging.WARNING)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

price_cache = {}
CACHE_DURATION = 300
last_nft_number_cache = {}

class PriceParser:
    def __init__(self):
        self.session = None
        self.base_url = "https://telegifter.ru/gifts/"
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
    
    def normalize_gift_name(self, gift_name):
        """Нормализует имя подарка для поиска на telegifter"""
        try:
            from nft_config import GIFT_NAME_MAPPING
            if gift_name in GIFT_NAME_MAPPING:
                return GIFT_NAME_MAPPING[gift_name]
            
            # Общая нормализация
            name_lower = gift_name.lower().replace(' ', '-')
            return name_lower
        except:
            return gift_name.lower().replace(' ', '-')
    
    async def get_gift_price_info(self, gift_name, characteristics=None):
        """Получает информацию о ценах подарка с telegifter"""
        cache_key = gift_name.lower()
        current_time = time.time()
        
        if cache_key in price_cache:
            cached_data, timestamp = price_cache[cache_key]
            if current_time - timestamp < CACHE_DURATION:
                return cached_data
        
        try:
            normalized_name = self.normalize_gift_name(gift_name)
            url = f"{self.base_url}{normalized_name}/"
            
            logger.debug(f"Запрос цены для {gift_name}: {url}")
            
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    logger.debug(f"Страница не найдена: {response.status}")
                    return None
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Ищем цены на странице
                price_data = {'ton': None, 'usdt': None, 'rub': None}
                
                # Ищем все div с ценами
                price_divs = soup.find_all('div', class_=re.compile(r'price', re.I))
                
                for div in price_divs:
                    text = div.get_text(strip=True)
                    
                    # Ищем TON
                    ton_match = re.search(r'([\d\.,]+)\s*TON', text, re.I)
                    if ton_match:
                        try:
                            ton_price = ton_match.group(1).replace(',', '')
                            price_data['ton'] = float(ton_price)
                        except:
                            pass
                    
                    # Ищем USDT
                    usdt_match = re.search(r'([\d\.,]+)\s*USDT', text, re.I)
                    if usdt_match:
                        try:
                            usdt_price = usdt_match.group(1).replace(',', '')
                            price_data['usdt'] = float(usdt_price)
                        except:
                            pass
                    
                    # Ищем RUB
                    rub_match = re.search(r'([\d\.,]+)\s*RUB', text, re.I)
                    if rub_match:
                        try:
                            rub_price = rub_match.group(1).replace(',', '')
                            price_data['rub'] = float(rub_price)
                        except:
                            pass
                
                # Если не нашли в div, ищем во всем тексте
                if not any(price_data.values()):
                    all_text = soup.get_text()
                    
                    ton_matches = re.findall(r'([\d\.,]+)\s*TON', all_text, re.I)
                    if ton_matches:
                        try:
                            price_data['ton'] = float(ton_matches[-1].replace(',', ''))
                        except:
                            pass
                    
                    usdt_matches = re.findall(r'([\d\.,]+)\s*USDT', all_text, re.I)
                    if usdt_matches:
                        try:
                            price_data['usdt'] = float(usdt_matches[-1].replace(',', ''))
                        except:
                            pass
                    
                    rub_matches = re.findall(r'([\d\.,]+)\s*RUB', all_text, re.I)
                    if rub_matches:
                        try:
                            price_data['rub'] = float(rub_matches[-1].replace(',', ''))
                        except:
                            pass
                
                if any(price_data.values()):
                    price_cache[cache_key] = (price_data, current_time)
                    return price_data
                
                return None
                
        except Exception as e:
            logger.debug(f"Ошибка получения цены для {gift_name}: {e}")
            return None

class Parcer:
    def __init__(self):
        self.session = None
        self.price_parser = None
        self.current_user_agent = random.choice(USER_AGENTS)
    
    def extract_gift_name(self, url: str) -> str:
        """Извлекает название подарка из URL"""
        try:
            parts = url.rstrip('-').split('/')
            gift_part = parts[-1] if parts else ""
            
            # Преобразуем kebab-case в читаемое имя
            name_parts = gift_part.split('-')
            name = ' '.join(part.capitalize() for part in name_parts if part)
            
            # Специальные случаи
            special_cases = {
                'Bdaycandle': 'B-day Candle',
                'Durovscap': "Durov's Cap",
                'Nekobucket': 'Neko Bucket',
                'Blingbinky': 'Bling Binky',
                'Springbasket': 'Spring Basket',
                'Victorymedal': 'Victory Medal',
                'Spicedwine': 'Spiced Wine',
                'Snowmittens': 'Snow Mittens',
                'Lushbouquet': 'Lush Bouquet',
                'Whipcupcake': 'Whip Cupcake',
                'Winterwreath': 'Winter Wreath',
                'Snowglobe': 'Snow Globe',
                'Santahat': 'Santa Hat',
                'Bunnymuffin': 'Bunny Muffin',
                'Candycane': 'Candy Cane',
                'Eternalrose': 'Eternal Rose',
                'Astralshard': 'Astral Shard',
                'Cookieheart': 'Cookie Heart',
                'Crystalball': 'Crystal Ball',
                'Deskcalendar': 'Desk Calendar',
                'Diamondring': 'Diamond Ring',
                'Electricskull': 'Electric Skull',
                'Eternalcandle': 'Eternal Candle',
                'Evileye': 'Evil Eye',
                'Flyingbroom': 'Flying Broom',
                'Genielamp': 'Genie Lamp',
                'Gingercookie': 'Ginger Cookie',
                'Hangingstar': 'Hanging Star',
                'Hexpot': 'Hex Pot',
                'Homemadecake': 'Homemade Cake',
                'Hypnolollipop': 'Hypno Lollipop',
                'Iongem': 'Ion Gem',
                'Jackinthebox': 'Jack in the Box',
                'Jellybunny': 'Jelly Bunny',
                'Jesterhat': 'Jester Hat',
                'Jinglebells': 'Jingle Bells',
                'Kissedfrog': 'Kissed Frog',
                'Lolpop': 'Lol Pop',
                'Lootbag': 'Loot Bag',
                'Lovecandle': 'Love Candle',
                'Lovepotion': 'Love Potion',
                'Lunarsnake': 'Lunar Snake',
                'Madpumpkin': 'Mad Pumpkin',
                'Magicpotion': 'Magic Potion',
                'Minioscar': 'Mini Oscar',
                'Nekohelmet': 'Neko Helmet',
                'Partysparkler': 'Party Sparkler',
                'Perfumebottle': 'Perfume Bottle',
                'Plushpepe': 'Plush Pepe',
                'Preciouspeach': 'Precious Peach',
                'Recordplayer': 'Record Player',
                'Sakuraflower': 'Sakura Flower',
                'Scaredcat': 'Scared Cat',
                'Sharptongue': 'Sharp Tongue',
                'Signetring': 'Signet Ring',
                'Skullflower': 'Skull Flower',
                'Sleighbell': 'Sleigh Bell',
                'Snakebox': 'Snake Box',
                'Snoopcigar': 'Snoop Cigar',
                'Snoopdogg': 'Snoop Dogg',
                'Spyagaric': 'Spy Agaric',
                'Starnotepad': 'Star Notepad',
                'Swisswatch': 'Swiss Watch',
                'Tamagadget': 'Tama Gadget',
                'Tophat': 'Top Hat',
                'Toybear': 'Toy Bear',
                'Trappedheart': 'Trapped Heart',
                'Valentinebox': 'Valentine Box',
                'Vintagecigar': 'Vintage Cigar',
                'Voodoodoll': 'Voodoo Doll',
                'Winterwreath': 'Winter Wreath',
                'Witchhat': 'Witch Hat',
                'Xmasstocking': 'Xmas Stocking',
                'Westside': 'Westside Sign',
                'Skystilettos': 'Sky Stilettos',
                'Artisanbrick': 'Artisan Brick',
                'Instantramen': 'Instant Ramen',
                'Jollychimp': 'Jolly Chimp',
                'Icecream': 'Ice Cream',
                'Freshsocks': 'Fresh Socks',
                'Gemsignet': 'Gem Signet',
                'Heroichelmet': 'Heroic Helmet',
                'Happybrownie': 'Happy Brownie',
                'Heartlocket': 'Heart Locket',
                'Holidaydrink': 'Holiday Drink',
                'Inputkey': 'Input Key',
                'Ionicdryer': 'Ionic Dryer',
                'Joyfulbundle': 'Joyful Bundle',
                'Lightsword': 'Light Sword',
                'Lowrider': 'Low Rider',
                'Moonpendant': 'Moon Pendant',
                'Nailbracelet': 'Nail Bracelet',
                'Petsnake': 'Pet Snake',
                'Restlessbar': 'Restless Bar',
                'Swagbag': 'Swag Bag',
                'MoneyPot': 'Money Pot',
                'Prettyposy': 'Pretty Posy',
                'Bondedring': 'Bonded Ring',
                'Cloverpin': 'Clover Pin',
                'Cupidcharm': 'Cupid Charm',
                'Faithamulet': 'Faith Amulet',
                'MousseCake': 'Mousse Cake',
                'Mightyarm': 'Mighty Arm',
            }
            
            simple_name = ''.join(part.capitalize() for part in name_parts)
            if simple_name in special_cases:
                return special_cases[simple_name]
            
            return name if name else "Unknown"
        except Exception:
            return "Unknown"
    
    async def __aenter__(self):
        self.current_user_agent = random.choice(USER_AGENTS)
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                'User-Agent': self.current_user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        self.price_parser = PriceParser()
        await self.price_parser.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
        if self.price_parser:
            await self.price_parser.__aexit__(exc_type, exc, tb)
    
    def rotate_user_agent(self):
        self.current_user_agent = random.choice(USER_AGENTS)
        if self.session:
            self.session.headers.update({'User-Agent': self.current_user_agent})

    async def fetch(self, num: str, url: str) -> Optional[Dict]:
        """Получает информацию о подарке"""
        try:
            full_url = url + num
            
            async with self.session.get(full_url, timeout=5) as response:
                if response.status != 200:
                    return None
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                title = soup.title.string if soup.title else ''
                
                if not title or "gift" not in title.lower():
                    return None
                
                # Парсим информацию о владельце
                owner_info = self.parse_owner_info(soup)
                gift_link = full_url
                gift_name = self.extract_gift_name(url)
                
                characteristics = self.parse_characteristics_from_table(soup)
                issued_info = self.parse_issued_info(soup)
                
                # Получаем информацию о ценах
                price_info = await self.get_price_info(gift_name, characteristics)
                
                message = self.format_message(
                    gift_name, num, characteristics, price_info, 
                    issued_info, owner_info, gift_link
                )
                
                keyboard = self.create_keyboard_with_show_gift(gift_link, owner_info, price_info)
                
                return {
                    'message': message,
                    'num': num,
                    'link': gift_link,
                    'keyboard': keyboard,
                    'owner_info': owner_info,
                    'issued_info': issued_info,
                    'characteristics': characteristics,
                    'price_info': price_info
                }
                
        except Exception as e:
            logger.debug(f"Ошибка fetch для {url}{num}: {e}")
            return None

    def parse_owner_info(self, soup):
        """Парсит информацию о владельце"""
        try:
            # Ищем все ссылки с t.me
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href', '')
                
                if 't.me/' in href or 'tg://' in href:
                    name = a_tag.get_text(strip=True)
                    
                    if not name or name in ['Telegram', 'Share', 'Open', 'Forward', 'Preview', 'View in Telegram']:
                        continue
                    
                    username = None
                    user_id = None
                    
                    # Извлекаем user_id или username
                    if 't.me/' in href:
                        match = re.search(r't\.me/([a-zA-Z0-9_]+)', href)
                        if match:
                            extracted = match.group(1)
                            if extracted.startswith('id') and extracted[2:].isdigit():
                                user_id = extracted[2:]
                            else:
                                username = extracted
                    
                    elif 'tg://' in href:
                        match = re.search(r'tg://(?:user|openmessage)\?id=(\d+)', href)
                        if match:
                            user_id = match.group(1)
                    
                    name = re.sub(r'[^\w\s@\-\.]', '', name).strip()
                    
                    if not name:
                        continue
                    
                    return {
                        'name': html.escape(name),
                        'username': username,
                        'user_id': user_id,
                        'href': href
                    }
            
            return None
        except Exception:
            return None

    def format_message(self, gift_name, num, characteristics, price_info, issued_info, owner_info, gift_link):
        """Форматирует сообщение ТОЧНО как в примере"""
        message_lines = []
        
        # Заголовок с ссылкой на подарок в скобках
        message_lines.append(f"🎁 {gift_name} ({gift_link}) - #{num}")
        message_lines.append("")
        
        # Характеристики
        if characteristics:
            message_lines.append("<b>ХАРАКТЕРИСТИКИ:</b>")
            for char_type, char_text, percent in characteristics:
                if percent is not None:
                    # Форматируем проценты курсивом
                    char_display = f"{char_text} <i>{percent}%</i>"
                    
                    # Добавляем эмодзи в зависимости от процента
                    if percent < 0.5:
                        char_display += " 🔥🔥🔥"
                    elif percent < 1:
                        char_display += " 💍"
                    
                    # Специальные случаи для фона
                    if char_type.lower() == 'фон' and char_text.lower() in ['onyx black', 'black']:
                        char_display += " 🔥"
                else:
                    char_display = char_text
                
                message_lines.append(f"- <b>{char_type}:</b> {char_display}")
        
        # Issued информация
        if issued_info:
            issued, total = issued_info
            issued_formatted = f"{issued:,}".replace(',', ' ')
            total_formatted = f"{total:,}".replace(',', ' ')
            message_lines.append(f"\n<b>Выпущено:</b> {issued_formatted}/{total_formatted} issued")
        
        # Цены
        if price_info and price_info.get('average_price'):
            price = price_info['average_price']
            
            if price.get('ton'):
                message_lines.append(f"<b>Цена:</b> {price['ton']} TON")
            
            if price.get('usdt'):
                message_lines.append(f"<b>Цена:</b> {price['usdt']} USDT")
            
            if price.get('rub'):
                message_lines.append(f"<b>Цена:</b> {price['rub']} RUB")
        else:
            message_lines.append("<b>Цена:</b> Не найдена")
        
        # Владелец с ссылкой
        if owner_info and owner_info.get('name'):
            owner_display = self.format_owner_display(owner_info)
            message_lines.append(f"\n<b>Владелец:</b> {owner_display}")
        else:
            message_lines.append(f"\n<b>Владелец:</b> Не указан")
        
        # Ссылка на подарок
        message_lines.append(f"<b>Ссылка:</b> {gift_link}")
        
        # Вечные ссылки
        if owner_info:
            eternal_links = self.format_eternal_links(owner_info)
            if eternal_links:
                message_lines.append("\n<b>Вечные ссылки:</b>")
                for link in eternal_links:
                    message_lines.append(link)
        
        return "\n".join(message_lines)

    def format_owner_display(self, owner_info):
        """Форматирует отображение владельца"""
        name = owner_info.get('name', 'Unknown')
        user_id = owner_info.get('user_id')
        username = owner_info.get('username')
        
        name = re.sub(r'[^\w\s@\-\.]', '', name).strip()
        
        if user_id:
            return f'{name} (<a href="https://t.me/id{user_id}">https://t.me/id{user_id}</a>)'
        elif username:
            return f'{name} (<a href="https://t.me/{username}">https://t.me/{username}</a>)'
        else:
            return name

    def format_eternal_links(self, owner_info):
        """Форматирует вечные ссылки ТОЧНО как в примере"""
        user_id = owner_info.get('user_id')
        username = owner_info.get('username')
        
        links = []
        
        if user_id:
            # Android: ссылка, затем эмодзи и текст с tg-ссылкой
            links.append(f'(<a href="https://t.me/id{user_id}">https://t.me/id{user_id}</a>)')
            links.append(f'🤖 Android (tg://resolve?domain={user_id})')
            # Apple: эмодзи, текст и ссылка
            links.append(f'🍎 Apple (<a href="https://t.me/id{user_id}">https://t.me/id{user_id}</a>)')
        elif username:
            links.append(f'(<a href="https://t.me/{username}">https://t.me/{username}</a>)')
            links.append(f'🤖 Android (tg://resolve?domain={username})')
            links.append(f'🍎 Apple (<a href="https://t.me/{username}">https://t.me/{username}</a>)')
        
        return links

    def create_keyboard_with_show_gift(self, gift_link, owner_info, price_info):
        """Создает inline клавиатуру с цветными кнопками (новое API)"""
        inline_keyboard = []
        
        # Кнопка показать подарок – синяя (primary)
        inline_keyboard.append([InlineKeyboardButton(
            text="🎁 ПОКАЗАТЬ ПОДАРОК", 
            url=gift_link,
            style='primary'          # синий цвет
        )])
        
        # Кнопка профиля владельца – зелёная (positive)
        if owner_info:
            if owner_info.get('user_id'):
                profile_url = f"https://t.me/id{owner_info['user_id']}"
            elif owner_info.get('username'):
                profile_url = f"https://t.me/{owner_info['username']}"
            else:
                profile_url = None
            
            if profile_url:
                inline_keyboard.append([InlineKeyboardButton(
                    text="👤 Профиль владельца", 
                    url=profile_url,
                    style='positive'    # зелёный цвет
                )])
        
        # Кнопка для просмотра цен – серая (secondary)
        if price_info and price_info.get('price_url'):
            inline_keyboard.append([InlineKeyboardButton(
                text="💰 Цены на Telegifter", 
                url=price_info['price_url'],
                style='secondary'       # серый / нейтральный
            )])
        
        return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    async def get_price_info(self, gift_name, characteristics):
        """Получает информацию о ценах для подарка"""
        try:
            price_data = await self.price_parser.get_gift_price_info(gift_name)
            if not price_data:
                return None
            
            return {
                'average_price': price_data,
                'price_url': self.price_parser.base_url + self.price_parser.normalize_gift_name(gift_name) + "/"
            }
            
        except Exception as e:
            logger.debug(f"Ошибка получения цены: {e}")
            return None

    def parse_characteristics_from_table(self, soup):
        """Парсит характеристики из таблицы"""
        try:
            characteristics = []
            table = soup.find('table', class_='tgme_gift_table')
            if not table:
                return []
            
            for row in table.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    char_type = th.text.strip().lower()
                    if char_type in ['owner', 'quantity']:
                        continue
                    
                    char_text = td.get_text(strip=True)
                    
                    # Ищем процент в скобках
                    percent = None
                    percent_match = re.search(r'([\d\.]+)%', char_text)
                    if percent_match:
                        try:
                            percent = float(percent_match.group(1))
                            # Убираем процент из текста
                            char_text = re.sub(r'\s*[\d\.]+%', '', char_text).strip()
                        except:
                            pass
                    
                    # Переводим на русский
                    char_translation = {
                        'model': 'Модель',
                        'backdrop': 'Фон',
                        'symbol': 'Символ',
                        'модель': 'Модель',
                        'фон': 'Фон',
                        'символ': 'Символ'
                    }
                    
                    char_type_ru = char_translation.get(char_type, char_type.capitalize())
                    
                    if char_text:
                        characteristics.append((char_type_ru, char_text, percent))
            
            return characteristics
            
        except Exception:
            return []

    def parse_issued_info(self, soup):
        """Парсит информацию о выпущенных подарках"""
        try:
            table = soup.find('table', class_='tgme_gift_table')
            if table:
                for row in table.find_all('tr'):
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        th_text = th.text.strip().lower()
                        td_text = td.text.strip()
                        
                        if any(keyword in th_text for keyword in ['quantity', 'выпущено', 'issued']):
                            td_text = td_text.replace(' issued', '').replace(' issued', '')
                            
                            match = re.search(r'([\d\s,]+)\s*[/из]?\s*([\d\s,]+)', td_text)
                            if match:
                                issued_str = match.group(1).replace(' ', '').replace(',', '').replace('\xa0', '')
                                total_str = match.group(2).replace(' ', '').replace(',', '').replace('\xa0', '')
                                
                                try:
                                    issued = int(issued_str)
                                    total = int(total_str)
                                    return (issued, total)
                                except:
                                    pass
            
            all_text = soup.get_text()
            
            patterns = [
                r'(\d[\d\s,]*)\s*/\s*(\d[\d\s,]*)\s*issued',
                r'issued\s*(\d[\d\s,]*)\s*of\s*(\d[\d\s,]*)',
                r'(\d[\d\s,]*)\s*из\s*(\d[\d\s,]*)\s*issued',
                r'(\d[\d\s,]*)\s*из\s*(\d[\d\s,]*)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    try:
                        issued_str = match.group(1).replace(' ', '').replace(',', '').replace('\xa0', '')
                        total_str = match.group(2).replace(' ', '').replace(',', '').replace('\xa0', '')
                        
                        issued = int(issued_str)
                        total = int(total_str)
                        return (issued, total)
                    except:
                        continue
            
            return None
        except Exception:
            return None

    async def get_current_issued_count(self, url: str) -> int:
        """Получает текущее количество выпущенных подарков"""
        try:
            test_url = url + "1"
            async with self.session.get(test_url, timeout=5) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    issued_info = self.parse_issued_info(soup)
                    if issued_info:
                        return issued_info[0]
                
                return 0
        except Exception:
            return 0

    async def get_last_nft_number(self, url: str, gift_name: str) -> Optional[int]:
        """Получает номер последнего NFT для подарка"""
        cache_key = gift_name.lower()
        current_time = time.time()
        
        if cache_key in last_nft_number_cache:
            cached_data, timestamp = last_nft_number_cache[cache_key]
            if current_time - timestamp < 300:
                return cached_data
        
        try:
            # Пробуем получить issued count
            issued_count = await self.get_current_issued_count(url)
            if issued_count and issued_count > 0:
                last_nft_number_cache[cache_key] = (issued_count, current_time)
                return issued_count
            
            # Если не получили, ищем бинарным поиском
            low = 1
            high = 1000000
            last_found = 0
            
            while low <= high and (high - low) > 100:
                mid = (low + high) // 2
                
                try:
                    test_url = url + str(mid)
                    async with self.session.get(test_url, timeout=3) as response:
                        if response.status == 200:
                            content = await response.text()
                            soup = BeautifulSoup(content, 'html.parser')
                            title = soup.title.string if soup.title else ''
                            
                            if "gift" in title.lower():
                                last_found = mid
                                low = mid + 1
                            else:
                                high = mid - 1
                        else:
                            high = mid - 1
                except Exception:
                    high = mid - 1
                
                await asyncio.sleep(0.01)
            
            if last_found > 0:
                last_nft_number_cache[cache_key] = (last_found, current_time)
                return last_found
            
            return None
            
        except Exception:
            return None

    async def check_promarket_gift(self, gift_name: str) -> bool:
        """Проверяет, есть ли подарок в премаркете"""
        try:
            normalized_name = gift_name.lower().replace(' ', '-')
            test_url = f"https://t.me/nft/{normalized_name}-1"
            
            async with self.session.get(test_url, timeout=5) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    title = soup.title.string if soup.title else ''
                    
                    if title and "gift" in title.lower():
                        issued_info = self.parse_issued_info(soup)
                        if issued_info and issued_info[0] == 0:
                            return False
                        return True
                
                return False
                
        except Exception:
            return False