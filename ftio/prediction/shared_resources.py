from multiprocessing import Manager


class SharedResources:
    def __init__(self):
        """Initialize the manager and shared resources."""
        self.manager = Manager()
        self._init_shared_resources()

    def _init_shared_resources(self):
        """Initialize the shared resources."""

        self.queue = self.manager.Queue()


        self.data = self.manager.list()

        self.aggregated_bytes = self.manager.Value("d", 0.0)

        self.hits = self.manager.Value("d", 0.0)

        self.start_time = self.manager.Value("d", 0.0)

        self.count = self.manager.Value("i", 0)

        self.b_app = self.manager.list()
        self.t_app = self.manager.list()

        self.sync_trigger = self.manager.Queue()

        self.t_flush = self.manager.list()
        

        self.adwin_frequencies = self.manager.list()
        self.adwin_timestamps = self.manager.list()
        self.adwin_total_samples = self.manager.Value("i", 0)
        self.adwin_change_count = self.manager.Value("i", 0)
        self.adwin_last_change_time = self.manager.Value("d", 0.0)
        self.adwin_initialized = self.manager.Value("b", False)
        

        self.adwin_lock = self.manager.Lock()
        

        self.cusum_frequencies = self.manager.list()
        self.cusum_timestamps = self.manager.list()
        self.cusum_change_count = self.manager.Value("i", 0)
        self.cusum_last_change_time = self.manager.Value("d", 0.0)
        self.cusum_initialized = self.manager.Value("b", False)
        

        self.cusum_lock = self.manager.Lock()
        

        self.pagehinkley_frequencies = self.manager.list()
        self.pagehinkley_timestamps = self.manager.list()
        self.pagehinkley_change_count = self.manager.Value("i", 0)
        self.pagehinkley_last_change_time = self.manager.Value("d", 0.0)
        self.pagehinkley_initialized = self.manager.Value("b", False)


        self.pagehinkley_state = self.manager.dict({
            'cumulative_sum_pos': 0.0,
            'cumulative_sum_neg': 0.0,
            'reference_mean': 0.0,
            'sum_of_samples': 0.0,
            'sample_count': 0,
            'initialized': False
        })
        

        self.pagehinkley_lock = self.manager.Lock()
        

        self.detector_frequencies = self.manager.list()
        self.detector_timestamps = self.manager.list()
        self.detector_is_calibrated = self.manager.Value("b", False)
        self.detector_reference_freq = self.manager.Value("d", 0.0)
        self.detector_sensitivity = self.manager.Value("d", 0.0)
        self.detector_threshold_factor = self.manager.Value("d", 0.0)
        

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
