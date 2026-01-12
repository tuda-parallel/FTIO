"""
Data models for storing and managing prediction data from FTIO
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np
from datetime import datetime


@dataclass
class FrequencyCandidate:
    """Individual frequency candidate with confidence"""
    frequency: float
    confidence: float


@dataclass
class ChangePoint:
    """ADWIN detected change point information"""
    prediction_id: int
    timestamp: float
    old_frequency: float
    new_frequency: float
    frequency_change_percent: float
    sample_number: int
    cut_position: int
    total_samples: int
    
    
@dataclass
class PredictionData:
    """Single prediction instance data"""
    prediction_id: int
    timestamp: str
    dominant_freq: float
    dominant_period: float
    confidence: float
    candidates: List[FrequencyCandidate]
    time_window: tuple  # (start, end) in seconds
    total_bytes: str
    bytes_transferred: str
    current_hits: int
    periodic_probability: float
    frequency_range: tuple  # (min_freq, max_freq)
    period_range: tuple  # (min_period, max_period)
    is_change_point: bool = False
    change_point: Optional[ChangePoint] = None
    sample_number: Optional[int] = None


class PredictionDataStore:
    """Manages all prediction data and provides query methods"""
    
    def __init__(self):
        self.predictions: List[PredictionData] = []
        self.change_points: List[ChangePoint] = []
        self.current_prediction_id = -1
        
    def add_prediction(self, prediction: PredictionData):
        """Add a new prediction to the store"""
        self.predictions.append(prediction)
        if prediction.is_change_point and prediction.change_point:
            self.change_points.append(prediction.change_point)
    
    def get_prediction_by_id(self, pred_id: int) -> Optional[PredictionData]:
        """Get prediction by ID"""
        for pred in self.predictions:
            if pred.prediction_id == pred_id:
                return pred
        return None
    
    def get_frequency_timeline(self) -> tuple:
        """Get data for frequency timeline plot"""
        if not self.predictions:
            return [], [], []
            
        pred_ids = [p.prediction_id for p in self.predictions]
        frequencies = [p.dominant_freq for p in self.predictions]
        confidences = [p.confidence for p in self.predictions]
        
        return pred_ids, frequencies, confidences
    
    def get_candidate_frequencies(self) -> Dict[int, List[FrequencyCandidate]]:
        """Get all candidate frequencies by prediction ID"""
        candidates_dict = {}
        for pred in self.predictions:
            if pred.candidates:
                candidates_dict[pred.prediction_id] = pred.candidates
        return candidates_dict
    
    def get_change_points_for_timeline(self) -> tuple:
        """Get change point data for timeline visualization"""
        if not self.change_points:
            return [], [], []
            
        pred_ids = [cp.prediction_id for cp in self.change_points]
        frequencies = [cp.new_frequency for cp in self.change_points]
        labels = [f"{cp.old_frequency:.2f} → {cp.new_frequency:.2f} Hz" 
                 for cp in self.change_points]
        
        return pred_ids, frequencies, labels
    
    def generate_cosine_wave(self, prediction_id: int, num_points: int = 1000) -> tuple:
        """Generate cosine wave data for a specific prediction - DOMINANT FREQUENCY ONLY"""
        pred = self.get_prediction_by_id(prediction_id)
        if not pred:
            return [], [], []
        
        start_time, end_time = pred.time_window
        duration = end_time - start_time
        
        # Use relative time (0 to duration) for individual prediction view
        t_relative = np.linspace(0, duration, num_points)
        
        # Primary cosine wave (dominant frequency ONLY) - phase starts at 0
        primary_wave = np.cos(2 * np.pi * pred.dominant_freq * t_relative)
        
        # NO candidate waves - only return empty list for backward compatibility
        candidate_waves = []
        
        return t_relative, primary_wave, candidate_waves
    
    def get_latest_predictions(self, n: int = 50) -> List[PredictionData]:
        """Get the latest N predictions"""
        return self.predictions[-n:] if len(self.predictions) >= n else self.predictions
    
    def clear_data(self):
        """Clear all stored data"""
        self.predictions.clear()
        self.change_points.clear()
        self.current_prediction_id = -1
