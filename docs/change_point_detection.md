# Change Point Detection for Online I/O Pattern Analysis

This document describes the adaptive change point detection feature for FTIO's online predictor, which enables automatic
detection of I/O pattern changes during streaming analysis.

## Overview

Change point detection allows FTIO to automatically detect when the I/O pattern changes during online prediction. When a
change is detected, the analysis window is adapted to focus on the new pattern, improving prediction accuracy.

Three algorithms are available:

- **ADWIN** (Adaptive Windowing) - Default
- **CUSUM** (Cumulative Sum)
- **Page-Hinkley** (Sequential change detection)

## Usage

### Command Line

There are two configuration modes:

**Pure change point detection**:

```bash
# Only change point detection, no hit-based optimization
predictor X.jsonl -e no -f 100 --window_adaptation adwin
predictor X.jsonl -e no -f 100 --window_adaptation cusum
predictor X.jsonl -e no -f 100 --window_adaptation ph
```

**Hybrid mode**:

```bash
# Change point detection + hit-based optimization
predictor X.jsonl -e no -f 100 -w frequency_hits --window_adaptation adwin
predictor X.jsonl -e no -f 100 -w frequency_hits --window_adaptation cusum
predictor X.jsonl -e no -f 100 -w frequency_hits --window_adaptation ph
```

### Configuration Modes Explained

| Mode   | Flags                                          |
|--------|------------------------------------------------|
| Pure   | `--window_adaptation <algo>`                   |
| Hybrid | `-w frequency_hits --window_adaptation <algo>` |

In **hybrid mode**, the two mechanisms are complementary:

- **Change point detection** handles pattern transitions (primary mechanism)
- **Hit-based** optimizes stable periods by shrinking the window (secondary optimization)

Hit-based only activates when change point detection reports no change. They do not interfere with each other.

## Algorithms

### ADWIN (Adaptive Windowing)

ADWIN uses Hoeffding bounds to detect statistically significant changes in the frequency distribution.

**How it works:**

1. Maintains a sliding window of frequency observations
2. Tests all possible cut points in the window
3. Uses Hoeffding inequality to determine if the means differ significantly
4. When change detected, discards old data and adapts window

**Parameters:**

- `delta` (default: 0.05): Confidence parameter. Lower values = higher confidence required for detection

### AV-CUSUM (Adaptive-Variance Cumulative Sum)

CUSUM tracks cumulative deviations from a reference value, with adaptive thresholds based on data variance.

**How it works:**

1. Establishes reference frequency from initial observations
2. Calculates positive and negative cumulative sums: `S+ = max(0, S+ + x - μ - k)` and `S- = max(0, S- - x + μ - k)`
3. Detects change when cumulative sum exceeds adaptive threshold (2σ)
4. Drift parameter (k = 0.5σ) prevents small fluctuations from accumulating

**Parameters:**

- `window_size` (default: 50): Size of rolling window for variance calculation

### STPH (Self-Tuning Page-Hinkley)

Page-Hinkley uses a running mean as reference and detects when observations deviate significantly.

**How it works:**

1. Maintains running mean as reference
2. Tracks cumulative positive and negative differences from reference
3. Uses adaptive threshold and delta based on rolling standard deviation
4. Detects change when cumulative difference exceeds threshold

**Parameters:**

- `window_size` (default: 10): Size of rolling window for variance calculation

## Window Adaptation

When a change point is detected:

1. **Exact timestamp** of the change is recorded
2. **Analysis window** is adapted to start from the change point
3. **Safety bounds** ensure minimum window size (0.5-1.0 seconds)
4. **Maximum lookback** limits window to prevent using stale data (10 seconds)

```
Before change detection:
|-------- old pattern --------|-- new pattern --|
                              ^ change point

After adaptation:
                              |-- new pattern --|
                              ^ analysis starts here
```

## GUI Dashboard

A real-time visualization dashboard is available for monitoring predictions and change points.

### Starting the Dashboard

```bash
# Install GUI dependencies (if not already installed)
pip install -e .[gui]

# 1. Start the GUI dashboard first
ftio-gui

# 2. Then run predictor with --gui flag to forward data to the dashboard
# Pure mode:
predictor X.jsonl -e no -f 100 --window_adaptation adwin --gui
# Or hybrid mode:
predictor X.jsonl -e no -f 100 -w frequency_hits --window_adaptation adwin --gui
```

The dashboard runs on `http://localhost:8050` and displays:

- Frequency timeline with change point markers
- Continuous cosine wave visualization
- Statistics (total predictions, changes detected, current frequency)

### Dashboard Features

- **Auto-updating**: Refreshes automatically as new predictions arrive
- **Change point markers**: Red vertical lines indicate detected changes
- **Frequency annotations**: Shows old → new frequency at each change
- **Gap visualization**: Displays periods with no detected frequency
- **Auto-connect**: The predictor automatically connects to the GUI when `--gui` flag is used

### Algorithm Selection

Algorithm is selected via the `--window_adaptation` flag:

| Flag Value | Algorithm    | Description                                  |
|------------|--------------|----------------------------------------------|
| `adwin`    | ADWIN        | Statistical guarantees with Hoeffding bounds |
| `cusum`    | AV-CUSUM     | Rapid detection with adaptive variance       |
| `ph`       | Page-Hinkley | Sequential detection with running mean       |

## Call Tree

### Change Point Detection Call Tree

```
ftio/cli/predictor.py::main()
└── ftio/prediction/processes.py::predictor_with_processes()
    └── ftio/prediction/online_analysis.py::ftio_process()
        ├── ftio.cli.ftio_core::main()
        │   ├── FTIO calculation
        │   ├── data parsing
        │   └── prediction queue construction
        │
        ├── ftio.prediction.helper::get_dominant()
        │   └── dominant frequency selection
        │
        ├── ftio.prediction.online_analysis::window_adaptation()
        │   ├── ftio.prediction.online_analysis::hits()
        │   │   └── hit accounting & logging
        │   │
        │   ├── ftio.prediction.change_detection.arwin::AdwinDetector()
        │   │   └── detect_pattern_change_adwin()
        │   │       └── AdwinDetector::add_prediction()
        │   │           └── AdwinDetector::_detect_change()
        │   │
        │   ├── ftio.prediction.change_detection.cusum::CUSUMDetector()
        │   │   └── detect_pattern_change_cusum()
        │   │       └── CUSUMDetector::add_prediction()
        │   │           └── CUSUMDetector::_detect_change()
        │   │
        │   └── ftio.prediction.change_detection.pagehinkley::SelfTuningPageHinkleyDetector()
        │       └── detect_pattern_change_pagehinkley()
        │           └── SelfTuningPageHinkleyDetector::add_prediction()
        │               └── SelfTuningPageHinkleyDetector::_detect_change()
        │
        ├── ftio.prediction.online_analysis::save_data()
        │   └── persist prediction results
        │
        ├── ftio.prediction.online_analysis::display_result()
        │   └── formatted output / GUI text
        │
        └── ftio.gui.socket_logger::send_log()
            └── structured prediction output (GUI)

```

### GUI Integration Call Tree

```
ftio/cli/predictor.py::main()
├── ftio/prediction/online_analysis.py::init_socket_logger()
│   └── online_analysis.py::SocketLogger()
└── ftio/prediction/processes.py::predictor_with_processes()
    └── ftio/prediction/online_analysis.py::ftio_process()
        └── online_analysis.py::log_to_gui_and_console()
            └── online_analysis.py::get_socket_logger()
                └── SocketLogger::send_log()  # Sends to ftio-gui dashboard

ftio/gui/dashboard.py::main()  # ftio-gui command
└── FTIODashApp::run()
    ├── ftio/gui/socket_listener.py::SocketListener()  # Receives from predictor
    └── FTIODashApp::_create_cosine_timeline_plot()    # Renders merged view
```
