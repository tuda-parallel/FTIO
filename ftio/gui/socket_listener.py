"""
Socket listener for receiving FTIO prediction data via direct JSON transmission.

This module provides a TCP socket server that receives structured prediction
data from FTIO's online predictor via direct JSON transmission.

Author: Amine Aherbil
Copyright (c) 2025 TU Darmstadt, Germany
Date: January 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""
import socket
import json
import threading
import logging
from typing import Optional, Callable
from ftio.gui.data_models import PredictionData, ChangePoint, FrequencyCandidate, PredictionDataStore


class SocketListener:
    """Listens for socket connections and processes FTIO prediction data"""

    def __init__(self, host='localhost', port=9999, data_callback: Optional[Callable] = None):
        self.host = host
        self.port = port
        self.data_callback = data_callback
        self.running = False
        self.server_socket = None
        self.client_connections = []

    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            print(f"Attempting to bind to {self.host}:{self.port}")
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f" Socket server successfully listening on {self.host}:{self.port}")

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f" Client connected from {address}")

                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.error as e:
                    if self.running:
                        print(f"Error accepting client connection: {e}")
                    break
                except KeyboardInterrupt:
                    print(" Socket server interrupted")
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
        try:
            while self.running:
                try:
                    data = client_socket.recv(4096).decode('utf-8')
                    if not data:
                        break

                    try:
                        message_data = json.loads(data)

                        if message_data.get('type') == 'prediction' and 'data' in message_data:
                            print(f"[DEBUG] Direct prediction data received: #{message_data['data']['prediction_id']}")

                            pred_data = message_data['data']

                            candidates = []
                            for cand in pred_data.get('candidates', []):
                                candidates.append(FrequencyCandidate(
                                    frequency=cand['frequency'],
                                    confidence=cand['confidence']
                                ))

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

                            if self.data_callback:
                                self.data_callback({'type': 'prediction', 'data': prediction_data})

                    except json.JSONDecodeError:
                        pass

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
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()
        return server_thread
