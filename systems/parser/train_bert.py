"""
BERT classifier training pipeline с MLflow tracking.
"""

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import torch
from torch.utils.data import Dataset
import pandas as pd
from core.utils.structured_logger import get_logger
from typing import List, Dict
import os

logger = get_logger(__name__)


class LeadDataset(Dataset):
    """PyTorch Dataset для обучения BERT classifier"""
    
    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 512):
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=max_length,
            return_tensors="pt"
        )
        self.labels = torch.tensor(labels)
    
    def __len__(self):
        return len(self.labels)
    
    def __getitem__(self, idx):
        item = {key: val[idx] for key, val in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item


def compute_metrics(pred):
    """Расчет метрик для Trainer"""
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary"
    )
    acc = accuracy_score(labels, preds)
    
    return {
        "accuracy": acc,
        "f1": f1,
        "precision": precision,
        "recall": recall
    }


def train_bert_classifier(
    train_data: pd.DataFrame,
    model_name: str = "cointegrated/rubert-tiny",
    output_dir: str = "models/bert_retrained",
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5
) -> Dict:
    """Fine-tune BERT classifier."""
    logger.info("training_started", train_size=len(train_data))
    
    # Split
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        train_data["text"].tolist(),
        train_data["is_lead"].tolist(),
        test_size=0.2,
        stratify=train_data["is_lead"],
        random_state=42
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
    
    train_dataset = LeadDataset(train_texts, train_labels, tokenizer)
    val_dataset = LeadDataset(val_texts, val_labels, tokenizer)
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_steps=10, # small for retrain
        weight_decay=0.01,
        logging_dir=f"{output_dir}/logs",
        logging_steps=5,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        save_total_limit=1,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics
    )
    
    trainer.train()
    eval_results = trainer.evaluate()
    
    os.makedirs(output_dir, exist_ok=True)
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    return {
        "train_accuracy": eval_results.get("eval_accuracy", 0),
        "val_f1": eval_results.get("eval_f1", 0)
    }
