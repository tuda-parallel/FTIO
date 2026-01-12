"""
Main Dash application for FTIO prediction visualization
"""
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import threading
import time
from datetime import datetime
import logging

from gui.data_models import PredictionDataStore
from gui.socket_listener import SocketListener
from gui.visualizations import FrequencyTimelineViz, CosineWaveViz, DashboardViz


class FTIODashApp:
    """Main Dash application for FTIO prediction visualization"""
    
    def __init__(self, host='localhost', port=8050, socket_port=9999):
        self.app = dash.Dash(__name__)
        self.host = host
        self.port = port
        self.socket_port = socket_port
        
        # Data storage
        self.data_store = PredictionDataStore()
        self.selected_prediction_id = None
        self.auto_update = True
        self.last_update = time.time()
        
        # Socket listener
        self.socket_listener = SocketListener(
            port=socket_port,
            data_callback=self._on_data_received
        )
        
        # Setup layout and callbacks
        self._setup_layout()
        self._setup_callbacks()
        
        # Start socket listener
        self.socket_thread = self.socket_listener.start_in_thread()
        
        print(f"FTIO Dashboard starting on http://{host}:{port}")
        print(f"Socket listener on port {socket_port}")
    
    def _setup_layout(self):
        """Setup the Dash app layout"""
        
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("FTIO Prediction Visualizer", 
                       style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '20px'}),
                html.Div([
                    html.P(f"Socket listening on port {self.socket_port}", 
                          style={'textAlign': 'center', 'color': '#7f8c8d', 'margin': '0'}),
                    html.P(id='connection-status', children="Waiting for predictions...", 
                          style={'textAlign': 'center', 'color': '#e74c3c', 'margin': '0'})
                ])
            ], style={'marginBottom': '30px'}),
            
            # Controls
            html.Div([
                html.Div([
                    html.Label("View Mode:"),
                    dcc.Dropdown(
                        id='view-mode',
                        options=[
                            {'label': 'Dashboard (Merged Cosine Wave)', 'value': 'dashboard'},
                            {'label': 'Individual Prediction (Single Wave)', 'value': 'cosine'}
                        ],
                        value='dashboard',
                        style={'width': '250px'}
                    )
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Select Prediction:"),
                    dcc.Dropdown(
                        id='prediction-selector',
                        options=[],
                        value=None,
                        placeholder="Select prediction for cosine view",
                        style={'width': '250px'}
                    )
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                html.Div([
                    html.Button("Clear Data", id='clear-button', n_clicks=0,
                              style={'backgroundColor': '#e74c3c', 'color': 'white', 
                                    'border': 'none', 'padding': '8px 16px', 'cursor': 'pointer'}),
                    html.Button("Auto Update", id='auto-update-button', n_clicks=0,
                              style={'backgroundColor': '#27ae60', 'color': 'white', 
                                    'border': 'none', 'padding': '8px 16px', 'cursor': 'pointer',
                                    'marginLeft': '10px'})
                ], style={'display': 'inline-block'})
                
            ], style={'textAlign': 'center', 'marginBottom': '20px', 'padding': '20px',
                     'backgroundColor': '#ecf0f1', 'borderRadius': '5px'}),
            
            # Statistics bar
            html.Div(id='stats-bar', style={'marginBottom': '20px'}),
            
            # Main visualization area
            html.Div(id='main-viz', style={'height': '600px'}),
            
            # Recent predictions table - ALWAYS VISIBLE
            html.Div([
                html.Hr(),
                html.H3("All Predictions", style={'color': '#2c3e50', 'marginTop': '30px'}),
                html.Div(
                    id='recent-predictions-table',
                    style={
                        'maxHeight': '400px',
                        'overflowY': 'auto',
                        'border': '1px solid #ddd',
                        'borderRadius': '8px',
                        'padding': '10px',
                        'backgroundColor': '#f9f9f9'
                    }
                )
            ], style={'marginTop': '20px'}),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=2000,  # Update every 2 seconds
                n_intervals=0
            ),
            
            # Store components for data persistence
            dcc.Store(id='data-store-trigger')
        ])
    
    def _setup_callbacks(self):
        """Setup Dash callbacks"""
        
        @self.app.callback(
            [Output('main-viz', 'children'),
             Output('prediction-selector', 'options'),
             Output('prediction-selector', 'value'),
             Output('connection-status', 'children'),
             Output('connection-status', 'style'),
             Output('stats-bar', 'children')],
            [Input('interval-component', 'n_intervals'),
             Input('view-mode', 'value'),
             Input('prediction-selector', 'value'),
             Input('clear-button', 'n_clicks')],
            [State('auto-update-button', 'n_clicks')]
        )
        def update_visualization(n_intervals, view_mode, selected_pred_id, clear_clicks, auto_clicks):
            
            # Handle clear button
            ctx = callback_context
            if ctx.triggered and ctx.triggered[0]['prop_id'] == 'clear-button.n_clicks':
                if clear_clicks > 0:
                    self.data_store.clear_data()
                    self.selected_prediction_id = None
            
            # Update prediction selector options
            pred_options = []
            pred_value = selected_pred_id
            
            if self.data_store.predictions:
                pred_options = [
                    {'label': f"Prediction #{p.prediction_id} ({p.dominant_freq:.2f} Hz)", 
                     'value': p.prediction_id}
                    for p in self.data_store.predictions[-50:]  # Last 50 predictions
                ]
                
                # Auto-select latest prediction if none selected
                if pred_value is None and self.data_store.predictions:
                    pred_value = self.data_store.predictions[-1].prediction_id
            
            # Update connection status
            if self.data_store.predictions:
                status_text = f"Connected - {len(self.data_store.predictions)} predictions received"
                status_style = {'textAlign': 'center', 'color': '#27ae60', 'margin': '0'}
            else:
                status_text = "Waiting for predictions..."
                status_style = {'textAlign': 'center', 'color': '#e74c3c', 'margin': '0'}
            
            # Create statistics bar
            stats_bar = self._create_stats_bar()
            
            # Create main visualization based on view mode
            if view_mode == 'cosine' and pred_value is not None:
                fig = CosineWaveViz.create_cosine_plot(self.data_store, pred_value)
                viz_component = dcc.Graph(figure=fig, style={'height': '600px'})
                
            elif view_mode == 'dashboard':
                # Dashboard shows cosine timeline (not raw frequency)
                fig = self._create_cosine_timeline_plot(self.data_store)
                viz_component = dcc.Graph(figure=fig, style={'height': '600px'})
                
            else:
                viz_component = html.Div([
                    html.H3("Select a view mode and prediction to visualize", 
                           style={'textAlign': 'center', 'color': '#7f8c8d', 'marginTop': '200px'})
                ])
            
            return viz_component, pred_options, pred_value, status_text, status_style, stats_bar
        
        @self.app.callback(
            Output('recent-predictions-table', 'children'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_recent_predictions_table(n_intervals):
            """Update the recent predictions table"""
            
            if not self.data_store.predictions:
                return html.P("No predictions yet", style={'textAlign': 'center', 'color': '#7f8c8d'})
            
            # Get ALL predictions for the table
            recent_preds = self.data_store.predictions

            # Remove duplicates by using a set to track seen prediction IDs
            seen_ids = set()
            unique_preds = []
            for pred in reversed(recent_preds):  # Newest first
                if pred.prediction_id not in seen_ids:
                    seen_ids.add(pred.prediction_id)
                    unique_preds.append(pred)

            # Create table rows with better styling
            rows = []
            for i, pred in enumerate(unique_preds):
                # Alternate row colors
                row_style = {
                    'backgroundColor': '#ffffff' if i % 2 == 0 else '#f8f9fa',
                    'padding': '8px',
                    'borderBottom': '1px solid #dee2e6'
                }

                # Check if no frequency was found (frequency = 0 or None)
                if pred.dominant_freq == 0 or pred.dominant_freq is None:
                    # Show GAP - no prediction found
                    row = html.Tr([
                        html.Td(f"#{pred.prediction_id}", style={'fontWeight': 'bold', 'color': '#999'}),
                        html.Td("—", style={'color': '#999', 'textAlign': 'center', 'fontStyle': 'italic'}),
                        html.Td("No pattern detected", style={'color': '#999', 'fontStyle': 'italic'})
                    ], style=row_style)
                else:
                    # Normal prediction
                    change_point_text = ""
                    if pred.is_change_point and pred.change_point:
                        cp = pred.change_point
                        change_point_text = f"🔴 {cp.old_frequency:.2f} → {cp.new_frequency:.2f} Hz"

                    row = html.Tr([
                        html.Td(f"#{pred.prediction_id}", style={'fontWeight': 'bold', 'color': '#495057'}),
                        html.Td(f"{pred.dominant_freq:.2f} Hz", style={'color': '#007bff'}),
                        html.Td(change_point_text, style={'color': 'red' if pred.is_change_point else 'black'})
                    ], style=row_style)

                rows.append(row)
            
            # Create beautiful table with modern styling
            table = html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("ID", style={'backgroundColor': '#6c757d', 'color': 'white', 'padding': '12px'}),
                        html.Th("Frequency", style={'backgroundColor': '#6c757d', 'color': 'white', 'padding': '12px'}),
                        html.Th("Change Point", style={'backgroundColor': '#6c757d', 'color': 'white', 'padding': '12px'})
                    ])
                ]),
                html.Tbody(rows)
            ], style={
                'width': '100%', 
                'borderCollapse': 'collapse', 
                'marginTop': '10px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'borderRadius': '8px',
                'overflow': 'hidden'
            })
            
            return table
    
    def _create_stats_bar(self):
        """Create statistics bar component"""
        
        if not self.data_store.predictions:
            return html.Div()
        
        # Calculate basic stats
        total_preds = len(self.data_store.predictions)
        total_changes = len(self.data_store.change_points)
        latest_pred = self.data_store.predictions[-1]
        
        stats_items = [
            html.Div([
                html.H4(str(total_preds), style={'margin': '0', 'color': '#2c3e50'}),
                html.P("Total Predictions", style={'margin': '0', 'fontSize': '12px', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'flex': '1'}),
            
            html.Div([
                html.H4(str(total_changes), style={'margin': '0', 'color': '#e74c3c'}),
                html.P("Change Points", style={'margin': '0', 'fontSize': '12px', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'flex': '1'}),
            
            html.Div([
                html.H4(f"{latest_pred.dominant_freq:.2f} Hz", style={'margin': '0', 'color': '#27ae60'}),
                html.P("Latest Frequency", style={'margin': '0', 'fontSize': '12px', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'flex': '1'}),
            
            html.Div([
                html.H4(f"{latest_pred.confidence:.1f}%", style={'margin': '0', 'color': '#3498db'}),
                html.P("Latest Confidence", style={'margin': '0', 'fontSize': '12px', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'flex': '1'})
        ]
        
        return html.Div(stats_items, style={
            'display': 'flex',
            'justifyContent': 'space-around',
            'backgroundColor': '#f8f9fa',
            'padding': '15px',
            'borderRadius': '5px',
            'border': '1px solid #dee2e6'
        })
    
    def _on_data_received(self, data):
        """Callback when new data is received from socket"""
        print(f"[DEBUG] Dashboard received data: {data}")
        
        if data['type'] == 'prediction':
            prediction_data = data['data']
            self.data_store.add_prediction(prediction_data)
            
            print(f"[DEBUG] Added prediction #{prediction_data.prediction_id}: "
                  f"{prediction_data.dominant_freq:.2f} Hz "
                  f"({'CHANGE POINT' if prediction_data.is_change_point else 'normal'})")
            
            self.last_update = time.time()
        else:
            print(f"[DEBUG] Received non-prediction data: type={data.get('type')}")
    
    def _create_cosine_timeline_plot(self, data_store):
        """Create single continuous cosine wave showing I/O pattern evolution"""
        import plotly.graph_objs as go
        import numpy as np
        
        if not data_store.predictions:
            fig = go.Figure()
            fig.add_annotation(
                x=0.5, y=0.5,
                text="Waiting for predictions...",
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                title="I/O Pattern Timeline (Continuous Cosine Wave)"
            )
            return fig
        
        # Get only last 3 predictions for the graph
        last_3_predictions = data_store.get_latest_predictions(3)

        # Sort predictions chronologically by time window start
        sorted_predictions = sorted(last_3_predictions, key=lambda p: p.time_window[0])
        
        # Build one continuous timeline by concatenating segments back-to-back
        global_time = []
        global_cosine = []
        cumulative_time = 0.0
        segment_info = []  # For change point markers
        
        for pred in sorted_predictions:
            t_start, t_end = pred.time_window
            duration = max(0.001, t_end - t_start)  # Ensure positive duration
            freq = pred.dominant_freq

            # Check if no frequency found - show GAP
            if freq == 0 or freq is None:
                # Add a GAP (flat line at 0 or None values to break the line)
                num_points = 100
                t_local = np.linspace(0, duration, num_points)
                t_global = cumulative_time + t_local

                # Add None values to create a gap in the plot
                global_time.extend(t_global.tolist())
                global_cosine.extend([None] * num_points)  # None creates a gap
            else:
                # Generate points proportional to frequency for smooth waves
                num_points = max(100, int(freq * duration * 50))  # 50 points per cycle

                # Local time for this segment (0 to duration)
                t_local = np.linspace(0, duration, num_points)

                # Cosine wave for this segment (starts at phase 0)
                cosine_segment = np.cos(2 * np.pi * freq * t_local)

                # Map to global concatenated timeline
                t_global = cumulative_time + t_local

                # Add to continuous arrays
                global_time.extend(t_global.tolist())
                global_cosine.extend(cosine_segment.tolist())

            # Store segment info for change point markers
            segment_start = cumulative_time
            segment_end = cumulative_time + duration
            segment_info.append((segment_start, segment_end, pred))

            # Advance cumulative time pointer
            cumulative_time += duration
        
        fig = go.Figure()

        # Single continuous cosine trace (None values will create gaps)
        fig.add_trace(go.Scatter(
            x=global_time,
            y=global_cosine,
            mode='lines',
            name='I/O Pattern Evolution',
            line=dict(color='#1f77b4', width=2),
            connectgaps=False,  # DON'T connect across None values - creates visible gaps
            hovertemplate="<b>I/O Pattern</b><br>" +
                         "Time: %{x:.3f} s<br>" +
                         "Amplitude: %{y:.3f}<extra></extra>"
        ))

        # Add gray boxes to highlight GAP regions where no pattern was detected
        for seg_start, seg_end, pred in segment_info:
            if pred.dominant_freq == 0 or pred.dominant_freq is None:
                fig.add_vrect(
                    x0=seg_start,
                    x1=seg_end,
                    fillcolor="gray",
                    opacity=0.15,
                    layer="below",
                    line_width=0,
                    annotation_text="No pattern",
                    annotation_position="top"
                )
        
        # Add RED change point markers at segment start (just vertical lines, no stars)
        for seg_start, seg_end, pred in segment_info:
            if pred.is_change_point and pred.change_point:
                marker_time = seg_start  # Mark at the START of the changed segment

                # RED vertical line (no rounding - show exact values)
                fig.add_vline(
                    x=marker_time,
                    line_dash="solid",
                    line_color="red",
                    line_width=4,
                    opacity=0.8
                )

                # Add annotation above with EXACT frequency values (2 decimals)
                fig.add_annotation(
                    x=marker_time,
                    y=1.1,
                    text=f"🔴 CHANGE<br>{pred.change_point.old_frequency:.2f}→{pred.change_point.new_frequency:.2f} Hz",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="red",
                    ax=0,
                    ay=-40,
                    font=dict(size=12, color="red", family="Arial Black"),
                    bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="red",
                    borderwidth=2
                )
        
        # Configure layout with uirevision to prevent full refresh
        fig.update_layout(
            title="I/O Pattern Timeline (Continuous Evolution)",
            xaxis_title="Time (s) - Concatenated Segments",
            yaxis_title="I/O Pattern Amplitude",
            showlegend=True,
            height=600,
            hovermode='x unified',
            yaxis=dict(range=[-1.2, 1.2]),
            uirevision='constant'  # Prevents full page refresh - keeps zoom/pan state
        )
        
        return fig
    
    def run(self, debug=False):
        """Run the Dash application"""
        try:
            self.app.run(host=self.host, port=self.port, debug=debug)
        except KeyboardInterrupt:
            print("\nShutting down FTIO Dashboard...")
            self.socket_listener.stop_server()
        except Exception as e:
            print(f"Error running dashboard: {e}")
            self.socket_listener.stop_server()


if __name__ == "__main__":
    # Create and run the dashboard
    dashboard = FTIODashApp(host='localhost', port=8050, socket_port=9999)
    dashboard.run(debug=False)
