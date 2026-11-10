import logging
from pathlib import Path
from typing import Dict, Any, Optional
import joblib

from app.config import settings

logger = logging.getLogger(__name__)


class KMRLDocumentClassifier:
    """
    Wrapper around the pre-trained KMRL Document Classifier.
    Predicts one of the 8 KMRL core categories with confidence scores.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path or settings.KMRL_MODEL_PATH)
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        if self.model_path.exists():
            try:
                self.model = joblib.load(str(self.model_path))
                logger.info(f"Loaded KMRL Document Classifier from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load KMRL Document Classifier from {self.model_path}: {e}")
                self.model = None
        else:
            logger.warning(f"KMRL Document Classifier not found at {self.model_path}")
            self.model = None

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Classify input text into one of 8 KMRL categories.
        Returns:
            {
                "predicted_category": str,
                "confidence": float (0.0 to 1.0),
                "probabilities": dict
            }
        """
        clean_text = text.strip()
        if not clean_text:
            return {
                "predicted_category": "Passenger Grievances",
                "confidence": 0.5,
                "probabilities": {},
            }

        if self.model is None:
            # Fallback if model binary is missing
            return {
                "predicted_category": "Passenger Grievances",
                "confidence": 0.5,
                "probabilities": {},
            }

        try:
            prediction = self.model.predict([clean_text])[0]
            probabilities = self.model.predict_proba([clean_text])[0]
            confidence = float(max(probabilities))

            probs_dict = {
                cat: round(float(prob), 4)
                for cat, prob in zip(self.model.classes_, probabilities)
            }

            return {
                "predicted_category": str(prediction),
                "confidence": round(confidence, 4),
                "probabilities": probs_dict,
            }
        except Exception as e:
            logger.error(f"Error during classifier inference: {e}")
            return {
                "predicted_category": "Passenger Grievances",
                "confidence": 0.5,
                "probabilities": {},
            }


# Singleton instance
classifier = KMRLDocumentClassifier()

