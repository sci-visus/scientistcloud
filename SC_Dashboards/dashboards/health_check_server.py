#!/usr/bin/env python3
"""
Simple health check server for Bokeh dashboards
Runs on a separate port to provide /health endpoint for Docker health checks
"""
import http.server
import socketserver
import json
from datetime import datetime
import os

# Health check server runs on a separate port (8052) to avoid conflicts with Bokeh (8051)
HEALTH_PORT = 8052

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "3DVTK Dashboard",
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress health check logs to reduce noise
        if '/health' not in args[0]:
            super().log_message(format, *args)

if __name__ == "__main__":
    with socketserver.TCPServer(("", HEALTH_PORT), HealthCheckHandler) as httpd:
        print(f"Health check server running on port {HEALTH_PORT}")
        httpd.serve_forever()

