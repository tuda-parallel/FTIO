#!/usr/bin/env python3
"""
Launcher script for FTIO GUI Dashboard
"""
import sys
import os
import argparse

# Add the parent directory to Python path so we can import from ftio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.dashboard import FTIODashApp


def main():
    parser = argparse.ArgumentParser(description='FTIO Prediction GUI Dashboard')
    parser.add_argument('--host', default='localhost', help='Dashboard host (default: localhost)')
    parser.add_argument('--port', type=int, default=8050, help='Dashboard port (default: 8050)')
    parser.add_argument('--socket-port', type=int, default=9999, help='Socket listener port (default: 9999)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("FTIO Prediction GUI Dashboard")
    print("=" * 60)
    print(f"Dashboard URL: http://{args.host}:{args.port}")
    print(f"Socket listener: {args.socket_port}")
    print("")
    print("Instructions:")
    print("1. Start this dashboard")
    print("2. Run your FTIO predictor with socket logging enabled")
    print("3. Watch real-time predictions and change points in the browser")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        dashboard = FTIODashApp(
            host=args.host, 
            port=args.port, 
            socket_port=args.socket_port
        )
        dashboard.run(debug=args.debug)
    except KeyboardInterrupt:
        print("\nDashboard stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
