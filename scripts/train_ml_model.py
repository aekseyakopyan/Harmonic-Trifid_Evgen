
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from systems.parser.ml_classifier import ml_classifier

async def train_model():
    print("🧠 Training ML classifier...")
    try:
        metrics = ml_classifier.train_from_database("vacancies.db")
        
        print(f"✅ Training complete!")
        print(f"   Train accuracy: {metrics['train_score']:.2%}")
        print(f"   Test accuracy: {metrics['test_score']:.2%}")
        print(f"   Train size: {metrics['train_size']}")
        print(f"   Test size: {metrics['test_size']}")
        
        ml_classifier.save("ml_classifier.pkl")
        print("💾 Model saved to ml_classifier.pkl")
    except Exception as e:
        print(f"❌ Training failed: {e}")

if __name__ == "__main__":
    asyncio.run(train_model())
