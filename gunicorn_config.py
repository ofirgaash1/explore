#!/usr/bin/env python
# Gunicorn configuration file for ivrit.ai Explore

# Server socket
bind = '0.0.0.0:9000'  # Running on port 9000

# Worker processes
workers = 4  # Recommended: 2-4 x number of CPU cores
worker_class = 'sync'  # Options: sync, eventlet, gevent, tornado, gthread
threads = 2  # Number of worker threads per process
timeout = 120  # Timeout in seconds

# Server mechanics
daemon = False  # Don't daemonize the Gunicorn process
pidfile = 'gunicorn.pid'
umask = 0o007
user = None  # Set to a specific user if needed
group = None  # Set to a specific group if needed

# Logging
errorlog = 'logs/gunicorn-error.log'
accesslog = 'logs/gunicorn-access.log'
loglevel = 'info'  # Options: debug, info, warning, error, critical

# Process naming
proc_name = 'ivrit-explore'

# SSL Support (if needed)
# keyfile = '/etc/letsencrypt/live/explore.ivrit.ai/privkey.pem'
# certfile = '/etc/letsencrypt/live/explore.ivrit.ai/fullchain.pem'

# Server hooks
def on_starting(server):
    """Log when server starts"""
    server.log.info("Starting Gunicorn server for ivrit.ai Explore")

def on_exit(server):
    """Log when server exits"""
    server.log.info("Shutting down Gunicorn server for ivrit.ai Explore") 