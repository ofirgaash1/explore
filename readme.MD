# ivrit.ai Explore

A web application for searching and exploring Hebrew audio transcripts from the ivrit.ai dataset.

## Overview

ivrit.ai Explore allows users to search through transcribed Hebrew audio content with advanced search capabilities including regex and substring matching. The application provides an intuitive interface for exploring search results, listening to audio segments, and exporting data.

## Features

- Full-text search with support for:
  - Regular expressions
  - Substring matching
  - Word boundary matching
- Audio playback of search results
- CSV export of search results

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/ivrit-ai/ivrit-explore.git
   cd ivrit-explore
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Start the application:
   ```
   python run.py
   ```

2. Open a browser and navigate to `http://localhost:5000`

3. Place your data files in the appropriate directories:
   - JSON transcripts: `data/json/`
   - Audio files: `data/audio/`

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
