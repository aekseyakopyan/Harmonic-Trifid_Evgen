
import re
from typing import Dict, List, Optional, Any

class EntityExtractor:
    """
    Извлекает сущности из текста вакансии.
    """
    
    @staticmethod
    def extract_budget(text: str) -> Dict[str, Any]:
        """
        Извлекает информацию о бюджете.
        """
        # Паттерны для бюджета
        patterns = [
            r'бюджет[:\s]+(?:от\s+)?(\d+[\s,]*\d*)\s*(?:до\s+(\d+[\s,]*\d*))?\s*(₽|руб|рублей|тыс|тысяч|\$|долларов|usd)',
            r'(?:от|до)\s+(\d+[\s,]*\d*)\s*(₽|руб|рублей|тыс|тысяч|\$|долларов)',
            r'(\d+[\s,]*\d*)\s*[-–—]\s*(\d+[\s,]*\d*)\s*(₽|руб|рублей|\$)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                groups = match.groups()
                
                try:
                    min_val = int(re.sub(r'[\s,]', '', groups[0]))
                    max_val = int(re.sub(r'[\s,]', '', groups[1])) if len(groups) > 1 and groups[1] else min_val
                    currency = groups[-1] if len(groups) > 2 else '₽'
                    
                    # Нормализация (тыс → умножаем на 1000)
                    if 'тыс' in currency or 'тысяч' in currency:
                        min_val *= 1000
                        max_val *= 1000
                        currency = '₽'
                    
                    return {
                        "min": min_val,
                        "max": max_val,
                        "currency": currency,
                        "text": match.group(0)
                    }
                except (ValueError, IndexError):
                    continue
        
        return {"min": 0, "max": 0, "currency": None, "text": None}
    
    @staticmethod
    def extract_deadline(text: str) -> Dict[str, Any]:
        """
        Извлекает дедлайн.
        """
        urgency_patterns = [
            (r'\bсрочно\b', 'urgent'),
            (r'\bасап\b|asap', 'asap'),
            (r'\bсегодня\b', 'today'),
            (r'\bзавтра\b', 'tomorrow'),
            (r'\bна этой неделе\b', 'this_week'),
            (r'\bдо\s+(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)', 'specific_date'),
        ]
        
        for pattern, urgency_type in urgency_patterns:
            if re.search(pattern, text.lower()):
                return {"urgency": urgency_type, "has_deadline": True}
        
        return {"urgency": None, "has_deadline": False}
    
    @staticmethod
    def extract_contact_info(text: str) -> Dict[str, Any]:
        """
        Извлекает контактную информацию.
        """
        # Email
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        
        # Телефон
        phones = re.findall(r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text)
        
        # Telegram username
        tg_usernames = re.findall(r'@([a-zA-Z0-9_]{5,})', text)
        
        # URL
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        
        return {
            "emails": emails,
            "phones": phones,
            "telegram": tg_usernames,
            "urls": urls,
            "has_contact": len(emails) > 0 or len(phones) > 0 or len(tg_usernames) > 0
        }
    
    @staticmethod
    def extract_company_name(text: str) -> List[str]:
        """
        Извлекает упоминания компаний (простая эвристика).
        """
        # Паттерны для компаний
        patterns = [
            r'(?:компания|проект|бренд|магазин|школа)\s+[«"]([^»"]+)[»"]',
            r'(?:для|у нас в)\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)',
        ]
        
        companies = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            companies.extend(matches)
        
        return list(set(companies))
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        """
        Извлекает все сущности.
        """
        return {
            "budget": self.extract_budget(text),
            "deadline": self.extract_deadline(text),
            "contact": self.extract_contact_info(text),
            "companies": self.extract_company_name(text),
        }
