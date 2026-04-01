
import pickle
import os
import time
import numpy as np
from typing import Dict, Any, Optional
from core.utils.logger import logger

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from scipy.sparse import hstack
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class MLLeadClassifier:
    """
    ML-классификатор лидов v2 — квалификация по критериям:
    направление работы, конкретная задача, срочность.
    Использует двойную векторизацию (word + char n-grams) для
    лучшего распознавания морфологических вариантов.
    """

    def __init__(self, model_path: str = "systems/parser/ml_classifier_qual.pkl"):
        self.model_path = model_path
        self.vectorizer_word = None
        self.vectorizer_char = None
        self.model = None
        self.threshold = 0.60
        self.is_trained = False

        if os.path.exists(self.model_path):
            # Предупреждаем если модель устарела (> 7 дней)
            age_days = (time.time() - os.path.getmtime(self.model_path)) / 86400
            if age_days > 7:
                logger.warning(
                    f"[MLClassifier] ⚠️ Модель устарела: {age_days:.0f} дней без переобучения. "
                    f"Рекомендуется запустить clean_and_retrain_ml.py"
                )
            self.load(self.model_path)
        elif os.path.exists("ml_classifier.pkl"):
            logger.error(
                "[MLClassifier] ❌ FALLBACK на старую модель! "
                "ml_classifier_qual.pkl не найден — точность снижена."
            )
            self._load_legacy("ml_classifier.pkl")

    def predict(self, text: str) -> Dict[str, Any]:
        if not self.is_trained or not SKLEARN_AVAILABLE:
            return {"is_lead": False, "confidence": 0.0, "method": "ML_NONE"}

        try:
            if self.vectorizer_char is not None:
                # Новая двойная модель
                x_w = self.vectorizer_word.transform([text])
                x_c = self.vectorizer_char.transform([text])
                vec = hstack([x_w, x_c])
            else:
                # Легаси (один векторайзер)
                vec = self.vectorizer_word.transform([text])

            proba = self.model.predict_proba(vec)[0]
            confidence = float(proba[1])

            return {
                "is_lead": confidence >= self.threshold,
                "confidence": confidence,
                "method": "ML_QUAL_V2" if self.vectorizer_char is not None else "ML_LEGACY"
            }
        except Exception as e:
            return {"is_lead": False, "confidence": 0.0, "method": f"ML_ERROR:{e}"}

    def train_from_database(self, db_path: str):
        """Переобучение на данных БД — запускается из clean_and_retrain_ml.py."""
        import sqlite3
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn не установлен")

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT text, status FROM vacancies
            WHERE status IN ('accepted', 'rejected')
              AND (dirty_executor IS NULL OR dirty_executor = 0)
              AND text IS NOT NULL AND LENGTH(text) > 30
        """)
        data = cur.fetchall()
        conn.close()

        if len(data) < 100:
            raise ValueError(f"Мало данных для обучения: {len(data)}")

        texts = [r[0] for r in data]
        labels = [1 if r[1] == 'accepted' else 0 for r in data]

        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )

        self.vectorizer_word = TfidfVectorizer(
            analyzer='word', ngram_range=(1, 3),
            max_features=50000, min_df=2, sublinear_tf=True
        )
        self.vectorizer_char = TfidfVectorizer(
            analyzer='char_wb', ngram_range=(3, 5),
            max_features=50000, min_df=2, sublinear_tf=True
        )

        X_tr = hstack([
            self.vectorizer_word.fit_transform(X_train),
            self.vectorizer_char.fit_transform(X_train)
        ])
        X_te = hstack([
            self.vectorizer_word.transform(X_test),
            self.vectorizer_char.transform(X_test)
        ])

        self.model = LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced')
        self.model.fit(X_tr, y_train)
        self.is_trained = True

        y_prob = self.model.predict_proba(X_te)[:, 1]
        y_pred = (y_prob >= self.threshold).astype(int)

        from sklearn.metrics import precision_score, recall_score, f1_score
        return {
            "precision": precision_score(y_test, y_pred),
            "recall": recall_score(y_test, y_pred),
            "f1": f1_score(y_test, y_pred),
            "train_size": len(X_train),
            "test_size": len(X_test),
        }

    def save(self, path: Optional[str] = None):
        if not self.is_trained:
            return
        path = path or self.model_path
        with open(path, 'wb') as f:
            pickle.dump({
                'vectorizer_word': self.vectorizer_word,
                'vectorizer_char': self.vectorizer_char,
                'model': self.model,
                'threshold': self.threshold,
                'is_trained': self.is_trained,
                'version': '2.1_qual',
            }, f)

    def load(self, path: str):
        if not os.path.exists(path):
            return
        # Validate the path is inside the expected directory to prevent loading
        # a maliciously placed pickle from an arbitrary location
        resolved = os.path.realpath(path)
        expected_dir = os.path.realpath(os.path.dirname(self.model_path) or os.getcwd())
        if not resolved.startswith(expected_dir):
            print(f"[MLClassifier] Rejected load from unexpected path: {path}")
            return
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.vectorizer_word = data.get('vectorizer_word') or data.get('vectorizer')
            self.vectorizer_char = data.get('vectorizer_char')
            self.model = data.get('classifier') or data.get('model')
            self.threshold = data.get('threshold', 0.65)
            self.is_trained = bool(self.model and self.vectorizer_word)
        except Exception as e:
            print(f"[MLClassifier] Ошибка загрузки модели: {e}")

    def _load_legacy(self, path: str):
        """Загружает старую модель с одним векторайзером."""
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.vectorizer_word = data.get('vectorizer')
            self.vectorizer_char = None
            self.model = data.get('model')
            self.threshold = 0.5
            self.is_trained = bool(self.model and self.vectorizer_word)
        except Exception as e:
            print(f"[MLClassifier] Ошибка загрузки легаси-модели: {e}")


# Singleton
ml_classifier = MLLeadClassifier()
