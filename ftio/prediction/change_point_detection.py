"""Change point detection algorithms for FTIO online predictor."""

from __future__ import annotations

import numpy as np
import math
from typing import List, Tuple, Optional, Dict, Any
from multiprocessing import Lock
from rich.console import Console
from ftio.prediction.helper import get_dominant
from ftio.freq.prediction import Prediction
from ftio.util.server_ftio import ftio


class ChangePointDetector:
    """ADWIN detector for I/O pattern changes with automatic window sizing."""
    
    def __init__(self, delta: float = 0.05, shared_resources=None, show_init: bool = True, verbose: bool = False):
        """Initialize ADWIN detector with confidence parameter delta (default: 0.05)."""
        self.delta = min(max(delta, 1e-12), 1 - 1e-12)
        self.shared_resources = shared_resources
        self.verbose = verbose
        
        if shared_resources and not shared_resources.adwin_initialized.value:
            if hasattr(shared_resources, 'adwin_lock'):
                with shared_resources.adwin_lock:
                    if not shared_resources.adwin_initialized.value:
                        shared_resources.adwin_frequencies[:] = []
                        shared_resources.adwin_timestamps[:] = []
                        shared_resources.adwin_total_samples.value = 0
                        shared_resources.adwin_change_count.value = 0
                        shared_resources.adwin_last_change_time.value = 0.0
                        shared_resources.adwin_initialized.value = True
            else:
                if not shared_resources.adwin_initialized.value:
                    shared_resources.adwin_frequencies[:] = []
                    shared_resources.adwin_timestamps[:] = []
                    shared_resources.adwin_total_samples.value = 0
                    shared_resources.adwin_change_count.value = 0
                    shared_resources.adwin_last_change_time.value = 0.0
                    shared_resources.adwin_initialized.value = True
        
        if shared_resources is None:
            self.frequencies: List[float] = []
            self.timestamps: List[float] = []
            self.total_samples = 0
            self.change_count = 0
            self.last_change_time: Optional[float] = None
        
        self.last_change_point: Optional[int] = None
        self.min_window_size = 2  
        self.console = Console()
        
        if show_init:
            self.console.print(f"[green][ADWIN] Initialized with δ={delta:.3f} "
                             f"({(1-delta)*100:.0f}% confidence) "
                             f"[Process-safe: {shared_resources is not None}][/]")
    
    def _get_frequencies(self):
        """Get frequencies list (shared or local)."""
        if self.shared_resources:
            return self.shared_resources.adwin_frequencies
        return self.frequencies
    
    def _get_timestamps(self):
        """Get timestamps list (shared or local).""" 
        if self.shared_resources:
            return self.shared_resources.adwin_timestamps
        return self.timestamps
    
    def _get_total_samples(self):
        """Get total samples count (shared or local)."""
        if self.shared_resources:
            return self.shared_resources.adwin_total_samples.value
        return self.total_samples
    
    def _set_total_samples(self, value):
        """Set total samples count (shared or local)."""
        if self.shared_resources:
            self.shared_resources.adwin_total_samples.value = value
        else:
            self.total_samples = value
    
    def _get_change_count(self):
        """Get change count (shared or local)."""
        if self.shared_resources:
            return self.shared_resources.adwin_change_count.value
        return self.change_count
    
    def _set_change_count(self, value):
        """Set change count (shared or local)."""
        if self.shared_resources:
            self.shared_resources.adwin_change_count.value = value
        else:
            self.change_count = value
    
    def _get_last_change_time(self):
        """Get last change time (shared or local)."""
        if self.shared_resources:
            return self.shared_resources.adwin_last_change_time.value if self.shared_resources.adwin_last_change_time.value > 0 else None
        return self.last_change_time
    
    def _set_last_change_time(self, value):
        """Set last change time (shared or local)."""
        if self.shared_resources:
            self.shared_resources.adwin_last_change_time.value = value if value is not None else 0.0
        else:
            self.last_change_time = value
            
    def _reset_window(self):
        """Reset ADWIN window when no frequency is detected."""
        frequencies = self._get_frequencies()
        timestamps = self._get_timestamps()
        
        if self.shared_resources:
            del frequencies[:]
            del timestamps[:]
            self._set_total_samples(0)
            self._set_last_change_time(None)
        else:
            self.frequencies.clear()
            self.timestamps.clear()
            self._set_total_samples(0)
            self._set_last_change_time(None)
        
        self.console.print("[dim yellow][ADWIN] Window cleared: No frequency data to analyze[/]")
        
    def add_prediction(self, prediction: Prediction, timestamp: float) -> Optional[Tuple[int, float]]:
        """
        Add a new prediction and check for change points using ADWIN.
        This method is process-safe and can be called concurrently.

        Args:
            prediction: FTIO prediction result
            timestamp: Timestamp of this prediction

        Returns:
            Tuple of (change_point_index, exact_change_point_timestamp) if detected, None otherwise
        """
        freq = get_dominant(prediction)

        if np.isnan(freq) or freq <= 0:
            self.console.print("[yellow][ADWIN] No frequency found - resetting window history[/]")
            self._reset_window()
            return None
        
        if self.shared_resources and hasattr(self.shared_resources, 'adwin_lock'):
            with self.shared_resources.adwin_lock:
                return self._add_prediction_synchronized(prediction, timestamp, freq)
        else:
            return self._add_prediction_local(prediction, timestamp, freq)
    
    def _add_prediction_synchronized(self, prediction: Prediction, timestamp: float, freq: float) -> Optional[Tuple[int, float]]:
        """Add prediction with synchronized access to shared state."""
        frequencies = self._get_frequencies()
        timestamps = self._get_timestamps()
        
        frequencies.append(freq)
        timestamps.append(timestamp)
        self._set_total_samples(self._get_total_samples() + 1)
        
        if len(frequencies) < self.min_window_size:
            return None
            
        change_point = self._detect_change()
        
        if change_point is not None:
            exact_change_timestamp = timestamps[change_point]
            
            self._process_change_point(change_point)
            self._set_change_count(self._get_change_count() + 1)
            
            return (change_point, exact_change_timestamp)
            
        return None
    
    def _add_prediction_local(self, prediction: Prediction, timestamp: float, freq: float) -> Optional[Tuple[int, float]]:
        """Add prediction using local state (non-multiprocessing mode)."""
        frequencies = self._get_frequencies()
        timestamps = self._get_timestamps()
        
        frequencies.append(freq)
        timestamps.append(timestamp)
        self._set_total_samples(self._get_total_samples() + 1)
        
        if len(frequencies) < self.min_window_size:
            return None
            
        change_point = self._detect_change()
        
        if change_point is not None:
            exact_change_timestamp = timestamps[change_point]
            
            self._process_change_point(change_point)
            self._set_change_count(self._get_change_count() + 1)
            
            return (change_point, exact_change_timestamp)
            
        return None
        
    def _detect_change(self) -> Optional[int]:
        """
        Pure ADWIN change detection algorithm.
        
        Implements the original ADWIN algorithm using only statistical hypothesis testing
        with Hoeffding bounds. This preserves the theoretical guarantees on false alarm rates.
        
        Returns:
            Index of change point if detected, None otherwise
        """
        frequencies = self._get_frequencies()
        timestamps = self._get_timestamps()
        n = len(frequencies)
        
        if n < 2 * self.min_window_size:
            return None
            
        for cut in range(self.min_window_size, n - self.min_window_size + 1):
            if self._test_cut_point(cut):
                self.console.print(f"[blue][ADWIN] Change detected at position {cut}/{n}, "
                                 f"time={timestamps[cut]:.3f}s[/]")
                return cut
                
        return None
        
    def _test_cut_point(self, cut: int) -> bool:
        """
        Test if a cut point indicates a significant change using ADWIN's statistical test.
        
        Args:
            cut: Index to split the window (left: [0, cut), right: [cut, n))
            
        Returns:
            True if change detected at this cut point
        """
        frequencies = self._get_frequencies()
        n = len(frequencies)
        
        left_data = frequencies[:cut]
        n0 = len(left_data)
        mean0 = np.mean(left_data)
        
        right_data = frequencies[cut:]
        n1 = len(right_data)
        mean1 = np.mean(right_data)
        
        if n0 <= 0 or n1 <= 0:
            return False
            
        n_harmonic = (n0 * n1) / (n0 + n1)
        
        try:
          
            confidence_term = math.log(2.0 / self.delta) / (2.0 * n_harmonic)
            threshold = math.sqrt(2.0 * confidence_term)

        except (ValueError, ZeroDivisionError):
            threshold = 0.05
        
        mean_diff = abs(mean1 - mean0)

        if self.verbose:
            self.console.print(f"[dim blue][ADWIN DEBUG] Cut={cut}:[/]")
            self.console.print(f"  [dim]• Left window: {n0} samples, mean={mean0:.3f}Hz[/]")
            self.console.print(f"  [dim]• Right window: {n1} samples, mean={mean1:.3f}Hz[/]")
            self.console.print(f"  [dim]• Mean difference: |{mean1:.3f} - {mean0:.3f}| = {mean_diff:.3f}[/]")
            self.console.print(f"  [dim]• Harmonic mean: {n_harmonic:.1f}[/]")
            self.console.print(f"  [dim]• Confidence term: log(2/{self.delta}) / (2×{n_harmonic:.1f}) = {confidence_term:.6f}[/]")
            self.console.print(f"  [dim]• Threshold: √(2×{confidence_term:.6f}) = {threshold:.3f}[/]")
            self.console.print(f"  [dim]• Test: {mean_diff:.3f} > {threshold:.3f} ? {'CHANGE!' if mean_diff > threshold else 'No change'}[/]")

        return mean_diff > threshold
        
    def _process_change_point(self, change_point: int):
        """
        Process detected change point by updating window (core ADWIN behavior).
        
        ADWIN drops data before the change point to keep only recent data,
        effectively adapting the window size automatically.
        
        Args:
            change_point: Index where change was detected
        """
        frequencies = self._get_frequencies()
        timestamps = self._get_timestamps()
        
        self.last_change_point = change_point
        change_time = timestamps[change_point]
        self._set_last_change_time(change_time)
        
        old_window_size = len(frequencies)
        old_freq = np.mean(frequencies[:change_point]) if change_point > 0 else 0
        
        if self.shared_resources:
            del frequencies[:change_point]
            del timestamps[:change_point]
            new_frequencies = frequencies
            new_timestamps = timestamps
        else:
            self.frequencies = frequencies[change_point:]
            self.timestamps = timestamps[change_point:]
            new_frequencies = self.frequencies
            new_timestamps = self.timestamps
        
        new_window_size = len(new_frequencies)
        new_freq = np.mean(new_frequencies) if new_frequencies else 0
        
        freq_change = abs(new_freq - old_freq) / old_freq * 100 if old_freq > 0 else 0
        time_span = new_timestamps[-1] - new_timestamps[0] if len(new_timestamps) > 1 else 0
        
        self.console.print(f"[green][ADWIN] Window adapted: "
                         f"{old_window_size} → {new_window_size} samples[/]")
        self.console.print(f"[green][ADWIN] Frequency shift: "
                         f"{old_freq:.3f} → {new_freq:.3f} Hz ({freq_change:.1f}%)[/]")
        self.console.print(f"[green][ADWIN] New window span: {time_span:.2f} seconds[/]")
        
    def get_adaptive_start_time(self, current_prediction: Prediction) -> float:
        """
        Calculate the adaptive start time based on ADWIN's current window.
        
        When a change point was detected, this returns the EXACT timestamp of the 
        most recent change point, allowing the analysis window to start precisely
        from the moment the I/O pattern changed.
        
        Args:
            current_prediction: Current prediction result
            
        Returns:
            Exact start time for analysis window (change point timestamp or fallback)
        """
        timestamps = self._get_timestamps()
        
        if len(timestamps) == 0:
            return current_prediction.t_start
        
        last_change_time = self._get_last_change_time()
        if last_change_time is not None:
            exact_change_start = last_change_time
            
            min_window = 0.5   
            max_lookback = 10.0  
            
            window_span = current_prediction.t_end - exact_change_start
            
            if window_span < min_window:
                adaptive_start = max(0, current_prediction.t_end - min_window)
                self.console.print(f"[yellow][ADWIN] Change point too recent, using min window: "
                                 f"{adaptive_start:.6f}s[/]")
            elif window_span > max_lookback:
                adaptive_start = max(0, current_prediction.t_end - max_lookback)
                self.console.print(f"[yellow][ADWIN] Change point too old, using max lookback: "
                                 f"{adaptive_start:.6f}s[/]")
            else:
                adaptive_start = exact_change_start
                self.console.print(f"[green][ADWIN] Using EXACT change point timestamp: "
                                 f"{adaptive_start:.6f}s (window span: {window_span:.3f}s)[/]")
                
            return adaptive_start
        
        window_start = timestamps[0]
        
        min_start = current_prediction.t_end - 10.0 
        max_start = current_prediction.t_end - 0.5   
        
        adaptive_start = max(min_start, min(window_start, max_start))
        
        return adaptive_start
        
    def get_window_stats(self) -> Dict[str, Any]:
        """Get current ADWIN window statistics for debugging and logging."""
        frequencies = self._get_frequencies()
        timestamps = self._get_timestamps()
        
        if not frequencies:
            return {
                "size": 0, "mean": 0.0, "std": 0.0, 
                "range": [0.0, 0.0], "time_span": 0.0,
                "total_samples": self._get_total_samples(),
                "change_count": self._get_change_count()
            }
            
        return {
            "size": len(frequencies),
            "mean": np.mean(frequencies),
            "std": np.std(frequencies),
            "range": [float(np.min(frequencies)), float(np.max(frequencies))],
            "time_span": float(timestamps[-1] - timestamps[0]) if len(timestamps) > 1 else 0.0,
            "total_samples": self._get_total_samples(),
            "change_count": self._get_change_count()
        }
        
    def should_adapt_window(self) -> bool:
        """Check if window adaptation should be triggered."""
        return self.last_change_point is not None
        
    def log_change_point(self, counter: int, old_freq: float, new_freq: float) -> str:
        """
        Generate log message for ADWIN change point detection.
        
        Args:
            counter: Prediction counter
            old_freq: Previous dominant frequency  
            new_freq: Current dominant frequency
            
        Returns:
            Formatted log message
        """
        last_change_time = self._get_last_change_time()
        if last_change_time is None:
            return ""
            
        freq_change_pct = abs(new_freq - old_freq) / old_freq * 100 if old_freq > 0 else 0
        stats = self.get_window_stats()
        
        log_msg = (
            f"[red bold][CHANGE_POINT] t_s={last_change_time:.3f} sec[/]\n"
            f"[purple][PREDICTOR] (#{counter}):[/][yellow] "
            f"ADWIN detected pattern change: {old_freq:.3f} → {new_freq:.3f} Hz "
            f"({freq_change_pct:.1f}% change)[/]\n"
            f"[purple][PREDICTOR] (#{counter}):[/][yellow] "
            f"Adaptive window: {stats['size']} samples, "
            f"span={stats['time_span']:.1f}s, "
            f"changes={stats['change_count']}/{stats['total_samples']}[/]\n"
            f"[dim blue]ADWIN ANALYSIS: Statistical significance detected using Hoeffding bounds[/]\n"
            f"[dim blue]Window split analysis found mean difference > confidence threshold[/]\n"
            f"[dim blue]Confidence level: {(1-self.delta)*100:.0f}% (δ={self.delta:.3f})[/]"
        )

        
        self.last_change_point = None
        
        return log_msg

    def get_change_point_time(self, shared_resources=None) -> Optional[float]:
        """
        Get the timestamp of the most recent change point.
        
        Args:
            shared_resources: Shared resources (kept for compatibility)
            
        Returns:
            Timestamp of the change point, or None if no change detected
        """
        return self._get_last_change_time()

def detect_pattern_change_adwin(shared_resources, current_prediction: Prediction,
                         detector: ChangePointDetector, counter: int) -> Tuple[bool, Optional[str], float]:
    """
    Main function to detect pattern changes using ADWIN and adapt window.

    Args:
        shared_resources: Shared resources containing prediction history
        current_prediction: Current prediction result
        detector: ADWIN detector instance
        counter: Current prediction counter

    Returns:
        Tuple of (change_detected, log_message, new_start_time)
    """
    change_point = detector.add_prediction(current_prediction, current_prediction.t_end)
    
    if change_point is not None:
        change_idx, change_time = change_point
        
        current_freq = get_dominant(current_prediction)
        
        old_freq = current_freq  
        frequencies = detector._get_frequencies()
        if len(frequencies) > 1:
            window_stats = detector.get_window_stats()
            old_freq = max(0.1, window_stats["mean"] * 0.9)  
        
        log_msg = detector.log_change_point(counter, old_freq, current_freq)
        
        new_start_time = detector.get_adaptive_start_time(current_prediction)
        
        try:
            from ftio.prediction.online_analysis import get_socket_logger
            logger = get_socket_logger()
            logger.send_log("change_point", "ADWIN Change Point Detected", {
                'exact_time': change_time,
                'old_freq': old_freq,
                'new_freq': current_freq,
                'adaptive_start': new_start_time,
                'counter': counter
            })
        except ImportError:
            pass
        
        return True, log_msg, new_start_time
    
    return False, None, current_prediction.t_start


class CUSUMDetector:
    """Adaptive-Variance CUSUM detector with variance-based threshold adaptation."""

    def __init__(self, window_size: int = 50, shared_resources=None, show_init: bool = True, verbose: bool = False):
        """Initialize AV-CUSUM detector with rolling window size (default: 50)."""
        self.window_size = window_size
        self.shared_resources = shared_resources
        self.show_init = show_init
        self.verbose = verbose

        self.sum_pos = 0.0  
        self.sum_neg = 0.0 
        self.reference = None  
        self.initialized = False

        self.adaptive_threshold = 0.0  
        self.adaptive_drift = 0.0  
        self.rolling_std = 0.0  
        self.frequency_buffer = [] 

        self.console = Console()
    
    def _update_adaptive_parameters(self, freq: float):
        """Calculate thresholds automatically from data standard deviation."""
        import numpy as np

        if self.shared_resources and hasattr(self.shared_resources, 'cusum_frequencies'):
            if hasattr(self.shared_resources, 'cusum_lock'):
                with self.shared_resources.cusum_lock:
                    all_freqs = list(self.shared_resources.cusum_frequencies)
                    recent_freqs = all_freqs[-self.window_size-1:-1] if len(all_freqs) > 1 else []
            else:
                all_freqs = list(self.shared_resources.cusum_frequencies)
                recent_freqs = all_freqs[-self.window_size-1:-1] if len(all_freqs) > 1 else []
        else:
            self.frequency_buffer.append(freq)
            if len(self.frequency_buffer) > self.window_size:
                self.frequency_buffer.pop(0)
            recent_freqs = self.frequency_buffer[:-1] if len(self.frequency_buffer) > 1 else []

        if self.verbose:
            self.console.print(f"[dim magenta][CUSUM DEBUG] Buffer for σ calculation (excluding current): {[f'{f:.3f}' for f in recent_freqs]} (len={len(recent_freqs)})[/]")

        if len(recent_freqs) >= 3:
            freqs = np.array(recent_freqs)
            self.rolling_std = np.std(freqs)

          
            std_factor = max(self.rolling_std, 0.01)

            self.adaptive_threshold = 2.0 * std_factor
            self.adaptive_drift = 0.5 * std_factor

            if self.verbose:
                self.console.print(f"[dim cyan][CUSUM] σ={self.rolling_std:.3f}, "
                                 f"h_t={self.adaptive_threshold:.3f} (2σ threshold), "
                                 f"k_t={self.adaptive_drift:.3f} (0.5σ drift)[/]")
    
    def _reset_cusum_state(self):
        """Reset CUSUM state when no frequency is detected."""
        self.sum_pos = 0.0
        self.sum_neg = 0.0
        self.reference = None
        self.initialized = False

        self.frequency_buffer.clear()
        self.rolling_std = 0.0
        self.adaptive_threshold = 0.0
        self.adaptive_drift = 0.0

        if self.shared_resources:
            if hasattr(self.shared_resources, 'cusum_lock'):
                with self.shared_resources.cusum_lock:
                    del self.shared_resources.cusum_frequencies[:]
                    del self.shared_resources.cusum_timestamps[:]
            else:
                del self.shared_resources.cusum_frequencies[:]
                del self.shared_resources.cusum_timestamps[:]

        self.console.print("[dim yellow][CUSUM] State cleared: Starting fresh when frequency resumes[/]")
    
    def add_frequency(self, freq: float, timestamp: float = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Add frequency observation and check for change points.
        
        Args:
            freq: Frequency value (NaN or <=0 means no frequency found)
            timestamp: Time of observation
            
        Returns:
            Tuple of (change_detected, change_info)
        """
        if np.isnan(freq) or freq <= 0:
            self.console.print("[yellow][AV-CUSUM] No frequency found - resetting algorithm state[/]")
            self._reset_cusum_state()
            return False, {}

        if self.shared_resources:
            if hasattr(self.shared_resources, 'cusum_lock'):
                with self.shared_resources.cusum_lock:
                    self.shared_resources.cusum_frequencies.append(freq)
                    self.shared_resources.cusum_timestamps.append(timestamp or 0.0)
            else:
                self.shared_resources.cusum_frequencies.append(freq)
                self.shared_resources.cusum_timestamps.append(timestamp or 0.0)
        
        self._update_adaptive_parameters(freq)
        
        if not self.initialized:
            min_init_samples = 3  
            if self.shared_resources and len(self.shared_resources.cusum_frequencies) >= min_init_samples:
                first_freqs = list(self.shared_resources.cusum_frequencies)[:min_init_samples]
                self.reference = np.mean(first_freqs)
                self.initialized = True
                if self.show_init:
                    self.console.print(f"[yellow][AV-CUSUM] Reference established: {self.reference:.3f} Hz "
                                     f"(from first {min_init_samples} observations: {[f'{f:.3f}' for f in first_freqs]})[/]")
            else:
                current_count = len(self.shared_resources.cusum_frequencies) if self.shared_resources else 0
                self.console.print(f"[dim yellow][AV-CUSUM] Collecting calibration data ({current_count}/{min_init_samples})[/]")
                return False, {}
        
        deviation = freq - self.reference

       
        new_sum_pos = max(0, self.sum_pos + deviation - self.adaptive_drift)
        new_sum_neg = max(0, self.sum_neg - deviation - self.adaptive_drift)

        self.sum_pos = new_sum_pos
        self.sum_neg = new_sum_neg

        if self.verbose:
            current_window_size = len(self.shared_resources.cusum_frequencies) if self.shared_resources else 0

            self.console.print(f"[dim yellow][AV-CUSUM DEBUG] Observation #{current_window_size}:[/]")
            self.console.print(f"  [dim]• Current freq: {freq:.3f} Hz[/]")
            self.console.print(f"  [dim]• Reference: {self.reference:.3f} Hz[/]")
            self.console.print(f"  [dim]• Deviation: {freq:.3f} - {self.reference:.3f} = {deviation:.3f}[/]")
            self.console.print(f"  [dim]• Adaptive drift: {self.adaptive_drift:.3f} (k_t = 0.5×σ, σ={self.rolling_std:.3f})[/]")
            self.console.print(f"  [dim]• Sum_pos before: {self.sum_pos:.3f}[/]")
            self.console.print(f"  [dim]• Sum_neg before: {self.sum_neg:.3f}[/]")
            self.console.print(f"  [dim]• Sum_pos calculation: max(0, {self.sum_pos:.3f} + {deviation:.3f} - {self.adaptive_drift:.3f}) = {new_sum_pos:.3f}[/]")
            self.console.print(f"  [dim]• Sum_neg calculation: max(0, {self.sum_neg:.3f} - {deviation:.3f} - {self.adaptive_drift:.3f}) = {new_sum_neg:.3f}[/]")
            self.console.print(f"  [dim]• Adaptive threshold: {self.adaptive_threshold:.3f} (h_t = 5.0×σ, σ={self.rolling_std:.3f})[/]")
            self.console.print(f"  [dim]• Upward change test: {self.sum_pos:.3f} > {self.adaptive_threshold:.3f} = {'UPWARD CHANGE!' if self.sum_pos > self.adaptive_threshold else 'No change'}[/]")
            self.console.print(f"  [dim]• Downward change test: {self.sum_neg:.3f} > {self.adaptive_threshold:.3f} = {'DOWNWARD CHANGE!' if self.sum_neg > self.adaptive_threshold else 'No change'}[/]")
        
        if self.shared_resources and hasattr(self.shared_resources, 'cusum_frequencies'):
            sample_count = len(self.shared_resources.cusum_frequencies)
        else:
            sample_count = len(self.frequency_buffer)

        if sample_count < 3 or self.adaptive_threshold <= 0:
            return False, {}

        upward_change = self.sum_pos > self.adaptive_threshold
        downward_change = self.sum_neg > self.adaptive_threshold
        change_detected = upward_change or downward_change

        change_info = {
            'timestamp': timestamp,
            'frequency': freq,
            'reference': self.reference,
            'sum_pos': self.sum_pos,
            'sum_neg': self.sum_neg,
            'threshold': self.adaptive_threshold,
            'rolling_std': self.rolling_std,
            'deviation': deviation,
            'change_type': 'increase' if upward_change else 'decrease' if downward_change else 'none'
        }

        if change_detected:
            change_type = change_info['change_type']
            change_percent = abs(deviation / self.reference * 100) if self.reference != 0 else 0

            self.console.print(f"[bold yellow][AV-CUSUM] CHANGE DETECTED! "
                             f"{self.reference:.3f}Hz → {freq:.3f}Hz "
                             f"({change_percent:.1f}% {change_type})[/]")
            self.console.print(f"[yellow][AV-CUSUM] Sum_pos={self.sum_pos:.2f}, Sum_neg={self.sum_neg:.2f}, "
                             f"Adaptive_Threshold={self.adaptive_threshold:.2f}[/]")
            self.console.print(f"[dim yellow]AV-CUSUM ANALYSIS: Cumulative sum exceeded adaptive threshold {self.adaptive_threshold:.2f}[/]")
            self.console.print(f"[dim yellow]Detection method: {'Positive sum (upward trend)' if upward_change else 'Negative sum (downward trend)'}[/]")
            self.console.print(f"[dim yellow]Adaptive drift: {self.adaptive_drift:.3f} (σ={self.rolling_std:.3f})[/]")

            old_reference = self.reference
            self.reference = freq 
            self.console.print(f"[cyan][CUSUM] Reference updated: {old_reference:.3f} → {self.reference:.3f} Hz "
                             f"({change_percent:.1f}% change)[/]")
            
            self.sum_pos = 0.0
            self.sum_neg = 0.0
            
            if self.shared_resources:
                if hasattr(self.shared_resources, 'cusum_lock'):
                    with self.shared_resources.cusum_lock:
                        old_window_size = len(self.shared_resources.cusum_frequencies)

                        current_freq_list = [freq]
                        current_timestamp_list = [timestamp or 0.0]

                        self.shared_resources.cusum_frequencies[:] = current_freq_list
                        self.shared_resources.cusum_timestamps[:] = current_timestamp_list

                        self.console.print(f"[green][CUSUM] CHANGE POINT ADAPTATION: Discarded {old_window_size-1} past samples, "
                                         f"starting fresh from current detection[/]")
                        self.console.print(f"[green][CUSUM] WINDOW RESET: {old_window_size} → {len(self.shared_resources.cusum_frequencies)} samples[/]")

                        self.shared_resources.cusum_change_count.value += 1
                else:
                    old_window_size = len(self.shared_resources.cusum_frequencies)
                    current_freq_list = [freq]
                    current_timestamp_list = [timestamp or 0.0]
                    self.shared_resources.cusum_frequencies[:] = current_freq_list
                    self.shared_resources.cusum_timestamps[:] = current_timestamp_list
                    self.console.print(f"[green][CUSUM] CHANGE POINT ADAPTATION: Discarded {old_window_size-1} past samples[/]")
                    self.shared_resources.cusum_change_count.value += 1
        
        return change_detected, change_info


def detect_pattern_change_cusum(
    shared_resources,
    current_prediction: Prediction,
    detector: CUSUMDetector,
    counter: int
) -> Tuple[bool, Optional[str], float]:
    """
    CUSUM-based change point detection with enhanced logging.

    Args:
        shared_resources: Shared state for multiprocessing
        current_prediction: Current frequency prediction
        detector: CUSUM detector instance
        counter: Prediction counter

    Returns:
        Tuple of (change_detected, log_message, adaptive_start_time)
    """

    current_freq = get_dominant(current_prediction)
    current_time = current_prediction.t_end

    if np.isnan(current_freq):
        detector._reset_cusum_state()
        return False, None, current_prediction.t_start
    
    change_detected, change_info = detector.add_frequency(current_freq, current_time)
    
    if not change_detected:
        return False, None, current_prediction.t_start
    
    change_type = change_info['change_type']
    reference = change_info['reference']
    threshold = change_info['threshold']
    sum_pos = change_info['sum_pos']
    sum_neg = change_info['sum_neg']
    
    magnitude = abs(current_freq - reference)
    percent_change = (magnitude / reference * 100) if reference > 0 else 0
    
    log_msg = (
        f"[bold red][CUSUM] CHANGE DETECTED! "
        f"{reference:.1f}Hz → {current_freq:.1f}Hz "
        f"(Δ={magnitude:.1f}Hz, {percent_change:.1f}% {change_type}) "
        f"at sample {len(shared_resources.cusum_frequencies)}, time={current_time:.3f}s[/]\n"
        f"[red][CUSUM] CUSUM stats: sum_pos={sum_pos:.2f}, sum_neg={sum_neg:.2f}, "
        f"threshold={threshold}[/]\n"
        f"[red][CUSUM] Cumulative sum exceeded threshold -> Starting fresh analysis[/]"
    )
    
    if percent_change > 100:  
        min_window_size = 0.5

    elif percent_change > 50:   
        min_window_size = 1.0
    else: 
        min_window_size = 2.0
    
    new_start_time = max(0, current_time - min_window_size)
    
    try:
        from ftio.prediction.online_analysis import get_socket_logger
        logger = get_socket_logger()
        logger.send_log("change_point", "CUSUM Change Point Detected", {
            'algorithm': 'CUSUM',
            'detection_time': current_time,
            'change_type': change_type,
            'frequency': current_freq,
            'reference': reference,
            'magnitude': magnitude,
            'percent_change': percent_change,
            'threshold': threshold,
            'counter': counter
        })
    except ImportError:
        pass
    
    return True, log_msg, new_start_time


class SelfTuningPageHinkleyDetector:
    """Self-Tuning Page-Hinkley detector with adaptive running mean baseline."""

    def __init__(self, window_size: int = 10, shared_resources=None, show_init: bool = True, verbose: bool = False):
        """Initialize STPH detector with rolling window size (default: 10)."""
        self.window_size = window_size
        self.shared_resources = shared_resources
        self.show_init = show_init
        self.verbose = verbose
        self.console = Console()

        self.adaptive_threshold = 0.0 
        self.adaptive_delta = 0.0  
        self.rolling_std = 0.0 
        self.frequency_buffer = [] 

        self.cumulative_sum_pos = 0.0
        self.cumulative_sum_neg = 0.0
        self.reference_mean = 0.0
        self.sum_of_samples = 0.0
        self.sample_count = 0

        if shared_resources and hasattr(shared_resources, 'pagehinkley_state'):
            try:
                state = dict(shared_resources.pagehinkley_state)
                if state.get('initialized', False):
                    self.cumulative_sum_pos = state.get('cumulative_sum_pos', 0.0)
                    self.cumulative_sum_neg = state.get('cumulative_sum_neg', 0.0)
                    self.reference_mean = state.get('reference_mean', 0.0)
                    self.sum_of_samples = state.get('sum_of_samples', 0.0)
                    self.sample_count = state.get('sample_count', 0)
                    if self.verbose:
                        self.console.print(f"[green][PH DEBUG] Restored state: cusum_pos={self.cumulative_sum_pos:.3f}, cusum_neg={self.cumulative_sum_neg:.3f}, ref_mean={self.reference_mean:.3f}[/]")
                else:
                    self._initialize_fresh_state()
            except Exception as e:
                if self.verbose:
                    self.console.print(f"[red][PH DEBUG] State restore failed: {e}[/]")
                self._initialize_fresh_state()
        else:
            self._initialize_fresh_state()
        
    def _update_adaptive_parameters(self, freq: float):
        """Calculate thresholds automatically from data standard deviation."""
        import numpy as np

        
        if self.shared_resources and hasattr(self.shared_resources, 'pagehinkley_frequencies'):
            if hasattr(self.shared_resources, 'ph_lock'):
                with self.shared_resources.ph_lock:
                    all_freqs = list(self.shared_resources.pagehinkley_frequencies)
                    recent_freqs = all_freqs[-self.window_size-1:-1] if len(all_freqs) > 1 else []
            else:
                all_freqs = list(self.shared_resources.pagehinkley_frequencies)
                recent_freqs = all_freqs[-self.window_size-1:-1] if len(all_freqs) > 1 else []
        else:
            self.frequency_buffer.append(freq)
            if len(self.frequency_buffer) > self.window_size:
                self.frequency_buffer.pop(0)
            recent_freqs = self.frequency_buffer[:-1] if len(self.frequency_buffer) > 1 else []

        if len(recent_freqs) >= 3:
            freqs = np.array(recent_freqs)
            self.rolling_std = np.std(freqs)

           
            std_factor = max(self.rolling_std, 0.01)

            self.adaptive_threshold = 2.0 * std_factor
            self.adaptive_delta = 0.5 * std_factor

            if self.verbose:
                self.console.print(f"[dim magenta][Page-Hinkley] σ={self.rolling_std:.3f}, "
                                 f"λ_t={self.adaptive_threshold:.3f} (2σ threshold), "
                                 f"δ_t={self.adaptive_delta:.3f} (0.5σ delta)[/]")
    
    def _reset_pagehinkley_state(self):
        """Reset Page-Hinkley state when no frequency is detected."""
        self.cumulative_sum_pos = 0.0
        self.cumulative_sum_neg = 0.0
        self.reference_mean = 0.0
        self.sum_of_samples = 0.0
        self.sample_count = 0

        self.frequency_buffer.clear()
        self.rolling_std = 0.0
        self.adaptive_threshold = 0.0
        self.adaptive_delta = 0.0
        
        if self.shared_resources:
            if hasattr(self.shared_resources, 'pagehinkley_lock'):
                with self.shared_resources.pagehinkley_lock:
                    if hasattr(self.shared_resources, 'pagehinkley_frequencies'):
                        del self.shared_resources.pagehinkley_frequencies[:]
                    if hasattr(self.shared_resources, 'pagehinkley_timestamps'):
                        del self.shared_resources.pagehinkley_timestamps[:]
                    if hasattr(self.shared_resources, 'pagehinkley_state'):
                        self.shared_resources.pagehinkley_state.clear()
            else:
                if hasattr(self.shared_resources, 'pagehinkley_frequencies'):
                    del self.shared_resources.pagehinkley_frequencies[:]
                if hasattr(self.shared_resources, 'pagehinkley_timestamps'):
                    del self.shared_resources.pagehinkley_timestamps[:]
                if hasattr(self.shared_resources, 'pagehinkley_state'):
                    self.shared_resources.pagehinkley_state.clear()
        
        self.console.print("[dim yellow][STPH] State cleared: Starting fresh when frequency resumes[/]")
    
    def _initialize_fresh_state(self):
        """Initialize fresh Page-Hinkley state."""
        self.cumulative_sum_pos = 0.0
        self.cumulative_sum_neg = 0.0
        self.reference_mean = 0.0
        self.sum_of_samples = 0.0
        self.sample_count = 0
        
    def reset(self, current_freq: float = None):
        """
        Reset Page-Hinckley internal state for fresh start after change point detection.

        Args:
            current_freq: Optional current frequency to use as new reference.
                         If None, state is completely cleared for reinitialization.
        """
        self.cumulative_sum_pos = 0.0
        self.cumulative_sum_neg = 0.0

        if current_freq is not None:
            self.reference_mean = current_freq
            self.sum_of_samples = current_freq
            self.sample_count = 1
        else:
            self.reference_mean = 0.0
            self.sum_of_samples = 0.0
            self.sample_count = 0

        if self.shared_resources:
            if hasattr(self.shared_resources, 'pagehinkley_lock'):
                with self.shared_resources.pagehinkley_lock:
                    if hasattr(self.shared_resources, 'pagehinkley_state'):
                        self.shared_resources.pagehinkley_state.update({
                            'cumulative_sum_pos': 0.0,
                            'cumulative_sum_neg': 0.0,
                            'reference_mean': self.reference_mean,
                            'sum_of_samples': self.sum_of_samples,
                            'sample_count': self.sample_count,
                            'initialized': True
                        })

                 
                    if hasattr(self.shared_resources, 'pagehinkley_frequencies'):
                        if current_freq is not None:
                            self.shared_resources.pagehinkley_frequencies[:] = [current_freq]
                        else:
                            del self.shared_resources.pagehinkley_frequencies[:]
                    if hasattr(self.shared_resources, 'pagehinkley_timestamps'):
                        if current_freq is not None:
                            last_timestamp = self.shared_resources.pagehinkley_timestamps[-1] if len(self.shared_resources.pagehinkley_timestamps) > 0 else 0.0
                            self.shared_resources.pagehinkley_timestamps[:] = [last_timestamp]
                        else:
                            del self.shared_resources.pagehinkley_timestamps[:]
            else:
                if hasattr(self.shared_resources, 'pagehinkley_state'):
                    self.shared_resources.pagehinkley_state.update({
                        'cumulative_sum_pos': 0.0,
                        'cumulative_sum_neg': 0.0,
                        'reference_mean': self.reference_mean,
                        'sum_of_samples': self.sum_of_samples,
                        'sample_count': self.sample_count,
                        'initialized': True
                    })
                if hasattr(self.shared_resources, 'pagehinkley_frequencies'):
                    if current_freq is not None:
                        self.shared_resources.pagehinkley_frequencies[:] = [current_freq]
                    else:
                        del self.shared_resources.pagehinkley_frequencies[:]
                if hasattr(self.shared_resources, 'pagehinkley_timestamps'):
                    if current_freq is not None:
                        last_timestamp = self.shared_resources.pagehinkley_timestamps[-1] if len(self.shared_resources.pagehinkley_timestamps) > 0 else 0.0
                        self.shared_resources.pagehinkley_timestamps[:] = [last_timestamp]
                    else:
                        del self.shared_resources.pagehinkley_timestamps[:]

        if current_freq is not None:
            self.console.print(f"[cyan][PH] Internal state reset with new reference: {current_freq:.3f} Hz[/]")
        else:
            self.console.print(f"[cyan][PH] Internal state reset: Page-Hinkley parameters reinitialized[/]")
        
    def add_frequency(self, freq: float, timestamp: float = None) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Add frequency observation and update Page-Hinkley statistics.
        
        Args:
            freq: Frequency observation (NaN or <=0 means no frequency found)
            timestamp: Time of observation (optional)
            
        Returns:
            Tuple of (change_detected, triggering_sum, metadata)
        """
        if np.isnan(freq) or freq <= 0:
            self.console.print("[yellow][STPH] No frequency found - resetting Page-Hinkley state[/]")
            self._reset_pagehinkley_state()
            return False, 0.0, {}
        
        self._update_adaptive_parameters(freq)

        if self.shared_resources:
            if hasattr(self.shared_resources, 'pagehinkley_lock'):
                with self.shared_resources.pagehinkley_lock:
                    self.shared_resources.pagehinkley_frequencies.append(freq)
                    self.shared_resources.pagehinkley_timestamps.append(timestamp or 0.0)
            else:
                self.shared_resources.pagehinkley_frequencies.append(freq)
                self.shared_resources.pagehinkley_timestamps.append(timestamp or 0.0)
            
        if self.sample_count == 0:
            self.sample_count = 1
            self.reference_mean = freq
            self.sum_of_samples = freq
            if self.show_init:
                self.console.print(f"[yellow][STPH] Reference mean initialized: {self.reference_mean:.3f} Hz[/]")
        else:
            self.sample_count += 1
            self.sum_of_samples += freq
            self.reference_mean = self.sum_of_samples / self.sample_count
        
        pos_difference = freq - self.reference_mean - self.adaptive_delta
        old_cumsum_pos = self.cumulative_sum_pos
        self.cumulative_sum_pos = max(0, self.cumulative_sum_pos + pos_difference)
        
        neg_difference = self.reference_mean - freq - self.adaptive_delta
        old_cumsum_neg = self.cumulative_sum_neg
        self.cumulative_sum_neg = max(0, self.cumulative_sum_neg + neg_difference)

        if self.verbose:
            self.console.print(f"[dim magenta][STPH DEBUG] Sample #{self.sample_count}:[/]")
            self.console.print(f"  [dim]• Current freq: {freq:.3f} Hz[/]")
            self.console.print(f"  [dim]• Reference mean: {self.reference_mean:.3f} Hz[/]")
            self.console.print(f"  [dim]• Adaptive delta: {self.adaptive_delta:.3f}[/]")
            self.console.print(f"  [dim]• Positive difference: {freq:.3f} - {self.reference_mean:.3f} - {self.adaptive_delta:.3f} = {pos_difference:.3f}[/]")
            self.console.print(f"  [dim]• Sum_pos = max(0, {old_cumsum_pos:.3f} + {pos_difference:.3f}) = {self.cumulative_sum_pos:.3f}[/]")
            self.console.print(f"  [dim]• Negative difference: {self.reference_mean:.3f} - {freq:.3f} - {self.adaptive_delta:.3f} = {neg_difference:.3f}[/]")
            self.console.print(f"  [dim]• Sum_neg = max(0, {old_cumsum_neg:.3f} + {neg_difference:.3f}) = {self.cumulative_sum_neg:.3f}[/]")
            self.console.print(f"  [dim]• Adaptive threshold: {self.adaptive_threshold:.3f}[/]")
            self.console.print(f"  [dim]• Upward change test: {self.cumulative_sum_pos:.3f} > {self.adaptive_threshold:.3f} = {'UPWARD CHANGE!' if self.cumulative_sum_pos > self.adaptive_threshold else 'No change'}[/]")
            self.console.print(f"  [dim]• Downward change test: {self.cumulative_sum_neg:.3f} > {self.adaptive_threshold:.3f} = {'DOWNWARD CHANGE!' if self.cumulative_sum_neg > self.adaptive_threshold else 'No change'}[/]")
        
        if self.shared_resources and hasattr(self.shared_resources, 'pagehinkley_state'):
            if hasattr(self.shared_resources, 'pagehinkley_lock'):
                with self.shared_resources.pagehinkley_lock:
                    self.shared_resources.pagehinkley_state.update({
                        'cumulative_sum_pos': self.cumulative_sum_pos,
                        'cumulative_sum_neg': self.cumulative_sum_neg,
                        'reference_mean': self.reference_mean,
                        'sum_of_samples': self.sum_of_samples,
                        'sample_count': self.sample_count,
                        'initialized': True
                    })
            else:
                self.shared_resources.pagehinkley_state.update({
                    'cumulative_sum_pos': self.cumulative_sum_pos,
                    'cumulative_sum_neg': self.cumulative_sum_neg,
                    'reference_mean': self.reference_mean,
                    'sum_of_samples': self.sum_of_samples,
                    'sample_count': self.sample_count,
                    'initialized': True
                })
            
        if self.shared_resources and hasattr(self.shared_resources, 'pagehinkley_frequencies'):
            sample_count = len(self.shared_resources.pagehinkley_frequencies)
        else:
            sample_count = len(self.frequency_buffer)

        if sample_count < 3 or self.adaptive_threshold <= 0:
            return False, 0.0, {}

        upward_change = self.cumulative_sum_pos > self.adaptive_threshold
        downward_change = self.cumulative_sum_neg > self.adaptive_threshold
        change_detected = upward_change or downward_change

        if upward_change:
            change_type = "increase"
            triggering_sum = self.cumulative_sum_pos
        elif downward_change:
            change_type = "decrease"
            triggering_sum = self.cumulative_sum_neg
        else:
            change_type = "none"
            triggering_sum = max(self.cumulative_sum_pos, self.cumulative_sum_neg)

        if change_detected:
            magnitude = abs(freq - self.reference_mean)
            percent_change = (magnitude / self.reference_mean * 100) if self.reference_mean > 0 else 0

            self.console.print(f"[bold magenta][STPH] CHANGE DETECTED! "
                             f"{self.reference_mean:.3f}Hz → {freq:.3f}Hz "
                             f"({percent_change:.1f}% {change_type})[/]")
            self.console.print(f"[magenta][STPH] Sum_pos={self.cumulative_sum_pos:.2f}, Sum_neg={self.cumulative_sum_neg:.2f}, "
                             f"Adaptive_Threshold={self.adaptive_threshold:.3f} (σ={self.rolling_std:.3f})[/]")
            self.console.print(f"[dim magenta]STPH ANALYSIS: Cumulative sum exceeded adaptive threshold {self.adaptive_threshold:.2f}[/]")
            self.console.print(f"[dim magenta]Detection method: {'Positive sum (upward trend)' if upward_change else 'Negative sum (downward trend)'}[/]")
            self.console.print(f"[dim magenta]Adaptive minimum detectable change: {self.adaptive_delta:.3f}[/]")
            
            if self.shared_resources and hasattr(self.shared_resources, 'pagehinkley_change_count'):
                if hasattr(self.shared_resources, 'pagehinkley_lock'):
                    with self.shared_resources.pagehinkley_lock:
                        self.shared_resources.pagehinkley_change_count.value += 1
                else:
                    self.shared_resources.pagehinkley_change_count.value += 1
                
        current_window_size = len(self.shared_resources.pagehinkley_frequencies) if self.shared_resources else self.sample_count
        
        metadata = {
            'cumulative_sum_pos': self.cumulative_sum_pos,
            'cumulative_sum_neg': self.cumulative_sum_neg,
            'triggering_sum': triggering_sum,
            'change_type': change_type,
            'reference_mean': self.reference_mean,
            'frequency': freq,
            'window_size': current_window_size,
            'threshold': self.adaptive_threshold,
            'adaptive_delta': self.adaptive_delta,
            'rolling_std': self.rolling_std
        }
        
        return change_detected, triggering_sum, metadata


def detect_pattern_change_pagehinkley(
    shared_resources,
    current_prediction: Prediction,
    detector: SelfTuningPageHinkleyDetector,
    counter: int
) -> Tuple[bool, Optional[str], float]:
    """
    Page-Hinkley-based change point detection with enhanced logging.

    Args:
        shared_resources: Shared state for multiprocessing
        current_prediction: Current frequency prediction
        detector: Page-Hinkley detector instance
        counter: Prediction counter

    Returns:
        Tuple of (change_detected, log_message, adaptive_start_time)
    """
    import numpy as np

    current_freq = get_dominant(current_prediction)
    current_time = current_prediction.t_end

    if current_freq is None or np.isnan(current_freq):
        detector._reset_pagehinkley_state()
        return False, None, current_prediction.t_start
    
    change_detected, triggering_sum, metadata = detector.add_frequency(current_freq, current_time)
    
    if change_detected:
        detector.reset(current_freq=current_freq)
        
        change_type = metadata.get("change_type", "unknown")
        frequency = metadata.get("frequency", current_freq)
        reference_mean = metadata.get("reference_mean", 0.0)
        window_size = metadata.get("window_size", 0)
        
        magnitude = abs(frequency - reference_mean)
        percent_change = (magnitude / reference_mean * 100) if reference_mean > 0 else 0
        
        direction_arrow = "increasing" if change_type == "increase" else "decreasing" if change_type == "decrease" else "stable"
        log_message = (
            f"[bold red][Page-Hinkley] PAGE-HINKLEY CHANGE DETECTED! {direction_arrow} "
            f"{reference_mean:.1f}Hz → {frequency:.1f}Hz "
            f"(Δ={magnitude:.1f}Hz, {percent_change:.1f}% {change_type}) "
            f"at sample {window_size}, time={current_time:.3f}s[/]\n"
            f"[red][Page-Hinkley] Page-Hinkley stats: sum_pos={metadata.get('cumulative_sum_pos', 0):.2f}, "
            f"sum_neg={metadata.get('cumulative_sum_neg', 0):.2f}, threshold={detector.adaptive_threshold:.3f}[/]\n"
            f"[red][Page-Hinkley] Cumulative sum exceeded threshold -> Starting fresh analysis[/]"
        )
        
        adaptive_start_time = current_time
        if hasattr(shared_resources, 'pagehinkley_last_change_time'):
            shared_resources.pagehinkley_last_change_time.value = current_time
        
        logger = shared_resources.logger if hasattr(shared_resources, 'logger') else None
        if logger:
            logger.send_log("change_point", "Page-Hinkley Change Point Detected", {
                'algorithm': 'PageHinkley',
                'frequency': frequency,
                'reference_mean': reference_mean,
                'magnitude': magnitude,
                'percent_change': percent_change,
                'triggering_sum': triggering_sum,
                'change_type': change_type,
                'position': window_size,
                'timestamp': current_time,
                'threshold': detector.adaptive_threshold,
                'delta': detector.adaptive_delta,
                'prediction_counter': counter
            })
        
        return True, log_message, adaptive_start_time

    return False, None, current_prediction.t_start
