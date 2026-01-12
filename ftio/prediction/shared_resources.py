from multiprocessing import Manager


class SharedResources:
    def __init__(self):
        """Initialize the manager and shared resources."""
        self.manager = Manager()
        self._init_shared_resources()

    def _init_shared_resources(self):
        """Initialize the shared resources."""
        # Queue for FTIO data
        self.queue = self.manager.Queue()
        # list of dicts with all predictions so far
        # Data for prediction : [key][type][mean][std][number_of_values_used_in_mean_and_std]
        self.data = self.manager.list()
        # Total bytes transferred so far
        self.aggregated_bytes = self.manager.Value("d", 0.0)
        # Hits indicating how often a dominant frequency was found
        self.hits = self.manager.Value("d", 0.0)
        # Start time window for ftio
        self.start_time = self.manager.Value("d", 0.0)
        # Number of prediction
        self.count = self.manager.Value("i", 0)
        # Bandwidth and time appended between predictions
        self.b_app = self.manager.list()
        self.t_app = self.manager.list()
        # For triggering cargo
        self.sync_trigger = self.manager.Queue()
        # saves when the dada ti received from gkfs
        self.t_flush = self.manager.list()
        
        # ADWIN shared state for multiprocessing
        self.adwin_frequencies = self.manager.list()
        self.adwin_timestamps = self.manager.list()
        self.adwin_total_samples = self.manager.Value("i", 0)
        self.adwin_change_count = self.manager.Value("i", 0)
        self.adwin_last_change_time = self.manager.Value("d", 0.0)
        self.adwin_initialized = self.manager.Value("b", False)
        
        # Lock for ADWIN operations to ensure process safety
        self.adwin_lock = self.manager.Lock()
        
        # CUSUM shared state for multiprocessing (same pattern as ADWIN)
        self.cusum_frequencies = self.manager.list()
        self.cusum_timestamps = self.manager.list()
        self.cusum_change_count = self.manager.Value("i", 0)
        self.cusum_last_change_time = self.manager.Value("d", 0.0)
        self.cusum_initialized = self.manager.Value("b", False)
        
        # Lock for CUSUM operations to ensure process safety
        self.cusum_lock = self.manager.Lock()
        
        # Page-Hinkley shared state for multiprocessing (same pattern as ADWIN/CUSUM)
        self.pagehinkley_frequencies = self.manager.list()
        self.pagehinkley_timestamps = self.manager.list()
        self.pagehinkley_change_count = self.manager.Value("i", 0)
        self.pagehinkley_last_change_time = self.manager.Value("d", 0.0)
        self.pagehinkley_initialized = self.manager.Value("b", False)
        # Persistent Page-Hinkley internal state across processes
        # Stores actual state fields used by SelfTuningPageHinkleyDetector
        self.pagehinkley_state = self.manager.dict({
            'cumulative_sum_pos': 0.0,
            'cumulative_sum_neg': 0.0,
            'reference_mean': 0.0,
            'sum_of_samples': 0.0,
            'sample_count': 0,
            'initialized': False
        })
        
        # Lock for Page-Hinkley operations to ensure process safety
        self.pagehinkley_lock = self.manager.Lock()
        
        # Legacy shared state for change point detection (kept for compatibility)
        self.detector_frequencies = self.manager.list()
        self.detector_timestamps = self.manager.list()
        self.detector_is_calibrated = self.manager.Value("b", False)
        self.detector_reference_freq = self.manager.Value("d", 0.0)
        self.detector_sensitivity = self.manager.Value("d", 0.0)
        self.detector_threshold_factor = self.manager.Value("d", 0.0)
        
        # Detector initialization flags to prevent repeated initialization messages
        self.adwin_initialized = self.manager.Value("b", False)
        self.cusum_initialized = self.manager.Value("b", False)
        self.ph_initialized = self.manager.Value("b", False)

    def restart(self):
        """Restart the manager and reinitialize shared resources."""
        print("Shutting down existing Manager...")
        self.manager.shutdown()

        print("Starting new Manager...")
        self.manager = Manager()
        self._init_shared_resources()

    def shutdown(self):
        """Shutdown the manager."""
        print("Shutting down Manager...")
        self.manager.shutdown()
