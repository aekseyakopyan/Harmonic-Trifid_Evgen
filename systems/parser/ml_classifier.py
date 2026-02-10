
import sqlite3
import pickle
import os
import numpy as np
from typing import Dict, List, Any, Optional

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class MLLeadClassifier:
    """
    ML-классификатор лидов на основе размеченных данных.
    """
    
    def __init__(self, model_path: str = "ml_classifier.pkl"):
        self.model_path = model_path
        self.vectorizer = None
        self.model = None
        self.is_trained = False
        
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 3),  # униграммы, биграммы, триграммы
                min_df=2
                # stop_words='russian' # Requires additional data/handling for russian
            )
            self.model = LogisticRegression(class_weight='balanced', max_iter=1000)
        
        if os.path.exists(self.model_path):
            self.load(self.model_path)
    
    def train_from_database(self, db_path: str):
        """
        Обучает модель на размеченных данных из БД.
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is not installed.")
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Выбираем размеченные примеры (только те, что были одобрены или отклонены человеком/автоматикой)
        cursor.execute("""
            SELECT text, status 
            FROM vacancies 
            WHERE status IN ('accepted', 'rejected')
            AND text IS NOT NULL
            AND text != ''
        """)
        
        data = cursor.fetchall()
        conn.close()
        
        if len(data) < 50:
            raise ValueError(f"Недостаточно данных для обучения (минимум 50, сейчас {len(data)})")
        
        texts = [row[0] for row in data]
        labels = [1 if row[1] == 'accepted' else 0 for row in data]
        
        # Разделение на train/test
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Векторизация
        X_train_vec = self.vectorizer.fit_transform(X_train)
        X_test_vec = self.vectorizer.transform(X_test)
        
        # Обучение
        self.model.fit(X_train_vec, y_train)
        
        # Оценка
        train_score = self.model.score(X_train_vec, y_train)
        test_score = self.model.score(X_test_vec, y_test)
        
        self.is_trained = True
        
        return {
            "train_score": train_score,
            "test_score": test_score,
            "train_size": len(X_train),
            "test_size": len(X_test)
        }
    
    def predict(self, text: str) -> Dict[str, Any]:
        """
        Предсказывает вероятность того, что это лид.
        """
        if not self.is_trained or not SKLEARN_AVAILABLE:
            return {"is_lead": False, "confidence": 0.0, "method": "ML_NONE"}
        
        try:
            vec = self.vectorizer.transform([text])
            proba = self.model.predict_proba(vec)[0]
            
            return {
                "is_lead": proba[1] > 0.5,
                "confidence": float(proba[1]),
                "method": "ML_TFIDF"
            }
        except Exception as e:
            print(f"ML Prediction error: {e}")
            return {"is_lead": False, "confidence": 0.0, "method": "ML_ERROR"}
    
    def save(self, path: Optional[str] = None):
        """Сохраняет модель."""
        if not self.is_trained:
            return
        path = path or self.model_path
        with open(path, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'model': self.model,
                'is_trained': self.is_trained
            }, f)
    
    def load(self, path: str):
        """Загружает модель."""
        if not os.path.exists(path):
            return
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.vectorizer = data['vectorizer']
                self.model = data['model']
                self.is_trained = data['is_trained']
        except Exception as e:
            print(f"Error loading ML model: {e}")

# Singleton
ml_classifier = MLLeadClassifier()
