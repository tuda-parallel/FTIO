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
        # saves when the data is received from gkfs
        self.t_flush = self.manager.list()

        # Change point detection shared state (used by all algorithms: ADWIN, CUSUM, Page-Hinkley)
        self.detector_frequencies = self.manager.list()
        self.detector_timestamps = self.manager.list()
        self.detector_total_samples = self.manager.Value("i", 0)
        self.detector_change_count = self.manager.Value("i", 0)
        self.detector_last_change_time = self.manager.Value("d", 0.0)
        self.detector_initialized = self.manager.Value("b", False)
        self.detector_lock = self.manager.Lock()
        # Algorithm-specific state (e.g., Page-Hinkley cumulative sums)
        self.detector_state = self.manager.dict()

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
