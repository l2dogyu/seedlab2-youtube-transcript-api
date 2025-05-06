from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os
import tempfile
import re
import httpx
from typing import Optional, List, Dict, Any

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_video_id(url_or_id: str) -> str:
    """YouTube URL 또는 ID에서 영상 ID를 추출"""
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id

def get_subtitle_with_ytdlp(video_id: str) -> Dict[str, Any]:
    """yt-dlp를 사용하여 자막을 가져옴"""
    temp_dir = tempfile.mkdtemp()
    subtitle_path = os.path.join(temp_dir, "subtitle.vtt")
    
    try:
        # 1. 자막 목록 가져오기
        cmd = [
            "yt-dlp", 
            f"https://www.youtube.com/watch?v={video_id}", 
            "--list-subs", 
            "-j"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        
        video_info = json.loads(result.stdout)
        
        # 2. 자막 다운로드 (우선순위: 한국어 > 영어 > 자동생성 > 임의)
        languages = ["ko", "en", "ko-KR", "en-US", "en-GB", "auto"]
        subtitle_formats = ["vtt", "ttml", "srv3", "srv2", "srv1", "srt"]
        
        for lang in languages:
            for fmt in subtitle_formats:
                cmd = [
                    "yt-dlp", 
                    f"https://www.youtube.com/watch?v={video_id}", 
                    "--skip-download", 
                    f"--sub-lang={lang}", 
                    f"--sub-format={fmt}", 
                    "--write-sub", 
                    "--write-auto-sub",
                    "-o", os.path.join(temp_dir, "subtitle")
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # 자막 파일 찾기
                for file in os.listdir(temp_dir):
                    if file.endswith(f".{fmt}"):
                        # 파일 읽기
                        with open(os.path.join(temp_dir, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # VTT/SRT 파싱하여 텍스트만 추출
                        lines = content.split('\n')
                        transcript_text = ""
                        for line in lines:
                            # 시간 코드와 메타데이터 제외
                            if not re.match(r'\d+:\d+:\d+', line) and \
                               not re.match(r'\d+\s*$', line) and \
                               '-->' not in line and \
                               not line.startswith('WEBVTT') and \
                               line.strip():
                                transcript_text += line.strip() + " "
                        
                        return {
                            "success": True, 
                            "transcript": transcript_text.strip(),
                            "language": lang,
                            "format": fmt
                        }
        
        # 3. 대체 방법: 스크립트에서 텍스트 추출
        if video_info.get("description"):
            return {
                "success": True,
                "transcript": video_info.get("description"),
                "source": "description"
            }
        
        return {"success": False, "error": "자막을 찾을 수 없음"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        # 임시 파일 정리
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.get("/")
async def root():
    return {"message": "YouTube 자막 추출 API가 실행 중입니다."}

@app.get("/transcript/{video_id}")
async def get_transcript(video_id: str):
    """영상 자막 가져오기"""
    try:
        # 영상 ID 추출
        video_id = extract_video_id(video_id)
        
        # yt-dlp로 자막 추출
        result = get_subtitle_with_ytdlp(video_id)
        
        if not result["success"]:
            # 대체 방법: YouTube API로 영상 정보 가져오기
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://www.youtube.com/watch?v={video_id}",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                
                if response.status_code == 200:
                    # 페이지에서 자막 데이터 찾기 (고급 파싱 필요)
                    html = response.text
                    # 여기서 복잡한 HTML 파싱이 필요함
            
            return {
                "video_id": video_id,
                "has_transcript": False,
                "error": result.get("error", "자막을 찾을 수 없음"),
                "message": "영상에 접근 가능한 자막이 없습니다."
            }
            
        return {
            "video_id": video_id,
            "has_transcript": True,
            "transcript": result.get("transcript", ""),
            "language": result.get("language", "unknown"),
            "format": result.get("format", "unknown")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 서버 실행 (개발용)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
