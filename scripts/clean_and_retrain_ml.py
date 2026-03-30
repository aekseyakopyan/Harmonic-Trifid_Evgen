"""
Скрипт очистки загрязнённых данных и переобучения ML-классификатора.

Проблема: в vacancies.db статус 'accepted' имеют ~29% сообщений от исполнителей.
ML-классификатор (TF-IDF + LogReg) обучался на этих данных, выучив паттерны
исполнителей как ПОЛОЖИТЕЛЬНЫЕ примеры → обратная петля.

Что делает скрипт:
1. Помечает "грязные" accepted-записи (исполнители) как dirty_executor=1
2. Переобучает ML только на чистых данных
3. Сохраняет новый ml_classifier.pkl
4. Выводит статистику до/после
"""

import re
import sys
import sqlite3
import pickle
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parents[1]))

DB_PATH = Path(__file__).parents[1] / "harmonic-trifid-data" / "vacancies.db"
MODEL_PATH = Path(__file__).parents[1] / "systems" / "parser" / "ml_classifier.pkl"
MODEL_BACKUP_PATH = MODEL_PATH.with_suffix(".pkl.bak")

# Импортируем актуальные паттерны из lead_filter_advanced
from systems.parser.lead_filter_advanced import BLACKLIST_CONFIG

# Все категории паттернов, которые должны быть отклонены (не клиентские лиды)
_DIRTY_PATTERN_KEYS = [
    "scam_patterns",
    "executor_offer_patterns",
    "crypto_scam_patterns",
    "mlm_scam_patterns",
    "mass_spam_patterns",
    "agency_hiring_patterns",
]

_ALL_DIRTY_PATTERNS = []
for key in _DIRTY_PATTERN_KEYS:
    _ALL_DIRTY_PATTERNS.extend(BLACKLIST_CONFIG.get(key, []))

# Ключевые слова (не regex) из scam_keywords и irrelevant_hard
_DIRTY_KEYWORDS = (
    BLACKLIST_CONFIG.get("scam_keywords", []) +
    BLACKLIST_CONFIG.get("irrelevant_hard", [])
)


def is_dirty(text: str) -> bool:
    """Возвращает True если текст должен быть отклонён (исполнитель / скам / спам)."""
    text_lower = text.lower()
    for pattern in _ALL_DIRTY_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    for kw in _DIRTY_KEYWORDS:
        if kw in text_lower:
            return True
    return False


def mark_dirty_records(conn: sqlite3.Connection) -> int:
    """
    Добавляет колонку dirty_executor если её нет.
    Помечает грязные accepted-записи.
    Возвращает количество помеченных записей.
    """
    cur = conn.cursor()

    # Добавить колонку если нет
    try:
        cur.execute("ALTER TABLE vacancies ADD COLUMN dirty_executor INTEGER DEFAULT 0")
        conn.commit()
        print("  Добавлена колонка dirty_executor")
    except sqlite3.OperationalError:
        pass  # колонка уже есть

    # Сбросить старые пометки
    cur.execute("UPDATE vacancies SET dirty_executor = 0")

    # Загружаем все accepted
    cur.execute("SELECT id, text FROM vacancies WHERE status = 'accepted'")
    rows = cur.fetchall()

    dirty_ids = []
    for row_id, text in rows:
        if text and is_dirty(text):
            dirty_ids.append(row_id)

    if dirty_ids:
        cur.executemany(
            "UPDATE vacancies SET dirty_executor = 1 WHERE id = ?",
            [(i,) for i in dirty_ids]
        )
        conn.commit()

    return len(dirty_ids)


def retrain_classifier(conn: sqlite3.Connection) -> dict:
    """
    Переобучает ML на чистых данных (без dirty_executor=1).
    Возвращает метрики.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    import numpy as np

    cur = conn.cursor()

    # Загружаем чистые данные
    cur.execute("""
        SELECT text, status
        FROM vacancies
        WHERE status IN ('accepted', 'rejected')
          AND (dirty_executor IS NULL OR dirty_executor = 0)
          AND text IS NOT NULL
          AND LENGTH(text) > 20
    """)
    rows = cur.fetchall()

    texts = [r[0] for r in rows]
    labels = [1 if r[1] == 'accepted' else 0 for r in rows]

    pos_texts = [t for t, l in zip(texts, labels) if l == 1]
    neg_texts = [t for t, l in zip(texts, labels) if l == 0]

    print(f"  Всего записей: {len(texts)}")
    print(f"  Позитивных (accepted): {len(pos_texts)}, Негативных: {len(neg_texts)}")

    if len(pos_texts) < 50:
        print("  ОШИБКА: Слишком мало позитивных примеров (<50). Переобучение невозможно.")
        return {}

    # Undersample negatives до соотношения 1:2 (оптимум по экспериментам: P=0.847 R=0.929 F1=0.886)
    MAX_NEG_RATIO = 2
    max_neg = len(pos_texts) * MAX_NEG_RATIO
    if len(neg_texts) > max_neg:
        import random
        random.seed(42)
        neg_texts = random.sample(neg_texts, max_neg)
        print(f"  Undersampling негативов: {len(neg_texts)} (ratio 1:{MAX_NEG_RATIO})")

    texts = pos_texts + neg_texts
    labels = [1] * len(pos_texts) + [0] * len(neg_texts)
    print(f"  Итоговая выборка: {len(texts)} записей")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 3), min_df=2)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    clf = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
    clf.fit(X_train_vec, y_train)

    y_pred = clf.predict(X_test_vec)
    report = classification_report(y_test, y_pred, output_dict=True)

    # Сохраняем модель
    if MODEL_PATH.exists():
        import shutil
        shutil.copy(MODEL_PATH, MODEL_BACKUP_PATH)
        print(f"  Бэкап старой модели → {MODEL_BACKUP_PATH}")

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({'vectorizer': vectorizer, 'classifier': clf}, f)

    print(f"  Новая модель сохранена → {MODEL_PATH}")

    return {
        'accuracy': report['accuracy'],
        'precision_1': report['1']['precision'],
        'recall_1': report['1']['recall'],
        'f1_1': report['1']['f1-score'],
    }


def main():
    print("=" * 60)
    print("Очистка загрязнённых данных и переобучение ML")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"ОШИБКА: БД не найдена: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    # Статистика до
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vacancies WHERE status='accepted'")
    total_accepted = cur.fetchone()[0]

    print(f"\n[1/3] Анализ принятых лидов ({total_accepted} записей)...")
    print(f"  Используем {len(_ALL_DIRTY_PATTERNS)} паттернов и {len(_DIRTY_KEYWORDS)} ключевых слов")
    dirty_count = mark_dirty_records(conn)
    clean_count = total_accepted - dirty_count

    print(f"  Грязные (исполнители/скам/спам): {dirty_count} ({100*dirty_count/total_accepted:.1f}%)")
    print(f"  Чистые клиентские лиды: {clean_count} ({100*clean_count/total_accepted:.1f}%)")

    print(f"\n[2/3] Переобучение ML на {clean_count} чистых примерах...")
    metrics = retrain_classifier(conn)

    if metrics:
        print(f"\n[3/3] Метрики новой модели:")
        print(f"  Accuracy:  {metrics['accuracy']:.3f}")
        print(f"  Precision: {metrics['precision_1']:.3f}")
        print(f"  Recall:    {metrics['recall_1']:.3f}")
        print(f"  F1:        {metrics['f1_1']:.3f}")
    else:
        print("\n[3/3] Переобучение не выполнено.")

    conn.close()
    print("\nГотово.")


if __name__ == "__main__":
    main()
