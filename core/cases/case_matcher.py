"""
Case Matcher - подбирает релевантный кейс для вакансии.
"""

import json
from typing import Dict, List, Optional
from pathlib import Path


class CaseMatcher:
    """Подбор кейса под вакансию"""
    
    def __init__(self, cases_db_path: str = "cases/cases_db.json"):
        self.cases_db_path = Path(cases_db_path)
        self.cases = self._load_cases()
    
    def _load_cases(self) -> List[Dict]:
        """Загружает базу кейсов"""
        if not self.cases_db_path.exists():
            print(f"[WARNING] Cases database not found: {self.cases_db_path}")
            return []
        
        try:
            with open(self.cases_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('cases', [])
        except Exception as e:
            print(f"[ERROR] Failed to load cases: {e}")
            return []
    
    def find_matching_case(
        self, 
        specialization: str, 
        niche_data: Optional[Dict] = None
    ) -> Dict:
        """
        Находит подходящий кейс для вакансии.
        
        Args:
            specialization: специализация из вакансии
            niche_data: данные о нише от NicheDetector
        
        Returns:
            {
                'case_found': bool,
                'case_id': str,
                'match_score': float,
                'case_data': dict
            }
        """
        if not self.cases:
            return self._no_case_result()
        
        if not niche_data or not niche_data.get('niche_found'):
            # Ищем только по специализации
            return self._match_by_specialization_only(specialization)
        
        # Ищем по специализации + нише
        return self._match_by_specialization_and_niche(
            specialization,
            niche_data
        )
    
    def _match_by_specialization_and_niche(
        self, 
        specialization: str,
        niche_data: Dict
    ) -> Dict:
        """Поиск с учетом ниши"""
        niche_name = niche_data.get('niche_name', '').lower()
        niche_keywords = [kw.lower() for kw in niche_data.get('niche_keywords_matched', [])]
        
        candidates = []
        
        for case in self.cases:
            # Проверка специализации
            if case['specialization'].lower() != specialization.lower():
                continue
            
            # Расчет совпадения ниши
            case_niche = case.get('niche', '').lower()
            case_keywords = [kw.lower() for kw in case.get('niche_keywords', [])]
            
            match_score = self._calculate_niche_match_score(
                niche_name,
                niche_keywords,
                case_niche,
                case_keywords
            )
            
            if match_score > 0:
                candidates.append({
                    'case': case,
                    'score': match_score
                })
        
        if not candidates:
            # Fallback на поиск только по специализации
            return self._match_by_specialization_only(specialization)
        
        # Выбираем лучший
        candidates.sort(key=lambda x: x['score'], reverse=True)
        best = candidates[0]
        
        return {
            'case_found': True,
            'case_id': best['case']['case_id'],
            'match_score': best['score'],
            'case_data': best['case']
        }
    
    def _match_by_specialization_only(self, specialization: str) -> Dict:
        """Поиск только по специализации (без ниши)"""
        for case in self.cases:
            if case['specialization'].lower() == specialization.lower():
                return {
                    'case_found': True,
                    'case_id': case['case_id'],
                    'match_score': 0.5,  # Средний скор, т.к. ниша не совпала
                    'case_data': case
                }
        
        return self._no_case_result()
    
    def _calculate_niche_match_score(
        self,
        niche_name: str,
        niche_keywords: List[str],
        case_niche: str,
        case_keywords: List[str]
    ) -> float:
        """Рассчитывает скор совпадения ниши"""
        score = 0.0
        
        # Точное совпадение названия ниши
        if niche_name and case_niche and niche_name in case_niche:
            score += 1.0
        
        # Совпадение ключевых слов
        if niche_keywords and case_keywords:
            matched_keywords = set(niche_keywords) & set(case_keywords)
            keyword_score = len(matched_keywords) / len(case_keywords)
            score += keyword_score
        
        # Проверка вхождения ключевых слов кейса в название ниши
        if niche_name and case_keywords:
            for keyword in case_keywords:
                if keyword in niche_name:
                    score += 0.3
        
        return min(score, 1.0)  # Нормализуем до 1.0
    
    def _no_case_result(self) -> Dict:
        """Результат когда кейс не найден"""
        return {
            'case_found': False,
            'case_id': None,
            'match_score': 0.0,
            'case_data': None
        }
