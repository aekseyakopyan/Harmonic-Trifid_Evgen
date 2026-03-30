"""
Fine-tuning rubert-tiny2 на квал-лидах.
Критерии квала: направление работы | конкретная задача | срочность
Устройство: MPS (Apple Silicon) если доступен, иначе CPU.
"""

import re, os, sqlite3, pickle, warnings, random
warnings.filterwarnings("ignore")

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report

# ── Пути ──────────────────────────────────────────────────────────
DB_PATH     = "harmonic-trifid-data/vacancies.db"
SAVE_DIR    = "systems/parser/bert_finetuned"
MODEL_NAME  = "cointegrated/rubert-tiny2"

# ── Гиперпараметры ─────────────────────────────────────────────────
MAX_LEN     = 256
BATCH_SIZE  = 16
EPOCHS      = 4
LR          = 2e-5
WARMUP_FRAC = 0.1
THRESHOLD   = 0.60

# ── Устройство ─────────────────────────────────────────────────────
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
    print("🍎 Используем MPS (Apple Silicon)")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    print("🖥️  Используем CUDA")
else:
    DEVICE = torch.device("cpu")
    print("💻 Используем CPU")

# ── Паттерны квалификации ──────────────────────────────────────────
DIRECTION_PATTERNS = [
    r"#(?:директолог|контекстолог|авитолог|таргетолог|сайтолог|тильдолог|техспец|смм|smm|ботмейкер|вебдизайнер|seo|маркетолог|копирайтер|редактор|дизайнер)",
    r"\b(?:яндекс[. ]?директ|google\s*ads|ppc|контекстная\s+реклама)\b",
    r"\b(?:seo|сео)\b.{0,40}(?:продвиж|оптимиз|аудит|специалист)",
    r"\b(?:авито|avito)\b.{0,30}(?:продвиж|реклам|настро|специалист)",
    r"\b(?:таргет|таргетиров)\w*.{0,30}(?:вк|вконтакте|instagram|fb|facebook|тикток)",
    r"(?:разработ|созда|сделат)\w+\s+(?:сайт|лендинг|интернет[- ]магазин)",
    r"\b(?:wordpress|tilda|тильда|bitrix|битрикс)\b.{0,40}(?:нужен|разработ|настро|специалист)",
    r"\b(?:smm|смм|контент[- ]менеджер|контентменеджер)\b.{0,30}(?:ищу|нужен|нужна)",
]
TASK_PATTERNS = [
    r"#ищу.{0,80}#(?:директолог|контекстолог|авитолог|таргетолог|сайтолог|дизайнер|smm|маркетолог|тильдолог|техспец|ботмейкер|вебдизайнер)",
    r"#(?:нужен|требуется|поиск).{0,60}#(?:директолог|контекстолог|авитолог|таргетолог|сайтолог|дизайнер|smm|маркетолог)",
    r"ищу\s+(?:специалист|подрядчик|фрилансер|исполнител)\w*.{0,80}(?:задач|проект|настро|созда|разработ|продвиж)",
    r"(?:нужно|нужен|нужна|требуется)\s+(?:специалист|подрядчик|фрилансер)\b.{0,60}(?:для|по|на|который|чтобы)",
    r"(?:задача|цель)\s*[:—–]\s*\S.{10,}",
    r"(?:сайт|магазин|бизнес|компания|кофейн|рестор|автосерв|клиник)\w*.{0,50}(?:нужен|нужна|ищу|ищем|требуется)",
    r"(?:нужно|надо)\s+(?:настроить|создать|сделать|запустить|разработать|продвинуть|поднять|вывести)\b",
    r"ищем\s+(?:специалист|подрядчик|фрилансер|исполнител)\w*",
]
URGENCY_PATTERNS = [
    r"\bсрочно\b", r"#срочно\b", r"\basap\b", r"\bгорит\b",
    r"\bнужен\s+(?:сейчас|сегодня|срочно)\b",
    r"\bдо\s+(?:завтра|конца\s+(?:недели|дня|месяца))\b",
    r"\bдедлайн\b", r"\bбыстрый\s+старт\b",
]
STAFF_PATTERNS = [
    r"\bв\s+штат\b.{0,30}(?:по\s+договору|договор|оформление|трудоустройств)",
    r"\bграфик\b.{0,10}\d+/\d+\b",
    r"\bполный\s+рабочий\s+день\b",
    r"\bоклад\b.{0,30}\d+\s*(?:₽|руб|тыс|к)\b",
    r"(?:скиньте|присылайте|пришлите)\s+(?:своё\s+)?(?:резюме|портфолио|кейсы)\b",
]

def is_qual(text: str) -> bool:
    t = text.lower()
    if any(re.search(p, t) for p in STAFF_PATTERNS):
        return False
    return (
        any(re.search(p, t) for p in DIRECTION_PATTERNS) or
        any(re.search(p, t) for p in TASK_PATTERNS) or
        any(re.search(p, t) for p in URGENCY_PATTERNS)
    )

# ── Данные ─────────────────────────────────────────────────────────
print("Загрузка данных из БД...")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("""SELECT text FROM vacancies WHERE status='accepted'
    AND (dirty_executor IS NULL OR dirty_executor=0)
    AND text IS NOT NULL AND LENGTH(text) > 30""")
accepted = [r[0] for r in cur.fetchall()]

cur.execute("""SELECT text FROM vacancies WHERE status='rejected'
    AND text IS NOT NULL AND LENGTH(text) > 30 LIMIT 8000""")
rejected = [r[0] for r in cur.fetchall()]
conn.close()

qual    = [t for t in accepted if is_qual(t)]
texts   = qual + rejected
labels  = [1]*len(qual) + [0]*len(rejected)

print(f"  Квал-лиды:  {len(qual)}")
print(f"  Rejected:   {len(rejected)}")
print(f"  Итого:      {len(texts)}")

# ── Токенайзер ─────────────────────────────────────────────────────
print(f"Загрузка {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# ── Dataset ────────────────────────────────────────────────────────
class LeadDataset(Dataset):
    def __init__(self, texts, labels):
        enc = tokenizer(
            texts,
            max_length=MAX_LEN,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        self.input_ids      = enc["input_ids"]
        self.attention_mask = enc["attention_mask"]
        self.labels         = torch.tensor(labels, dtype=torch.long)

    def __len__(self):  return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids":      self.input_ids[idx],
            "attention_mask": self.attention_mask[idx],
            "labels":         self.labels[idx],
        }

X_train, X_test, y_train, y_test = train_test_split(
    texts, labels, test_size=0.15, random_state=42, stratify=labels
)
print(f"Train: {len(X_train)}  Test: {len(X_test)}")

print("Токенизация...")
train_ds = LeadDataset(X_train, y_train)
test_ds  = LeadDataset(X_test,  y_test)

train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
test_dl  = DataLoader(test_ds,  batch_size=BATCH_SIZE)

# ── Модель ─────────────────────────────────────────────────────────
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
model.to(DEVICE)

optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
total_steps = len(train_dl) * EPOCHS
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=int(total_steps * WARMUP_FRAC),
    num_training_steps=total_steps,
)

# ── Обучение ───────────────────────────────────────────────────────
print(f"\nОбучение {EPOCHS} эпох на {DEVICE}...")
best_f1 = 0.0

for epoch in range(EPOCHS):
    model.train()
    total_loss = 0.0
    for batch in train_dl:
        batch = {k: v.to(DEVICE) for k, v in batch.items()}
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()
        total_loss += loss.item()

    avg_loss = total_loss / len(train_dl)

    # Валидация
    model.eval()
    all_probs, all_labels = [], []
    with torch.no_grad():
        for batch in test_dl:
            batch = {k: v.to(DEVICE) for k, v in batch.items()}
            outputs = model(**batch)
            probs = torch.softmax(outputs.logits, dim=1)[:, 1].cpu().tolist()
            all_probs.extend(probs)
            all_labels.extend(batch["labels"].cpu().tolist())

    y_pred = [1 if p >= THRESHOLD else 0 for p in all_probs]
    p = precision_score(all_labels, y_pred, zero_division=0)
    r = recall_score(all_labels, y_pred, zero_division=0)
    f = f1_score(all_labels, y_pred, zero_division=0)
    print(f"Эпоха {epoch+1}/{EPOCHS}  loss={avg_loss:.4f}  P={p:.3f}  R={r:.3f}  F1={f:.3f}")

    if f > best_f1:
        best_f1 = f
        # Сохраняем лучшую модель
        os.makedirs(SAVE_DIR, exist_ok=True)
        model.save_pretrained(SAVE_DIR)
        tokenizer.save_pretrained(SAVE_DIR)
        print(f"  ✅ Лучшая модель сохранена → {SAVE_DIR} (F1={f:.3f})")

print(f"\n── Финальный отчёт (порог {THRESHOLD}) ──")
print(classification_report(all_labels, y_pred, target_names=["rejected", "qual_lead"]))
print(f"Модель сохранена: {SAVE_DIR}")
