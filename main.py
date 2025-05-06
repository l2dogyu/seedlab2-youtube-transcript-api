from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import re
from typing import Optional

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 여기에 Google API 키를 입력하세요
GOOGLE_API_KEY = "YOUR_API_KEY_HERE"

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
                "comments": comments
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
