#!/usr/bin/env python3
"""
Simple test client to verify socket communication with the GUI server.
Run this to test that the socket server is working before running FTIO.
"""

import socket
import json
import time
import random

def send_test_logs():
    """Send test log messages to the GUI server"""
    
    try:
        # Connect to server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 9999))
        print("Connected to GUI server")
        
        # Send test messages
        test_messages = [
            {
                'timestamp': time.time(),
                'type': 'predictor_start',
                'message': '[PREDICTOR] (#0): Started',
                'data': {'count': 0}
            },
            {
                'timestamp': time.time(),
                'type': 'adwin',
                'message': '[ADWIN] Sample #1: freq=4.167 Hz, time=0.297802s',
                'data': {'sample_number': 1, 'frequency': 4.167, 'time': 0.297802}
            },
            {
                'timestamp': time.time(),
                'type': 'change_detection',
                'message': '[ADWIN] Change detected at cut 5/10!',
                'data': {'cut': 5, 'window_size': 10}
            },
            {
                'timestamp': time.time(),
                'type': 'change_point',
                'message': 'EXACT CHANGE POINT detected at 1.876802 seconds!',
                'data': {
                    'exact_time': 1.876802,
                    'old_freq': 3.730,
                    'new_freq': 4.930,
                    'freq_change_pct': 32.2
                }
            },
            {
                'timestamp': time.time(),
                'type': 'prediction_result',
                'message': '[PREDICTOR] (#0): Dominant freq 4.167 Hz (0.24 sec)',
                'data': {
                    'count': 0,
                    'freq': 4.167,
                    'prediction_data': {
                        't_start': 0.051,
                        't_end': 0.298,
                        'total_bytes': 1073741824
                    }
                }
            }
        ]
        
        for i, message in enumerate(test_messages):
            message['timestamp'] = time.time()  # Update timestamp
            json_data = json.dumps(message) + '\\n'
            client_socket.send(json_data.encode('utf-8'))
            print(f"Sent test message {i+1}: {message['type']}")
            time.sleep(1)  # Wait 1 second between messages
        
        # Keep sending periodic ADWIN samples
        for sample_num in range(2, 20):
            freq = random.uniform(3.0, 5.5)
            current_time = time.time()
            
            sample_msg = {
                'timestamp': current_time,
                'type': 'adwin',
                'message': f'[ADWIN] Sample #{sample_num}: freq={freq:.3f} Hz, time={current_time:.6f}s',
                'data': {
                    'sample_number': sample_num,
                    'frequency': freq,
                    'time': current_time,
                    'type': 'sample'
                }
            }
            
            json_data = json.dumps(sample_msg) + '\\n'
            client_socket.send(json_data.encode('utf-8'))
            print(f"Sent ADWIN sample #{sample_num}")
            time.sleep(2)
        
        print("All test messages sent successfully")
        
    except ConnectionRefusedError:
        print("Error: Could not connect to GUI server. Make sure it's running first.")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'client_socket' in locals():
            client_socket.close()

if __name__ == "__main__":
    send_test_logs()
