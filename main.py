# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import assemblyai as aai
import os
from dotenv import load_dotenv # Make sure this is imported
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, create_engine, Session, select


app = FastAPI(
    title="Speech-to-Text Microservice",
    description="A FastAPI service to transcribe audio and manage transcripts.",
    version="0.1.0"
)
origins = [
    "http://localhost",
    "http://localhost:3000", # Your React app's address
    # Add your hosted frontend URL here when you deploy!
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)
# --- Configuration ---
# It's crucial for load_dotenv() to be called early to load your .env file
load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if not ASSEMBLYAI_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY environment variable not set. Please check your .env file.")
aai.settings.api_key = ASSEMBLYAI_API_KEY

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # This error should halt startup if DATABASE_URL is missing
    raise ValueError("DATABASE_URL environment variable not set. Please check your .env file and ensure PostgreSQL is running.")

# Create the SQLAlchemy engine here
# echo=True is very helpful for debugging SQL issues by printing queries
engine = create_engine(DATABASE_URL, echo=True)

# --- SQLModel Database Table Definition ---
class Transcript(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    transcript_text: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# --- Pydantic Models for API Response ---
class TranscriptResponse(BaseModel):
    text: str
    status: str
    transcript_id: int # Ensure this is present and correct type

# --- Database Initialization Function ---
def create_db_and_tables():
    """Attempts to create database tables based on SQLModel metadata."""
    print("Attempting to create/verify database tables...") # Added for clarity
    try:
        SQLModel.metadata.create_all(engine)
        print("Database tables created/checked successfully.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify database tables: {e}")
        # Optionally re-raise the exception if you want startup to fail
        # raise

# --- Dependency for database session ---
def get_session():
    """Yields a database session, ensuring it's closed afterwards."""
    with Session(engine) as session:
        yield session


# --- Event Handlers (run on app startup) ---
@app.on_event("startup") # This decorator registers the function to run at startup
def on_startup():
    """Handler function to run when the application starts."""
    create_db_and_tables() # Call the function to create/verify tables

# --- Endpoints ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Speech-to-Text Microservice!"}

@app.post("/transcribe/", response_model=TranscriptResponse)
async def transcribe_audio(audio_file: UploadFile = File(...), session: Session = Depends(get_session)):
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY."
        )

    file_location = f"temp_{audio_file.filename}"
    transcript_id = None

    try:
        with open(file_location, "wb+") as file_object:
            file_object.write(await audio_file.read())

        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(language_code="en_us")
        transcript_result = transcriber.transcribe(file_location, config)

        os.remove(file_location) # Clean up the temporary file

        transcript_text_to_save = ""
        status_to_save = ""

        if transcript_result.status == aai.TranscriptStatus.completed:
            transcript_text_to_save = transcript_result.text
            status_to_save = "completed"
        else:
            transcript_text_to_save = transcript_result.error or "Transcription failed"
            status_to_save = transcript_result.status.value if transcript_result.status else "failed"

        # Create and save transcript to database
        db_transcript = Transcript(
            filename=audio_file.filename,
            transcript_text=transcript_text_to_save,
            status=status_to_save
        )
        session.add(db_transcript)
        session.commit()
        session.refresh(db_transcript) # IMPORTANT: Populates db_transcript.id from DB
        transcript_id = db_transcript.id

        # Debug prints:
        print(f"DEBUG: Saved transcript with ID: {transcript_id}")
        print(f"DEBUG: Transcript content: {transcript_text_to_save}")

        if transcript_result.status == aai.TranscriptStatus.completed:
            return TranscriptResponse(
                text=transcript_text_to_save,
                status="completed",
                transcript_id=transcript_id
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {transcript_text_to_save}"
            )
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        print(f"ERROR: An unexpected error occurred during transcription: {e}") # Log the actual error
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

@app.get("/transcripts/", response_model=List[Transcript])
async def get_all_transcripts(session: Session = Depends(get_session)):
    transcripts = session.exec(select(Transcript)).all()
    return transcripts

@app.get("/transcripts/{transcript_id}", response_model=Transcript)
async def get_transcript_by_id(transcript_id: int, session: Session = Depends(get_session)):
    transcript = session.get(Transcript, transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)