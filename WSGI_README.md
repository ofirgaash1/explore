# WSGI Deployment for ivrit.ai Explore

This document provides instructions for deploying the ivrit.ai Explore application using WSGI servers.

## WSGI Entry Point

The application provides a WSGI entry point in `wsgi.py`. This file initializes the Flask application and exposes it as a WSGI application object named `application`.

## Deployment Options

### Using Gunicorn

[Gunicorn](https://gunicorn.org/) is a Python WSGI HTTP Server for UNIX. It's a pre-fork worker model ported from Ruby's Unicorn project.

#### Installation

```bash
pip install gunicorn
```

#### Running with Gunicorn

Basic usage:

```bash
gunicorn wsgi:application
```

With configuration file:

```bash
gunicorn -c gunicorn_config.py wsgi:application
```

With command-line options:

```bash
gunicorn --workers=4 --bind=0.0.0.0:8000 --timeout=120 wsgi:application
```

With data directory and force reindex options:

```bash
gunicorn "wsgi:application" --env PYTHONPATH=. --preload
```

Note: When using `--preload`, Gunicorn will load your application before forking worker processes, which allows command-line arguments to be processed.

### Using uWSGI

[uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) is another popular WSGI server.

#### Installation

```bash
pip install uwsgi
```

#### Running with uWSGI

Basic usage:

```bash
uwsgi --http :8000 --wsgi-file wsgi.py --callable application
```

With more options:

```bash
uwsgi --http :8000 --wsgi-file wsgi.py --callable application --processes 4 --threads 2 --master
```

### Using with Nginx

For production deployments, it's recommended to use Nginx as a reverse proxy in front of Gunicorn or uWSGI.

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name explore.ivrit.ai;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## SSL Configuration

For SSL support, you can either:

1. Configure SSL in your WSGI server (both Gunicorn and uWSGI support SSL)
2. Configure SSL in Nginx (recommended for production)

The Gunicorn configuration file includes commented SSL options that you can uncomment and modify as needed.

## Command-line Arguments

The WSGI entry point supports the following command-line arguments:

- `--data-dir`: Path to the data directory (default: 'data')
- `--force-reindex`: Force rebuilding of search indices

Example:

```bash
gunicorn "wsgi:application()" --env PYTHONPATH=. --preload -- --data-dir=/path/to/data --force-reindex
```

## Systemd Service

For running as a systemd service, create a file `/etc/systemd/system/ivrit-explore.service`:

```ini
[Unit]
Description=ivrit.ai Explore Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/ivrit-explore
ExecStart=/path/to/gunicorn -c gunicorn_config.py wsgi:application
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable ivrit-explore
sudo systemctl start ivrit-explore
``` 