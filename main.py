# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import assemblyai as aai
import os
from dotenv import load_dotenv
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, create_engine, Session, select
from pydantic import BaseModel 
from textblob import TextBlob 

load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if not ASSEMBLYAI_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY environment variable not set. Please check your .env file.")
aai.settings.api_key = ASSEMBLYAI_API_KEY

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set. Please check your .env file and ensure PostgreSQL is running.")


engine = create_engine(DATABASE_URL, echo=True)


class Transcript(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    transcript_text: str
    status: str
    sentiment: Optional[str] = None 
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class TranscriptResponse(BaseModel): 
    text: str
    status: str
    transcript_id: int
    sentiment: Optional[str] = None 


def create_db_and_tables():
    """Attempts to create database tables based on SQLModel metadata."""
    print("Attempting to create/verify database tables...")
    try:
        SQLModel.metadata.create_all(engine)
        print("Database tables created/checked successfully.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify database tables: {e}")


def get_session():
    """Yields a database session, ensuring it's closed afterwards."""
    with Session(engine) as session:
        yield session

app = FastAPI(
    title="Speech-to-Text Microservice",
    description="A FastAPI service to transcribe audio and manage transcripts.",
    version="0.1.0"
)


origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://karim-speech-frontend.onrender.com", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)


@app.on_event("startup")
def on_startup():
    """Handler function to run when the application starts."""
    create_db_and_tables()


def analyze_sentiment(text: str) -> str:
    """Analyzes the sentiment of a given text."""
    if not text:
        return "N/A"
    blob = TextBlob(text)
    if blob.polarity > 0.1: 
        return "Positive"
    elif blob.polarity < -0.1:
        return "Negative"
    else:
        return "Neutral"


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
    analyzed_sentiment = None 

    try:
        with open(file_location, "wb+") as file_object:
            file_object.write(await audio_file.read())

        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(language_code="en_us")
        transcript_result = transcriber.transcribe(file_location, config)

        os.remove(file_location) 

        transcript_text_to_save = ""
        status_to_save = ""

        if transcript_result.status == aai.TranscriptStatus.completed:
            transcript_text_to_save = transcript_result.text
            status_to_save = "completed"
            analyzed_sentiment = analyze_sentiment(transcript_text_to_save) 
        else:
            transcript_text_to_save = transcript_result.error or "Transcription failed"
            status_to_save = transcript_result.status.value if transcript_result.status else "failed"
            analyzed_sentiment = "N/A"

        
        db_transcript = Transcript(
            filename=audio_file.filename,
            transcript_text=transcript_text_to_save,
            status=status_to_save,
            sentiment=analyzed_sentiment 
        )
        session.add(db_transcript)
        session.commit()
        session.refresh(db_transcript)
        transcript_id = db_transcript.id

        print(f"DEBUG: Saved transcript with ID: {transcript_id}, Sentiment: {analyzed_sentiment}")
        print(f"DEBUG: Transcript content: {transcript_text_to_save}")

        if transcript_result.status == aai.TranscriptStatus.completed:
            return TranscriptResponse(
                text=transcript_text_to_save,
                status="completed",
                transcript_id=transcript_id,
                sentiment=analyzed_sentiment 
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {transcript_text_to_save}"
            )
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        print(f"ERROR: An unexpected error occurred during transcription: {e}")
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