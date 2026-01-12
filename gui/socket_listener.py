"""
Socket listener for receiving FTIO prediction logs and parsing them into structured data
"""
import socket
import json
import threading
import re
import logging
from typing import Optional, Callable
from gui.data_models import PredictionData, ChangePoint, FrequencyCandidate, PredictionDataStore


class LogParser:
    """Parses FTIO prediction log messages into structured data"""
    
    def __init__(self):
        # Regex patterns for parsing different log types
        self.patterns = {
            'prediction_start': re.compile(r'\[PREDICTOR\]\s+\(#(\d+)\):\s+Started'),
            'prediction_end': re.compile(r'\[PREDICTOR\]\s+\(#(\d+)\):\s+Ended'),
            'dominant_freq': re.compile(r'\[PREDICTOR\]\s+\(#(\d+)\):\s+Dominant freq\s+([\d.]+)\s+Hz\s+\(([\d.]+)\s+sec\)'),
            'freq_candidates': re.compile(r'\[PREDICTOR\]\s+\(#(\d+)\):\s+\d+\)\s+([\d.]+)\s+Hz\s+--\s+conf\s+([\d.]+)'),
            'time_window': re.compile(r'\[PREDICTOR\]\s+\(#(\d+)\):\s+Time window\s+([\d.]+)\s+sec\s+\(\[([\d.]+),([\d.]+)\]\s+sec\)'),
            'total_bytes': re.compile(r'\[PREDICTOR\]\s+\(#(\d+)\):\s+Total bytes\s+(.+)'),
            'bytes_transferred': re.compile(r'\[PREDICTOR\]\s+\(#(\d+)\):\s+Bytes transferred since last time\s+(.+)'),
            'current_hits': re.compile(r'\[PREDICTOR\]\s+\(#(\d+)\):\s+Current hits\s+([\d.]+)'),
            'periodic_prob': re.compile(r'\[PREDICTOR\]\s+P\(periodic\)\s+=\s+([\d.]+)%'),
            'freq_range': re.compile(r'\[PREDICTOR\]\s+P\(\[([\d.]+),([\d.]+)\]\s+Hz\)\s+=\s+([\d.]+)%'),
            'period_range': re.compile(r'\[PREDICTOR\]\s+\|->\s+\[([\d.]+),([\d.]+)\]\s+Hz\s+=\s+\[([\d.]+),([\d.]+)\]\s+sec'),
            # ADWIN change detection
            'change_point': re.compile(r'\[ADWIN\]\s+Change detected at cut\s+(\d+)/(\d+)!'),
            'exact_change_point': re.compile(r'EXACT CHANGE POINT detected at\s+([\d.]+)\s+seconds!'),
            'frequency_shift': re.compile(r'\[ADWIN\]\s+Frequency shift:\s+([\d.]+)\s+→\s+([\d.]+)\s+Hz\s+\(([\d.]+)%\)'),
            'sample_number': re.compile(r'\[ADWIN\]\s+Sample\s+#(\d+):\s+freq=([\d.]+)\s+Hz'),
            # Page-Hinkley change detection
            'ph_change': re.compile(r'\[Page-Hinkley\]\s+PAGE-HINKLEY CHANGE DETECTED!\s+\w+\s+([\d.]+)Hz\s+→\s+([\d.]+)Hz.*?at sample\s+(\d+),\s+time=([\d.]+)s'),
            'stph_change': re.compile(r'\[STPH\]\s+CHANGE DETECTED!\s+([\d.]+)Hz\s+→\s+([\d.]+)Hz\s+\(([\d.]+)%'),
            # CUSUM change detection (multiple formats)
            'cusum_change': re.compile(r'\[AV-CUSUM\]\s+CHANGE DETECTED!\s+([\d.]+)Hz\s+→\s+([\d.]+)Hz\s+\(([\d.]+)%'),
            'cusum_change_alt': re.compile(r'\[CUSUM\]\s+CHANGE DETECTED!\s+([\d.]+)Hz\s+→\s+([\d.]+)Hz.*?time=([\d.]+)s'),
        }
        
        self.current_prediction = None
        self.current_change_point = None
        self.candidates_buffer = []
    
    def parse_log_message(self, message: str) -> Optional[dict]:
        """Parse a single log message and return structured data"""
        
        # Check for prediction start
        match = self.patterns['prediction_start'].search(message)
        if match:
            pred_id = int(match.group(1))
            self.current_prediction = {
                'prediction_id': pred_id,
                'candidates': [],
                'is_change_point': False,
                'change_point': None,
                'timestamp': '',
                'sample_number': None
            }
            self.candidates_buffer = []
            return None
        
        if not self.current_prediction:
            return None
            
        pred_id = self.current_prediction['prediction_id']
        
        # Parse dominant frequency
        match = self.patterns['dominant_freq'].search(message)
        if match and int(match.group(1)) == pred_id:
            self.current_prediction['dominant_freq'] = float(match.group(2))
            self.current_prediction['dominant_period'] = float(match.group(3))
        
        # Parse frequency candidates
        match = self.patterns['freq_candidates'].search(message)
        if match and int(match.group(1)) == pred_id:
            freq = float(match.group(2))
            conf = float(match.group(3))
            self.candidates_buffer.append(FrequencyCandidate(freq, conf))
        
        # Parse time window
        match = self.patterns['time_window'].search(message)
        if match and int(match.group(1)) == pred_id:
            self.current_prediction['time_window'] = (float(match.group(3)), float(match.group(4)))
        
        # Parse total bytes
        match = self.patterns['total_bytes'].search(message)
        if match and int(match.group(1)) == pred_id:
            self.current_prediction['total_bytes'] = match.group(2).strip()
        
        # Parse bytes transferred
        match = self.patterns['bytes_transferred'].search(message)
        if match and int(match.group(1)) == pred_id:
            self.current_prediction['bytes_transferred'] = match.group(2).strip()
        
        # Parse current hits
        match = self.patterns['current_hits'].search(message)
        if match and int(match.group(1)) == pred_id:
            self.current_prediction['current_hits'] = int(float(match.group(2)))
        
        # Parse periodic probability
        match = self.patterns['periodic_prob'].search(message)
        if match:
            self.current_prediction['periodic_probability'] = float(match.group(1))
        
        # Parse frequency range
        match = self.patterns['freq_range'].search(message)
        if match:
            self.current_prediction['frequency_range'] = (float(match.group(1)), float(match.group(2)))
            self.current_prediction['confidence'] = float(match.group(3))
        
        # Parse period range
        match = self.patterns['period_range'].search(message)
        if match:
            self.current_prediction['period_range'] = (float(match.group(3)), float(match.group(4)))
        
        # Parse change point detection
        match = self.patterns['change_point'].search(message)
        if match:
            self.current_change_point = {
                'cut_position': int(match.group(1)),
                'total_samples': int(match.group(2)),
                'prediction_id': pred_id
            }
            self.current_prediction['is_change_point'] = True
        
        # Parse exact change point timestamp
        match = self.patterns['exact_change_point'].search(message)
        if match and self.current_change_point:
            self.current_change_point['timestamp'] = float(match.group(1))
        
        # Parse frequency shift
        match = self.patterns['frequency_shift'].search(message)
        if match and self.current_change_point:
            self.current_change_point['old_frequency'] = float(match.group(1))
            self.current_change_point['new_frequency'] = float(match.group(2))
            self.current_change_point['frequency_change_percent'] = float(match.group(3))
        
        # Parse sample number
        match = self.patterns['sample_number'].search(message)
        if match:
            self.current_prediction['sample_number'] = int(match.group(1))

        # Parse Page-Hinkley change detection
        match = self.patterns['ph_change'].search(message)
        if match:
            self.current_change_point = {
                'old_frequency': float(match.group(1)),
                'new_frequency': float(match.group(2)),
                'cut_position': int(match.group(3)),
                'total_samples': int(match.group(3)),
                'timestamp': float(match.group(4)),
                'frequency_change_percent': abs((float(match.group(2)) - float(match.group(1))) / float(match.group(1)) * 100) if float(match.group(1)) > 0 else 0,
                'prediction_id': pred_id
            }
            self.current_prediction['is_change_point'] = True

        # Parse STPH change detection (additional info for Page-Hinkley)
        match = self.patterns['stph_change'].search(message)
        if match:
            if not self.current_change_point:
                self.current_change_point = {'prediction_id': pred_id}
            self.current_change_point['old_frequency'] = float(match.group(1))
            self.current_change_point['new_frequency'] = float(match.group(2))
            self.current_change_point['frequency_change_percent'] = float(match.group(3))
            self.current_prediction['is_change_point'] = True

        # Parse CUSUM change detection
        match = self.patterns['cusum_change'].search(message)
        if match:
            if not self.current_change_point:
                self.current_change_point = {'prediction_id': pred_id}
            self.current_change_point['old_frequency'] = float(match.group(1))
            self.current_change_point['new_frequency'] = float(match.group(2))
            self.current_change_point['frequency_change_percent'] = float(match.group(3))
            self.current_prediction['is_change_point'] = True

        # Parse CUSUM change detection (alternative format)
        match = self.patterns['cusum_change_alt'].search(message)
        if match:
            if not self.current_change_point:
                self.current_change_point = {'prediction_id': pred_id}
            self.current_change_point['old_frequency'] = float(match.group(1))
            self.current_change_point['new_frequency'] = float(match.group(2))
            self.current_change_point['timestamp'] = float(match.group(3))
            self.current_change_point['frequency_change_percent'] = abs((float(match.group(2)) - float(match.group(1))) / float(match.group(1)) * 100) if float(match.group(1)) > 0 else 0
            self.current_prediction['is_change_point'] = True

        # Check for prediction end
        match = self.patterns['prediction_end'].search(message)
        if match and int(match.group(1)) == pred_id:
            # Finalize the prediction data
            self.current_prediction['candidates'] = self.candidates_buffer.copy()
            
            # Create change point if detected
            if self.current_prediction['is_change_point'] and self.current_change_point:
                change_point = ChangePoint(
                    prediction_id=pred_id,
                    timestamp=self.current_change_point.get('timestamp', 0.0),
                    old_frequency=self.current_change_point.get('old_frequency', 0.0),
                    new_frequency=self.current_change_point.get('new_frequency', 0.0),
                    frequency_change_percent=self.current_change_point.get('frequency_change_percent', 0.0),
                    sample_number=self.current_prediction.get('sample_number', 0),
                    cut_position=self.current_change_point.get('cut_position', 0),
                    total_samples=self.current_change_point.get('total_samples', 0)
                )
                self.current_prediction['change_point'] = change_point
            
            # Create PredictionData object
            prediction_data = PredictionData(
                prediction_id=pred_id,
                timestamp=self.current_prediction.get('timestamp', ''),
                dominant_freq=self.current_prediction.get('dominant_freq', 0.0),
                dominant_period=self.current_prediction.get('dominant_period', 0.0),
                confidence=self.current_prediction.get('confidence', 0.0),
                candidates=self.current_prediction['candidates'],
                time_window=self.current_prediction.get('time_window', (0.0, 0.0)),
                total_bytes=self.current_prediction.get('total_bytes', ''),
                bytes_transferred=self.current_prediction.get('bytes_transferred', ''),
                current_hits=self.current_prediction.get('current_hits', 0),
                periodic_probability=self.current_prediction.get('periodic_probability', 0.0),
                frequency_range=self.current_prediction.get('frequency_range', (0.0, 0.0)),
                period_range=self.current_prediction.get('period_range', (0.0, 0.0)),
                is_change_point=self.current_prediction['is_change_point'],
                change_point=self.current_prediction['change_point'],
                sample_number=self.current_prediction.get('sample_number')
            )
            
            # Reset for next prediction
            self.current_prediction = None
            self.current_change_point = None
            self.candidates_buffer = []
            
            return {'type': 'prediction', 'data': prediction_data}
        
        return None


class SocketListener:
    """Listens for socket connections and processes FTIO prediction logs"""
    
    def __init__(self, host='localhost', port=9999, data_callback: Optional[Callable] = None):
        self.host = host
        self.port = port
        self.data_callback = data_callback
        self.parser = LogParser()
        self.running = False
        self.server_socket = None
        self.client_connections = []
        
    def start_server(self):
        """Start the socket server to listen for connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to bind to the port
            print(f"Attempting to bind to {self.host}:{self.port}")
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"✅ Socket server successfully listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"🔌 Client connected from {address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"❌ Error accepting client connection: {e}")
                    break
                except KeyboardInterrupt:
                    print("🛑 Socket server interrupted")
                    break
                    
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"Port {self.port} is already in use! Please use a different port or kill the process using it.")
            else:
                print(f"OS Error starting socket server: {e}")
            self.running = False
        except Exception as e:
            print(f"Unexpected error starting socket server: {e}")
            import traceback
            traceback.print_exc()
            self.running = False
        finally:
            self.stop_server()
    
    def _handle_client(self, client_socket, address):
        """Handle individual client connection"""
        try:
            while self.running:
                try:
                    data = client_socket.recv(4096).decode('utf-8')
                    if not data:
                        break
                    
                    # Process received message
                    try:
                        message_data = json.loads(data)
                        
                        # Check if this is direct prediction data (from test scripts)
                        if message_data.get('type') == 'prediction' and 'data' in message_data:
                            print(f"[DEBUG] Direct prediction data received: #{message_data['data']['prediction_id']}")
                            
                            # Convert the data to PredictionData object
                            pred_data = message_data['data']
                            
                            # Convert candidates to FrequencyCandidate objects
                            candidates = []
                            for cand in pred_data.get('candidates', []):
                                candidates.append(FrequencyCandidate(
                                    frequency=cand['frequency'],
                                    confidence=cand['confidence']
                                ))
                            
                            # Convert change point to ChangePoint object if present
                            change_point = None
                            if pred_data.get('is_change_point') and pred_data.get('change_point'):
                                cp_data = pred_data['change_point']
                                change_point = ChangePoint(
                                    prediction_id=cp_data['prediction_id'],
                                    timestamp=cp_data['timestamp'],
                                    old_frequency=cp_data['old_frequency'],
                                    new_frequency=cp_data['new_frequency'],
                                    frequency_change_percent=cp_data['frequency_change_percent'],
                                    sample_number=cp_data['sample_number'],
                                    cut_position=cp_data['cut_position'],
                                    total_samples=cp_data['total_samples']
                                )
                            
                            # Create PredictionData object
                            prediction_data = PredictionData(
                                prediction_id=pred_data['prediction_id'],
                                timestamp=pred_data['timestamp'],
                                dominant_freq=pred_data['dominant_freq'],
                                dominant_period=pred_data['dominant_period'],
                                confidence=pred_data['confidence'],
                                candidates=candidates,
                                time_window=tuple(pred_data['time_window']),
                                total_bytes=pred_data['total_bytes'],
                                bytes_transferred=pred_data['bytes_transferred'],
                                current_hits=pred_data['current_hits'],
                                periodic_probability=pred_data['periodic_probability'],
                                frequency_range=tuple(pred_data['frequency_range']),
                                period_range=tuple(pred_data['period_range']),
                                is_change_point=pred_data['is_change_point'],
                                change_point=change_point,
                                sample_number=pred_data.get('sample_number')
                            )
                            
                            # Send to callback
                            if self.data_callback:
                                self.data_callback({'type': 'prediction', 'data': prediction_data})
                        
                        else:
                            # Handle log message format (original behavior)
                            log_message = message_data.get('message', '')
                            
                            # Parse the log message
                            parsed_data = self.parser.parse_log_message(log_message)
                            
                            if parsed_data and self.data_callback:
                                self.data_callback(parsed_data)
                            
                    except json.JSONDecodeError:
                        # Handle plain text messages
                        parsed_data = self.parser.parse_log_message(data.strip())
                        if parsed_data and self.data_callback:
                            self.data_callback(parsed_data)
                            
                except socket.error:
                    break
                    
        except Exception as e:
            logging.error(f"Error handling client {address}: {e}")
        finally:
            try:
                client_socket.close()
                print(f"Client {address} disconnected")
            except:
                pass
    
    def stop_server(self):
        """Stop the socket server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        for client_socket in self.client_connections:
            try:
                client_socket.close()
            except:
                pass
        self.client_connections.clear()
        print("Socket server stopped")
    
    def start_in_thread(self):
        """Start the server in a background thread"""
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()
        return server_thread
