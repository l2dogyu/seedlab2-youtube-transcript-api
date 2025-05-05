from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import json
import re

app = FastAPI()

SCRAPERAPI_KEY = "f70288fff3436aca9b43f553e6676805"  # ← 여기에 실제 키 입력

@app.get("/transcript")
def get_transcript(videoId: str = Query(...)):
    try:
        # 1. 유튜브 URL에 언어 설정 추가
        youtube_url = f"https://www.youtube.com/watch?v={videoId}&gl=US&hl=en"
        proxy_url = f"https://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url={youtube_url}"

        # 2. 헤더 설정
        headers = {
            "Accept-Language": "en-US,en;q=0.9"
        }

        # 3. 유튜브 페이지 요청
        html = requests.get(proxy_url, headers=headers).text

        if "captionTracks" not in html:
            return {"error": "No captions found or request blocked by YouTube."}

        match = re.search(r'"captionTracks":(\[.*?\])', html)
        if not match:
            return {"error": "Failed to locate captionTracks in YouTube HTML."}

        tracks = json.loads(match.group(1))
        transcript_url = tracks[0].get("baseUrl")
        if not transcript_url:
            return {"error": "No baseUrl found for transcript."}

        resp = requests.get(transcript_url)
        if resp.status_code != 200:
            return {"error": f"Transcript URL failed: {resp.status_code}"}

        transcript_json = resp.json()

        transcript_text = ' '.join([
            seg["text"]
            for event in transcript_json.get("events", [])
            if "segs" in event
            for seg in event["segs"]
        ])

        return {"transcript": transcript_text}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
