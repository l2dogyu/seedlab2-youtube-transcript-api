from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
import re

app = FastAPI()

# CORS 설정 (모든 출처 허용)
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
        # URL에서 video_id 추출 (URL이 입력된 경우)
        if "youtube.com" in video_id or "youtu.be" in video_id:
            pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
            match = re.search(pattern, video_id)
            if match:
                video_id = match.group(1)
        
        # ID 길이 확인
        if len(video_id) != 11:
            raise HTTPException(status_code=400, detail="올바른 YouTube 영상 ID가 아닙니다.")
            
        # 자막 가져오기
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        
        # 전체 텍스트 결합
        full_text = " ".join([entry['text'] for entry in transcript])
        
        return {
            "video_id": video_id,
            "transcript": transcript,
            "full_text": full_text
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# 로컬 테스트용
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
