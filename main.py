from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

app = FastAPI()

@app.get("/transcript")
def get_transcript(videoId: str = Query(..., description="YouTube video ID")):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(videoId, languages=['ko', 'en'])
        full_text = ' '.join([entry['text'] for entry in transcript])
        return {"transcript": full_text}
    except TranscriptsDisabled:
        return JSONResponse(status_code=404, content={"error": "Transcript not available for this video"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})