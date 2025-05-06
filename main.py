from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import re
import os
from typing import Optional
import subprocess
import json
import tempfile
import uuid

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경 변수에서 API 키 가져오기
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyCe1GYdWRnDUBPikMy0aajvZju9kCoKhMk")

@app.get("/")
async def root():
    return {"message": "YouTube API 서버가 실행 중입니다."}

def extract_video_id(url_or_id: str) -> str:
    """YouTube URL 또는 ID에서 영상 ID를 추출"""
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id

async def get_transcript_yt_dlp(video_id: str):
    """yt-dlp를 사용하여 자막 추출 - 더 강력한 방법"""
    temp_dir = tempfile.gettempdir()
    output_file = os.path.join(temp_dir, f"subtitles_{uuid.uuid4().hex}.vtt")
    
    try:
        # 자막 다운로드 시도 (자동 생성 자막 포함)
        cmd = [
            "yt-dlp", 
            f"https://www.youtube.com/watch?v={video_id}", 
            "--skip-download", 
            "--write-auto-sub",
            "--sub-format", "vtt",
            "--sub-langs", "en,ko",
            "-o", f"{output_file}"
        ]
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        # 자막 파일 찾기
        subtitle_file = None
        for file in os.listdir(temp_dir):
            if file.startswith(f"subtitles_{uuid.uuid4().hex}") and file.endswith(".vtt"):
                subtitle_file = os.path.join(temp_dir, file)
                break
        
        if subtitle_file and os.path.exists(subtitle_file):
            # VTT 파일 읽기 및 텍스트 추출
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # VTT 파싱 (간단 버전)
            lines = content.split('\n')
            transcript_text = ""
            for line in lines:
                # 타임스탬프와 태그 제외, 텍스트만 추출
                if '-->' not in line and not line.startswith('WEBVTT') and line.strip():
                    transcript_text += line.strip() + " "
            
            # 정리 후 파일 삭제
            os.remove(subtitle_file)
            
            return transcript_text.strip()
        else:
            return None
    except Exception as e:
        print(f"yt-dlp error: {str(e)}")
        return None

@app.get("/video/{video_id}")
async def get_video_info(video_id: str):
    """YouTube 영상 정보 가져오기"""
    try:
        # 영상 ID 추출
        video_id = extract_video_id(video_id)
        
        # YouTube Data API 호출
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,contentDetails,statistics",
                    "id": video_id,
                    "key": GOOGLE_API_KEY
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            data = response.json()
            
            if not data.get("items"):
                raise HTTPException(status_code=404, detail=f"영상을 찾을 수 없습니다: {video_id}")
            
            video = data["items"][0]
            
            # 댓글 정보 가져오기
            comments_response = await client.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": 50,
                    "order": "relevance",
                    "key": GOOGLE_API_KEY
                }
            )
            
            comments = []
            if comments_response.status_code == 200:
                comments_data = comments_response.json()
                comments = [
                    {
                        "text": item["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                        "likeCount": item["snippet"]["topLevelComment"]["snippet"]["likeCount"],
                        "authorDisplayName": item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"]
                    }
                    for item in comments_data.get("items", [])
                ]
            
            # 자막 가져오기 (개선된 방법)
            transcript_text = await get_transcript_yt_dlp(video_id)
            
            # 리턴할 정보 구성
            return {
                "video_id": video_id,
                "title": video["snippet"]["title"],
                "description": video["snippet"]["description"],
                "publishedAt": video["snippet"]["publishedAt"],
                "channelTitle": video["snippet"]["channelTitle"],
                "viewCount": video["statistics"].get("viewCount", "0"),
                "likeCount": video["statistics"].get("likeCount", "0"),
                "commentCount": video["statistics"].get("commentCount", "0"),
                "comments": comments,
                "transcript": transcript_text,
                "has_transcript": bool(transcript_text)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transcript/{video_id}")
async def get_only_transcript(video_id: str):
    """영상 자막만 가져오기"""
    try:
        video_id = extract_video_id(video_id)
        transcript_text = await get_transcript_yt_dlp(video_id)
        
        if not transcript_text:
            return {
                "video_id": video_id,
                "has_transcript": False,
                "message": "이 영상에는 자막이 없거나 접근할 수 없습니다."
            }
            
        return {
            "video_id": video_id,
            "has_transcript": True,
            "transcript": transcript_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/{query}")
async def search_videos(query: str, max_results: Optional[int] = 10):
    """YouTube 영상 검색"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": max_results,
                    "key": GOOGLE_API_KEY
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            data = response.json()
            
            results = [
                {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "publishedAt": item["snippet"]["publishedAt"],
                    "channelTitle": item["snippet"]["channelTitle"],
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"]
                }
                for item in data.get("items", [])
            ]
            
            return {"results": results}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
