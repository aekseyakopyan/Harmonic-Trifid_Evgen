"""
Niche Detector - определяет нишу проекта из текста вакансии.
"""

import re
from typing import Dict, List, Optional


class NicheDetector:
    """Детектор ниши проекта"""
    
    # Паттерны для извлечения ниши
    PATTERNS = [
        (r"для\s+([а-яА-Яa-zA-Z\s-]+(?:компании|фирмы|проекта|бизнеса))", "для [ниша]"),
        (r"в нише\s+([а-яА-Яa-zA-Z\s-]+)", "в нише [ниша]"),
        (r"проект\s+([а-яА-Яa-zA-Z\s-]+)", "проект [ниша]"),
        (r"(?:seo|контекст|таргет)[- ]специалист\s+(?:по|для)\s+([а-яА-Яa-zA-Z\s-]+)", "[специалист] по [ниша]"),
        (r"(?:интернет[- ])?магазин\s+([а-яА-Яa-zA-Z\s]+)", "магазин [ниша]"),
        (r"(?:сайт|лендинг)\s+(?:для|по)\s+([а-яА-Яa-zA-Z\s-]+)", "сайт для [ниша]"),
    ]
    
    # Известные ниши с ключевыми словами
    KNOWN_NICHES = {
        "строительство": ["строительств", "коттедж", "дом", "ремонт", "стройк"],
        "недвижимость": ["недвижимост", "квартир", "жилье", "риэлтор"],
        "e-commerce": ["интернет-магазин", "e-commerce", "ecommerce", "онлайн-магазин", "маркетплейс"],
        "онлайн-школа": ["онлайн-школ", "курс", "обучение онлайн", "образование", "вебинар", "инфопродукт"],
        "медицина": ["медицин", "клиник", "стоматолог", "врач", "здоровье"],
        "автомобили": ["автомобил", "авто", "машин", "автосервис", "автозапчаст"],
        "красота": ["салон красоты", "парикмахерск", "косметолог", "маникюр", "барбершоп"],
        "фитнес": ["фитнес", "спортзал", "тренажерн", "йога", "спорт"],
        "ресторан": ["ресторан", "кафе", "бар", "общепит", "доставка еды"],
        "юриспруденция": ["юридическ", "адвокат", "юрист", "право"],
        "финансы": ["финанс", "банк", "кредит", "инвестиц", "страхов"],
        "туризм": ["туризм", "туристическ", "путешеств", "тур", "отдых"],
    }
    
    def detect_niche(self, text: str) -> Dict:
        """
        Определяет нишу из текста.
        
        Returns:
            {
                'niche_found': bool,
                'niche_name': str,
                'niche_keywords_matched': list,
                'extraction_confidence': str,
                'extraction_pattern': str
            }
        """
        text_lower = text.lower()
        
        # Попытка 1: Извлечение по паттернам
        pattern_result = self._match_patterns(text_lower)
        if pattern_result:
            # Попытка сопоставить с известными нишами
            niche_name, keywords = self._match_to_known_niches(pattern_result['extracted_text'])
            
            if niche_name:
                return {
                    'niche_found': True,
                    'niche_name': niche_name,
                    'niche_keywords_matched': keywords,
                    'extraction_confidence': 'high',
                    'extraction_pattern': pattern_result['pattern_type'],
                    'raw_extracted': pattern_result['extracted_text']
                }
            else:
                # Используем извлеченный текст как нишу
                return {
                    'niche_found': True,
                    'niche_name': pattern_result['extracted_text'].strip(),
                    'niche_keywords_matched': [],
                    'extraction_confidence': 'medium',
                    'extraction_pattern': pattern_result['pattern_type'],
                    'raw_extracted': pattern_result['extracted_text']
                }
        
        # Попытка 2: Прямое сопоставление с известными нишами по контексту
        niche_name, keywords = self._match_to_known_niches(text_lower)
        if niche_name:
            return {
                'niche_found': True,
                'niche_name': niche_name,
                'niche_keywords_matched': keywords,
                'extraction_confidence': 'medium',
                'extraction_pattern': 'context_matching',
                'raw_extracted': None
            }
        
        # Ниша не найдена
        return {
            'niche_found': False,
            'niche_name': None,
            'niche_keywords_matched': [],
            'extraction_confidence': 'none',
            'extraction_pattern': None,
            'raw_extracted': None
        }
    
    def _match_patterns(self, text: str) -> Optional[Dict]:
        """Пытается извлечь нишу по паттернам"""
        for pattern, pattern_type in self.PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # Очистка от лишних слов
                extracted = re.sub(r'\s+(и|или|,)\s+.*$', '', extracted)
                extracted = extracted[:50]  # Ограничиваем длину
                
                return {
                    'extracted_text': extracted,
                    'pattern_type': pattern_type
                }
        
        return None
    
    def _match_to_known_niches(self, text: str) -> tuple[Optional[str], List[str]]:
        """Сопоставляет текст с известными нишами"""
        best_match = None
        best_score = 0
        matched_keywords = []
        
        for niche_name, keywords in self.KNOWN_NICHES.items():
            matches = []
            for keyword in keywords:
                if keyword in text:
                    matches.append(keyword)
            
            score = len(matches)
            if score > best_score:
                best_match = niche_name
                best_score = score
                matched_keywords = matches
        
        if best_score > 0:
            return best_match, matched_keywords
        
        return None, []
