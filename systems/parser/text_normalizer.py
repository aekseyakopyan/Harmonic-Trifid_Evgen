"""
Text normalization utilities для извлечения числительных и дат.
Преобразует текстовые числа в numeric values.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict
from core.utils.structured_logger import get_logger

logger = get_logger(__name__)


class TextNormalizer:
    """
    Нормализация текстовых числительных и временных выражений.
    """
    
    def __init__(self):
        # Словарь для русских числительных
        self.number_words = {
            # Единицы
            "один": 1, "одна": 1, "одно": 1,
            "два": 2, "две": 2,
            "три": 3, "четыре": 4, "пять": 5,
            "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
            
            # Десятки
            "десять": 10, "одиннадцать": 11, "двенадцать": 12,
            "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15,
            "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18,
            "девятнадцать": 19, "двадцать": 20, "тридцать": 30,
            "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
            "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
            
            # Сотни
            "сто": 100, "двести": 200, "триста": 300,
            "четыреста": 400, "пятьсот": 500, "шестьсот": 600,
            "семьсот": 700, "восемьсот": 800, "девятьсот": 900,
            
            # Множители
            "тысяч": 1000, "тысяча": 1000, "тысячи": 1000,
            "миллион": 1000000, "миллиона": 1000000, "миллионов": 1000000,
            
            # Сокращения
            "тыс": 1000, "тыщ": 1000, "к": 1000,
            "млн": 1000000, "мил": 1000000,
        }
        
        # Словарь для временных периодов
        self.time_periods = {
            "сегодня": 0,
            "завтра": 1,
            "послезавтра": 2,
            "через день": 2,
            "через неделю": 7,
            "через две недели": 14,
            "через месяц": 30,
        }
        
        logger.info("text_normalizer_initialized")
    
    def text_to_number(self, text: str) -> Optional[int]:
        """
        Преобразование текстовых числительных в числа.
        
        Examples:
            "пятьдесят тысяч" → 50000
            "сто двадцать пять" → 125
            "три с половиной тысячи" → 3500
            "50к" → 50000
            "2.5 млн" → 2500000
        
        Args:
            text: текст с числительным
            
        Returns:
            Число или None если не удалось распознать
        """
        text = text.lower().strip()
        
        # Попытка 1: Распознать цифровые форматы
        # "50к", "2.5млн", "100 тыс"
        numeric_match = re.search(r'(\d+(?:[.,]\d+)?)\s*([кмтмил]+)', text)
        if numeric_match:
            number = float(numeric_match.group(1).replace(',', '.'))
            multiplier_text = numeric_match.group(2)
            
            if multiplier_text in ['к', 'тыс', 'тысяч']:
                return int(number * 1000)
            elif multiplier_text in ['м', 'млн', 'мил']:
                return int(number * 1000000)
        
        # Попытка 2: Текстовые числительные
        # "пятьдесят тысяч рублей"
        words = re.findall(r'[а-яё]+', text)
        
        total = 0
        current = 0
        
        for word in words:
            if word in self.number_words:
                value = self.number_words[word]
                
                if value >= 1000:
                    # Множитель: применяем к накопленному числу
                    current = (current or 1) * value
                    total += current
                    current = 0
                else:
                    # Обычное число: накапливаем
                    current += value
        
        # Добавить остаток
        total += current
        
        if total > 0:
            return total
        
        # Попытка 3: Чистые цифры
        digits_match = re.search(r'\d+', text)
        if digits_match:
            # Очистка от пробелов в числах типа "10 000"
            clean_digits = re.sub(r'\s+', '', digits_match.group())
            return int(clean_digits)
        
        return None
    
    def parse_budget_range(self, text: str) -> Dict[str, Optional[int]]:
        """
        Извлечение бюджетного диапазона из текста.
        
        Examples:
            "от 50 до 100 тысяч" → {"min": 50000, "max": 100000}
            "бюджет до 200к" → {"min": None, "max": 200000}
            "примерно 75 тыс" → {"min": 75000, "max": 75000}
        
        Args:
            text: текст с упоминанием бюджета
            
        Returns:
            {"min": int|None, "max": int|None}
        """
        result = {"min": None, "max": None}
        
        # Паттерн: "от X до Y"
        range_match = re.search(
            r'от\s+([а-яё\d\s.,]+?)\s+до\s+([а-яё\d\s.,]+?)(?:\s|$|[₽руб])',
            text,
            re.IGNORECASE
        )
        if range_match:
            min_text = range_match.group(1)
            max_text = range_match.group(2)
            
            result["min"] = self.text_to_number(min_text)
            result["max"] = self.text_to_number(max_text)
            
            return result
        
        # Паттерн: "до X"
        max_match = re.search(
            r'(?:до|максимум|не более)\s+([а-яё\d\s.,]+?)(?:\s|$|[₽руб])',
            text,
            re.IGNORECASE
        )
        if max_match:
            result["max"] = self.text_to_number(max_match.group(1))
            return result
        
        # Паттерн: "от X"
        min_match = re.search(
            r'от\s+([а-яё\d\s.,]+?)(?:\s|$|[₽руб])',
            text,
            re.IGNORECASE
        )
        if min_match:
            result["min"] = self.text_to_number(min_match.group(1))
            return result
        
        # Паттерн: "примерно X", "около X"
        approx_match = re.search(
            r'(?:примерно|около|приблизительно|~)\s+([а-яё\d\s.,]+?)(?:\s|$|[₽руб])',
            text,
            re.IGNORECASE
        )
        if approx_match:
            value = self.text_to_number(approx_match.group(1))
            result["min"] = value
            result["max"] = value
            return result
        
        # Паттерн: просто число с валютой
        simple_match = re.search(
            r'(\d+(?:\s*\d+)*)\s*(?:₽|руб|рублей|тысяч|тыс|к)',
            text,
            re.IGNORECASE
        )
        if simple_match:
            value = self.text_to_number(simple_match.group(0))
            result["min"] = value
            result["max"] = value
            return result
        
        return result
    
    def parse_deadline(self, text: str) -> Optional[datetime]:
        """
        Извлечение дедлайна из текста с преобразованием в дату.
        
        Examples:
            "срочно" → datetime.now()
            "завтра" → datetime.now() + 1 day
            "до конца недели" → ближайшее воскресенье
            "до 25 числа" → 25-е число текущего месяца
        
        Args:
            text: текст с упоминанием срока
            
        Returns:
            datetime или None
        """
        text = text.lower()
        now = datetime.now()
        
        # Срочные маркеры
        if any(word in text for word in ["срочно", "асап", "asap", "немедленно"]):
            return now
        
        # Относительные периоды
        for period_text, days in self.time_periods.items():
            if period_text in text:
                return now + timedelta(days=days)
        
        # "до конца недели"
        if "конец недели" in text or "конца недели" in text:
            # Найти ближайшее воскресенье
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            return now + timedelta(days=days_until_sunday)
        
        # "до конца месяца"
        if "конец месяца" in text or "конца месяца" in text:
            # Последний день текущего месяца
            next_month = now.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            return last_day
        
        # "до X числа"
        date_match = re.search(r'до\s+(\d+)\s*(?:числа|го)?', text)
        if date_match:
            day = int(date_match.group(1))
            try:
                deadline = now.replace(day=day)
                # Если день уже прошел в этом месяце, берем следующий
                if deadline < now:
                    next_month = deadline.replace(day=28) + timedelta(days=4)
                    deadline = next_month.replace(day=day)
                return deadline
            except ValueError:
                pass
        
        # "через N дней/недель"
        period_match = re.search(
            r'через\s+(\d+|[а-яё]+)\s+(день|дня|дней|неделю|недели|недель|месяц|месяца|месяцев)',
            text
        )
        if period_match:
            number_text = period_match.group(1)
            period_type = period_match.group(2)
            
            number = self.text_to_number(number_text) or (int(number_text) if number_text.isdigit() else 1)
            
            if period_type in ['день', 'дня', 'дней']:
                return now + timedelta(days=number)
            elif period_type in ['неделю', 'недели', 'недель']:
                return now + timedelta(weeks=number)
            elif period_type in ['месяц', 'месяца', 'месяцев']:
                return now + timedelta(days=number * 30)
        
        return None


# Singleton instance
text_normalizer = TextNormalizer()
