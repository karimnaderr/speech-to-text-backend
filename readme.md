# [Your Project Name] - Speech-to-Text Backend

---

## Project Description

This is the backend API for a Speech-to-Text application. It leverages the FastAPI framework to expose endpoints for transcribing audio files using the AssemblyAI API and performing sentiment analysis on the transcribed text using TextBlob. All transcriptions and their associated metadata are stored in a PostgreSQL database.

## Features

- **Audio Transcription:** Converts spoken audio into written text using AssemblyAI.
- **Sentiment Analysis:** Analyzes the transcribed text to determine its sentiment (Positive, Negative, Neutral, or N/A).
- **Transcript Management:** Stores transcription details (filename, text, status, sentiment, timestamp) in a PostgreSQL database.
- **RESTful API:** Provides clear API endpoints for easy integration with frontend applications.

## Technologies Used

- **Backend Framework:** FastAPI
- **Database ORM:** SQLModel
- **Database:** PostgreSQL
- **Speech-to-Text API:** AssemblyAI
- **Sentiment Analysis:** TextBlob
- **ASGI Server:** Gunicorn (for production)
- **Environment Variables:** `python-dotenv`

## Local Setup & Installation

Follow these steps to get the backend running on your local machine.

### Prerequisites

- Python 3.9+
- Git
- PostgreSQL installed and running locally
- An AssemblyAI API Key (get one from [AssemblyAI](https://www.assemblyai.com/))

### Steps

1.  **Clone the repository:**

    ```bash
    git clone [Your Backend GitHub Repo URL]
    cd speech-to-text
    ```

2.  **Create and activate a Python virtual environment:**

    ```bash
    python -m venv venv
    venv\Scripts\activate  # On Windows
    # source venv/bin/activate  # On macOS/Linux
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    If `requirements.txt` is missing or incomplete, ensure `venv` is active and run:

    ```bash
    pip install fastapi uvicorn sqlmodel assemblyai python-dotenv textblob gunicorn psycopg2-binary
    pip freeze > requirements.txt
    ```

4.  **Set up environment variables:**
    Create a file named `.env` in the root of the `speech-to-text` directory and add your API keys and database URL:

    ```dotenv
    ASSEMBLYAI_API_KEY="YOUR_ASSEMBLYAI_API_KEY_HERE"
    DATABASE_URL="postgresql://user:password@host:port/database_name"
    # Example local PostgreSQL: DATABASE_URL="postgresql://postgres:your_db_password@localhost:5432/speech_to_text_db"
    ```

5.  **Database Setup:**
    Ensure your PostgreSQL server is running. The application will automatically create the `transcript` table on its first run if it doesn't exist. If you made schema changes, you might need to drop and recreate the table manually in pgAdmin.

6.  **Run the application:**
    ```bash
    uvicorn main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

- **`GET /`**: Welcome message.
- **`POST /transcribe/`**: Uploads an audio file for transcription and sentiment analysis.
  - **Method:** `POST`
  - **Body:** `audio_file` (File)
  - **Returns:** `{"text": "...", "status": "completed", "transcript_id": ..., "sentiment": "..."}`
- **`GET /transcripts/`**: Retrieves a list of all stored transcripts.
- **`GET /transcripts/{transcript_id}`**: Retrieves a specific transcript by ID.

## Deployment

This backend is designed to be deployed on platforms like **Render.com** (as a Web Service with a Render PostgreSQL database) or Heroku. Refer to the deployment guide for specific instructions.

---
