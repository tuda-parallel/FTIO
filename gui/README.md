# FTIO Prediction GUI Dashboard

A real-time visualization dashboard for FTIO prediction data with change point detection.

## Features

### 📊 **1. Global Timeline View**
- **X-axis**: Prediction index (or timestamp)
- **Y-axis**: Dominant frequency (Hz)
- **Line plot**: Shows how dominant frequency evolves across predictions
- **Candidate frequencies**: Overlay as lighter/transparent points
- **Change points**: Marked with vertical dashed lines + annotations (e.g., `4.93 → 3.33 Hz`)
- **Confidence visualization**: Point opacity (higher confidence = darker points)

### 🌊 **2. Per-Prediction Cosine View**
- Select one prediction ID and view its cosine evolution
- Generate cosine wave: `y = cos(2π * f * t)` for the time window
- **Multiple candidates**: Overlay additional cosine curves in lighter colors
- **Change point markers**: Vertical dashed lines with frequency shift annotations

### 🎛️ **3. Interactive Dashboard**
- **View modes**: Timeline only, Cosine only, or Combined dashboard
- **Real-time updates**: New predictions appear automatically via socket connection
- **Click interaction**: Click timeline points to view cosine waves
- **Statistics panel**: Live stats (total predictions, change points, averages)

### 🔄 **4. Real-Time Socket Integration**
- Receives predictions via socket from FTIO predictor
- **Live updates**: Dashboard updates as new predictions arrive
- **Change point alerts**: Immediately highlights frequency shifts
- **Connection status**: Shows socket connection and data flow status

## Installation

### 1. Install Dependencies

```bash
cd gui/
pip install -r requirements.txt
```

### 2. Verify Installation

Make sure you have all required packages:
- `dash` - Web dashboard framework
- `plotly` - Interactive plotting
- `numpy` - Numerical computations
- `pandas` - Data handling (optional)

## Usage

### Method 1: Direct Launch

```bash
cd /path/to/FTIO/gui/
python3 run_dashboard.py
```

### Method 2: With Custom Settings

```bash
python3 run_dashboard.py --host 0.0.0.0 --port 8050 --socket-port 9999 --debug
```

**Parameters:**
- `--host`: Dashboard host (default: `localhost`)
- `--port`: Web dashboard port (default: `8050`)
- `--socket-port`: Socket listener port (default: `9999`)
- `--debug`: Enable debug mode

### Method 3: Programmatic Usage

```python
from gui.dashboard import FTIODashApp

# Create dashboard
dashboard = FTIODashApp(host='localhost', port=8050, socket_port=9999)

# Run dashboard
dashboard.run(debug=False)
```

## How It Works

### 1. Start the Dashboard
```bash
python3 gui/run_dashboard.py
```

The dashboard will:
- Start a web server at `http://localhost:8050`
- Start a socket listener on port `9999`
- Display "Waiting for predictions..." message

### 2. Run FTIO Predictor
```bash
# Your normal FTIO prediction command
predictor your_data.jsonl -e no -f 100 -w "frequency_hits"
```

The modified `online_analysis.py` will:
- Send predictions to socket (port 9999)
- **Still print** to console/terminal as before
- Send change point alerts when detected

### 3. Watch Real-Time Visualization

Open your browser to `http://localhost:8050` and see:
- **Timeline**: Frequency evolution over time
- **Change points**: Red markers with frequency shift labels
- **Cosine waves**: Individual prediction waveforms
- **Statistics**: Live counts and averages

## Dashboard Components

### Control Panel
- **View Mode**: Switch between Timeline, Cosine, or Dashboard view
- **Prediction Selector**: Choose specific prediction for cosine view
- **Clear Data**: Reset all stored predictions
- **Auto Update**: Toggle real-time updates

### Timeline View
```
Frequency (Hz)
    ^
    |  ●——————●——————◆ (Change Point: 4.93 → 3.33 Hz)
    |              /
    |         ●——————●
    |    ●————/
    |___________________________> Prediction Index
```

### Cosine View
```
Amplitude
    ^
    |     /\      /\      /\     <- Primary: 4.93 Hz
    |    /  \    /  \    /  \
    |___/____\__/____\__/____\___> Time (s)
    |         \  /    \  /
    |          \/      \/        <- Candidate: 3.33 Hz (dotted)
```

### Statistics Panel
- **Total Predictions**: Count of received predictions
- **Change Points**: Number of detected frequency shifts
- **Latest Frequency**: Most recent dominant frequency
- **Latest Confidence**: Confidence of latest prediction

## Data Flow

```
FTIO Predictor → Socket (port 9999) → Dashboard → Browser (port 8050)
       ↓                                 ↓
   Console logs                    Live visualization
```

1. **FTIO Predictor** runs prediction analysis
2. **Socket Logger** sends structured data to dashboard
3. **Log Parser** converts log messages to prediction objects
4. **Data Store** maintains prediction history
5. **Dash App** creates interactive visualizations
6. **Browser** displays real-time charts

## Troubleshooting

### Dashboard Won't Start
```bash
# Check if port is already in use
netstat -tulnp | grep :8050

# Try different port
python3 run_dashboard.py --port 8051
```

### No Predictions Appearing
1. **Check socket connection**: Dashboard shows connection status
2. **Verify predictor**: Make sure FTIO predictor is running
3. **Check logs**: Look for socket connection messages
4. **Port conflicts**: Ensure socket port (9999) is available

### Change Points Not Showing
1. **Verify ADWIN**: Make sure change point detection is enabled
2. **Check thresholds**: ADWIN needs sufficient frequency variation
3. **Log parsing**: Verify change point messages in console

### Browser Issues
1. **Clear cache**: Refresh page with Ctrl+F5
2. **Try incognito**: Test in private browsing mode
3. **Check JavaScript**: Ensure JavaScript is enabled

## Customization

### Change Plot Colors
Edit `gui/visualizations.py`:
```python
# Timeline colors
line=dict(color='blue', width=2)  # Main frequency line
marker=dict(color='red', symbol='diamond')  # Change points

# Cosine colors  
colors = ['orange', 'green', 'purple']  # Candidate frequencies
```

### Modify Update Interval
Edit `gui/dashboard.py`:
```python
dcc.Interval(
    id='interval-component',
    interval=2000,  # Change from 2000ms (2 seconds)
    n_intervals=0
)
```

### Add Custom Statistics
Edit `gui/visualizations.py` in `_calculate_stats()`:
```python
stats = {
    'Total Predictions': len(data_store.predictions),
    'Your Custom Stat': your_calculation(),
    # ... add more stats
}
```

## API Reference

### Core Classes

#### `PredictionDataStore`
- `add_prediction(prediction)` - Add new prediction
- `get_prediction_by_id(id)` - Get prediction by ID
- `get_frequency_timeline()` - Get timeline data
- `generate_cosine_wave(id)` - Generate cosine wave data

#### `SocketListener`
- `start_server()` - Start socket server
- `stop_server()` - Stop socket server
- `_handle_client(socket, address)` - Handle client connections

#### `FTIODashApp`
- `run(debug=False)` - Run dashboard server
- `_on_data_received(data)` - Handle incoming prediction data

## Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/gui-enhancement`
3. **Make changes** to GUI components
4. **Test thoroughly** with real FTIO data
5. **Submit pull request**

## License

Same as FTIO project - BSD License

---

**Need help?** Check the console output for debugging information or create an issue with your specific use case.
