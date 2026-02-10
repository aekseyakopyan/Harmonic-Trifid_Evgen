"""
Contact Extractor - извлекает контактную информацию из сообщений с приоритизацией.
"""

import re
from typing import Dict, List, Optional


class ContactExtractor:
    """Извлечение контактов из вакансий с приоритизацией источников"""
    
    # Паттерны для извлечения username из текста (Приоритет 1B)
    TEXT_PATTERNS = [
        (r"(?:откликаться|отклик|писать|пишите)\s+(?:сюда|в\s+личку|лс)?[:\s👉→]*(@\w+)", 1),
        (r"(?:контакт|тг|связь|tg|связаться)[:\s👉→]*(@\w+)", 2),
        (r"админ(?:у|а)?[:\s👉→]*(@\w+)", 3),
        (r"личка[:\s👉→]*(@\w+)", 4),
        (r"автор(?:у|а)?[:\s👉→]*(@\w+)", 5),
        (r"откликнуться\s+[👉→]\s*(@\w+)", 6),
        (r"(@\w+)\s+с пометкой\s+#\w+", 7),
        (r"написать\s+(@\w+)", 8),
        (r"менеджер(?:у)?[:\s👉→]*(@\w+)", 9),
    ]
    
    # Ключевые слова в тексте кнопок
    BUTTON_KEYWORDS = [
        "связаться",
        "откликнуться",
        "контакт",
        "написать",
        "отклик",
        "автор",
        "узнать подробнее",
        "заполнить",
        "админ",
        "анкета"
    ]
    
    def extract_contact(self, message_data: Dict) -> Dict:
        """
        Извлекает контакт с приоритизацией.
        
        Args:
            message_data: {
                'text': str,
                'buttons': str (секция 🔘 КНОПКИ),
                'sender_id': int
            }
        
        Returns:
            {
                'priority_level': str (1A, 1B, 2, 3),
                'contact_type': str (button_username, text_username, forwarded_from, sender_username, sender_id, form),
                'contact_value': str,
                'contact_link': str (t.me/username),
                'additional_instructions': str,
                'subject_line': str,
                'extraction_source': str,
                'extraction_confidence': str (high, medium, low),
                'backup_contacts': list
            }
        """
        results = []
        
        # ПРИОРИТЕТ 0: Forwarded From (если сообщение переслано от пользователя)
        fwd_contact = self._extract_from_forwarded(message_data.get('fwd_from'))
        if fwd_contact:
            return fwd_contact
        
        # ПРИОРИТЕТ 1A: Кнопки
        button_contact = self._extract_from_buttons(message_data.get('buttons', ''))
        if button_contact:
            return button_contact
        
        # ПРИОРИТЕТ 1B: Прямое указание в тексте
        text_contact = self._extract_from_text_patterns(message_data.get('text', ''))
        if text_contact:
            return text_contact
        
        # ПРИОРИТЕТ 1C: Упоминание админа/личка без @
        admin_contact = self._extract_admin_mentions(message_data.get('text', ''))
        if admin_contact:
            return admin_contact
        
        # ПРИОРИТЕТ 2: Username отправителя
        sender_username_contact = self._extract_sender_username(message_data.get('sender_username'))
        if sender_username_contact:
            return sender_username_contact
            
        # ПРИОРИТЕТ 3: Резервный поиск (любые @username или ссылки) - ВАЖНО: Это теперь ПЕРЕД ID
        fallback_contact = self._extract_fallback(message_data.get('text', ''))
        if fallback_contact:
            return fallback_contact
        
        # ПРИОРИТЕТ 4: ID отправителя (ТОЛЬКО ЕСЛИ НИЧЕГО БОЛЬШЕ НЕТ)
        sender_contact = self._extract_sender_id(message_data.get('sender_id'))
        if sender_contact:
            return sender_contact
        
        # Контакт не найден
        return {
            'priority_level': 'none',
            'contact_type': 'not_found',
            'contact_value': None,
            'contact_link': None,
            'additional_instructions': None,
            'subject_line': None,
            'extraction_source': 'не найдено',
            'extraction_confidence': 'none',
            'backup_contacts': []
        }
    
    def _extract_from_buttons(self, buttons_text: str) -> Optional[Dict]:
        """Извлечение контакта из кнопок (Приоритет 1A)"""
        if not buttons_text or '🔘 КНОПКИ:' not in buttons_text:
            return None
        
        # Парсим кнопки
        button_lines = buttons_text.split('\n')
        priority_buttons = []
        all_buttons = []
        
        for line in button_lines:
            if '→' in line:
                # Формат: "• Текст кнопки → URL"
                parts = line.split('→')
                if len(parts) == 2:
                    button_text = parts[0].strip(' •')
                    url = parts[1].strip()
                    
                    # Приоритизируем по ключевым словам
                    priority = 999
                    for i, keyword in enumerate(self.BUTTON_KEYWORDS):
                        if keyword in button_text.lower():
                            priority = i
                            break
                    
                    all_buttons.append({
                        'text': button_text,
                        'url': url,
                        'priority': priority
                    })
        
        if not all_buttons:
            return None
        
        # Сортируем по приоритету
        all_buttons.sort(key=lambda x: x['priority'])
        best_button = all_buttons[0]
        
        # Извлекаем username из URL
        username = self._extract_username_from_url(best_button['url'])
        
        if username:
            contact_link = f"https://t.me/{username.lstrip('@')}"
            return {
                'priority_level': '1A',
                'contact_type': 'button_username',
                'contact_value': username,
                'contact_link': contact_link,
                'additional_instructions': None,
                'subject_line': None,
                'extraction_source': f"кнопка '{best_button['text']}'",
                'extraction_confidence': 'high',
                'backup_contacts': [b['url'] for b in all_buttons[1:]]
            }
        
        return None
    
    def _extract_from_text_patterns(self, text: str) -> Optional[Dict]:
        """Извлечение контакта из текста по паттернам (Приоритет 1B)"""
        if not text:
            return None
        
        # Сортируем паттерны по приоритету
        sorted_patterns = sorted(self.TEXT_PATTERNS, key=lambda x: x[1])
        
        for pattern, priority in sorted_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                username = match.group(1)
                
                # Проверяем дополнительные инструкции
                additional_instructions = None
                subject_line = None
                
                # "с пометкой #тег"
                tag_match = re.search(rf"{re.escape(username)}\s+с пометкой\s+(#\w+)", text, re.IGNORECASE)
                if tag_match:
                    additional_instructions = f"с пометкой {tag_match.group(1)}"
                
                # "с темой 'X'"
                subject_match = re.search(rf"{re.escape(username)}\s+с темой\s+['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
                if subject_match:
                    subject_line = subject_match.group(1)
                
                contact_link = f"https://t.me/{username.lstrip('@')}"
                return {
                    'priority_level': '1B',
                    'contact_type': 'text_username',
                    'contact_value': username,
                    'contact_link': contact_link,
                    'additional_instructions': additional_instructions,
                    'subject_line': subject_line,
                    'extraction_source': f"текст (паттерн '{pattern}')",
                    'extraction_confidence': 'high',
                    'backup_contacts': []
                }
        
        return None
    
    def _extract_from_forwarded(self, fwd_from: Optional[Dict]) -> Optional[Dict]:
        """Извлечение контакта из пересланного сообщения (Приоритет 0)"""
        if not fwd_from:
            return None
        
        # Если переслано от пользователя (не канала)
        if fwd_from.get('from_id') and not fwd_from.get('channel_id'):
            user_id = fwd_from.get('from_id')
            username = fwd_from.get('from_username')
            
            if username:
                contact_link = f"https://t.me/{username.lstrip('@')}"
                return {
                    'priority_level': '0',
                    'contact_type': 'forwarded_from',
                    'contact_value': f"@{username}",
                    'contact_link': contact_link,
                    'additional_instructions': 'Переслано от пользователя',
                    'subject_line': None,
                    'extraction_source': 'пересланное сообщение',
                    'extraction_confidence': 'high',
                    'backup_contacts': []
                }
            elif user_id:
                return {
                    'priority_level': '0',
                    'contact_type': 'forwarded_from',
                    'contact_value': str(user_id),
                    'contact_link': f"tg://user?id={user_id}",
                    'additional_instructions': 'Переслано от пользователя (без username)',
                    'subject_line': None,
                    'extraction_source': 'пересланное сообщение (ID)',
                    'extraction_confidence': 'medium',
                    'backup_contacts': []
                }
        
        return None

    def _extract_admin_mentions(self, text: str) -> Optional[Dict]:
        """Поиск упоминаний админа/модератора без @ (крайний случай)"""
        if not text:
            return None
        
        # Различные формы "пишите в личку"
        pm_keywords = [
            r"личные\s+сообщения", r"личку", r"лс", r"в\s+личном", 
            r"личка\s+админа", r"лички\s+админа", r"писати\s+админу", 
            r"headmod", r"head[- ]mod", r"связаться\s+со\s+мной"
        ]
        
        for pattern in pm_keywords:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    'priority_level': '1C',
                    'contact_type': 'admin_mention',
                    'contact_value': 'написать автору/админу',
                    'contact_link': None,
                    'additional_instructions': 'В тексте указано писать в личные сообщения',
                    'subject_line': None,
                    'extraction_source': 'упоминание лички в тексте',
                    'extraction_confidence': 'medium',
                    'backup_contacts': []
                }
        
        # Поиск номера телефона
        phone_match = re.search(r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", text)
        if phone_match:
            phone = phone_match.group(0)
            # Попробуем найти имя рядом
            name_match = re.search(rf"{re.escape(phone)}\s*([А-Я][а-я]+)", text)
            contact_val = phone
            if name_match:
                contact_val = f"{phone} ({name_match.group(1)})"
            
            return {
                'priority_level': '1D',
                'contact_type': 'phone',
                'contact_value': contact_val,
                'contact_link': f"tel:{phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}",
                'additional_instructions': 'Указан номер телефона',
                'subject_line': None,
                'extraction_source': 'номер телефона в тексте',
                'extraction_confidence': 'high',
                'backup_contacts': []
            }

        return None

    def _extract_sender_username(self, sender_username: Optional[str]) -> Optional[Dict]:
        """Извлечение username отправителя (Приоритет 2)"""
        if not sender_username:
            return None
        
        username = sender_username if sender_username.startswith('@') else f"@{sender_username}"
        contact_link = f"https://t.me/{username.lstrip('@')}"
        
        return {
            'priority_level': '2',
            'contact_type': 'sender_username',
            'contact_value': username,
            'contact_link': contact_link,
            'additional_instructions': None,
            'subject_line': None,
            'extraction_source': 'username отправителя',
            'extraction_confidence': 'medium',
            'backup_contacts': []
        }
    
    def _extract_sender_id(self, sender_id: Optional[int]) -> Optional[Dict]:
        """Извлечение ID отправителя (Приоритет 3)"""
        if not sender_id:
            return None
        
        return {
            'priority_level': '3',
            'contact_type': 'sender_id',
            'contact_value': str(sender_id),
            'contact_link': f"tg://user?id={sender_id}",
            'additional_instructions': None,
            'subject_line': None,
            'extraction_source': 'ID отправителя',
            'extraction_confidence': 'medium',
            'backup_contacts': []
        }
    
    def _extract_fallback(self, text: str) -> Optional[Dict]:
        """Резервное извлечение (Приоритет 4)"""
        if not text:
            return None
        
        # Поиск любых @username
        username_pattern = r"@(\w+)"
        matches = re.findall(username_pattern, text)
        
        if matches:
            # Берем первый по порядку
            username = f"@{matches[0]}"
            contact_link = f"https://t.me/{username.lstrip('@')}"
            
            return {
                'priority_level': '4',
                'contact_type': 'text_username',
                'contact_value': username,
                'contact_link': contact_link,
                'additional_instructions': None,
                'subject_line': None,
                'extraction_source': 'резервный поиск в тексте',
                'extraction_confidence': 'low',
                'backup_contacts': [f"@{m}" for m in matches[1:]]
            }
        
        # Поиск форм
        form_pattern = r"https?://(?:forms\.gle|typeform\.com|docs\.google\.com)/\S+"
        form_match = re.search(form_pattern, text, re.IGNORECASE)
        
        if form_match:
            return {
                'priority_level': '4',
                'contact_type': 'form',
                'contact_value': form_match.group(0),
                'contact_link': form_match.group(0),
                'additional_instructions': 'Требуется заполнение формы',
                'subject_line': None,
                'extraction_source': 'ссылка на форму',
                'extraction_confidence': 'low',
                'backup_contacts': []
            }
        
        return None
    
    def _extract_username_from_url(self, url: str) -> Optional[str]:
        """Извлекает username из Telegram URL"""
        # Паттерны для t.me ссылок
        patterns = [
            r"t\.me/(\w+)",
            r"https?://t\.me/(\w+)",
            r"telegram\.me/(\w+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return f"@{match.group(1)}"
        
        # Если это уже @username
        if url.startswith('@'):
            return url
        
        return None
