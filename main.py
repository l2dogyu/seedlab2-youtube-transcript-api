from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "YouTube Transcript API 서버가 실행 중입니다."}

@app.get("/transcript/{video_id}")
async def get_transcript(video_id: str):
    try:
        # URL에서 video_id 추출
        if "youtube.com" in video_id or "youtu.be" in video_id:
            pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
            match = re.search(pattern, video_id)
            if match:
                video_id = match.group(1)
        
        # 다양한 언어로 시도 (언어 제한 없음)
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        except (TranscriptsDisabled, NoTranscriptFound):
            # 언어 지정 없이 모든 자막 가져오기 시도
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(['en', 'ko', 'ja', 'zh-CN', 'zh-TW']).fetch()
        
        # 전체 텍스트 결합
        full_text = " ".join([entry['text'] for entry in transcript])
        
        return {
            "video_id": video_id,
            "transcript": transcript,
            "full_text": full_text
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
