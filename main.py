from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import re
import os
from typing import Optional
from bs4 import BeautifulSoup
import urllib.parse

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

def extract_urls_from_text(text: str) -> list:
    """텍스트에서 URL 추출"""
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    return re.findall(url_pattern, text)

async def get_transcript_from_url(url: str) -> str:
    """URL에서 트랜스크립트 내용 가져오기"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
                
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 텍스트 추출 (스탠포드 대학 페이지 구조에 맞게 조정)
            transcript = ""
            content_div = soup.find('div', {'id': 'content-body'})
            if content_div:
                # 단락 단위로 텍스트 추출
                paragraphs = content_div.find_all('p')
                for p in paragraphs:
                    transcript += p.get_text() + "\n\n"
            
            return transcript.strip() if transcript else None
    except Exception as e:
        print(f"URL 내용 가져오기 오류: {str(e)}")
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
            description = video["snippet"]["description"]
            
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
            
            # 설명에서 URL 추출 및 트랜스크립트 가져오기 시도
            transcript_text = ""
            urls = extract_urls_from_text(description)
            
            for url in urls:
                # 가능한 트랜스크립트 URL 패턴
                if "transcript" in url.lower() or "text" in url.lower():
                    transcript_content = await get_transcript_from_url(url)
                    if transcript_content:
                        transcript_text = transcript_content
                        break
            
            # 스티브 잡스 연설 특별 케이스 (특정 URL 확인)
            if video_id == "UF8uR6Z6KLc" and not transcript_text:
                stanford_url = "http://news-service.stanford.edu/news/2005/june15/jobs-061505.html"
                transcript_text = await get_transcript_from_url(stanford_url)
            
            # 리턴할 정보 구성
            return {
                "video_id": video_id,
                "title": video["snippet"]["title"],
                "description": description,
                "publishedAt": video["snippet"]["publishedAt"],
                "channelTitle": video["snippet"]["channelTitle"],
                "viewCount": video["statistics"].get("viewCount", "0"),
                "likeCount": video["statistics"].get("likeCount", "0"),
                "commentCount": video["statistics"].get("commentCount", "0"),
                "comments": comments,
                "transcript": transcript_text,
                "has_transcript": bool(transcript_text),
                "transcript_source": "external_url" if transcript_text else "none"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
