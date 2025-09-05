# Transcript Index Manager

This application provides functionality to manage and search through transcript data. It supports both building indexes on-the-fly and working with pre-generated flat index files.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Command Line Interface

The application provides a CLI for managing index files:

1. Generate an index file from transcript data:
   ```bash
   python -m app.cli generate-index /path/to/data/dir explore-index.json.gz
   ```

2. Validate an existing index file:
   ```bash
   python -m app.cli validate-index explore-index.json.gz
   ```

### Running the Web Application

You can run the web application in two modes:


1. Building index on-the-fly (default)

```bash
# Linux / macOS
export FLASK_APP="app:create_app('./data')"
export FLASK_ENV=development
export SECRET_KEY=dev-secret
flask run

# Windows PowerShell
$env:FLASK_APP = "app:create_app('./data')"
$env:FLASK_ENV = "development"
$env:SECRET_KEY = "dev-secret"
python -m flask run
```

2. Using a pre-generated index file

```bash
# Linux / macOS
export FLASK_APP="app:create_app('./data', './explore-index.json.gz')"
flask run

# Windows PowerShell
$env:FLASK_APP = "app:create_app('./data', './explore-index.json.gz')"
python -m flask run
```


## Environment Variables

- `INDEX_FILE`: Path to a pre-generated index file (optional)
- `FLASK_APP`: Set to "app" to run the Flask application
- `FLASK_ENV`: Set to "development" for development mode
- `SECRET_KEY`: Secret key for Flask sessions
- `POSTHOG_API_KEY`: PostHog API key for analytics (optional)
- `POSTHOG_HOST`: PostHog host URL (optional)
- `DISABLE_ANALYTICS`: Set to "true" to disable analytics

## Directory Structure

- `app/`: Main application package
  - `services/`: Core services including index management
  - `routes/`: Web application routes
  - `templates/`: HTML templates
  - `static/`: Static files
  - `cli.py`: Command line interface
- `data/`: Data directory
  - `json/`: Transcript JSON files
  - `audio/`: Audio files

## Project Structure

- `app/` - Main application code
  - `routes/` - Flask route definitions
  - `services/` - Business logic and data services
  - `static/` - CSS, JavaScript, and images
  - `templates/` - HTML templates

## Data Format

The application expects JSON transcript files with the following structure:
```json
[
  {
    "start": 0.0,
    "text": "Transcript text segment"
  },
  ...
]
```

## License

This project is licensed under the MIT License. The data accessible through this application is licensed under the [ivrit.ai license](https://www.ivrit.ai/en/the-license/).

## Contact

For support, help, ideas, and contributions, please contact us at [info@ivrit.ai](mailto:info@ivrit.ai).
