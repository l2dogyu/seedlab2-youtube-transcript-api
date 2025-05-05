from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import json
import re

app = FastAPI()

# ✅ 여기에 본인의 ScraperAPI 키를 입력하세요
SCRAPERAPI_KEY = "f70288fff3436aca9b43f553e6676805"

@app.get("/transcript")
def get_transcript(videoId: str = Query(..., description="YouTube video ID")):
    try:
        # 1. ScraperAPI를 통해 유튜브 페이지 요청
        youtube_url = f"https://www.youtube.com/watch?v={videoId}"
        proxy_url = f"https://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url={youtube_url}"

        html = requests.get(proxy_url).text

        # 2. 자막 정보 JSON이 포함되어 있는지 확인
        if "captionTracks" not in html:
            return {"error": "No captions found or request blocked by YouTube."}

        # 3. 자막 JSON 추출
        match = re.search(r'"captionTracks":(\[.*?\])', html)
        if not match:
            return {"error": "Failed to locate captionTracks in YouTube HTML."}

        tracks = json.loads(match.group(1))
        transcript_url = tracks[0].get("baseUrl")
        if not transcript_url:
            return {"error": "No baseUrl found for transcript."}

        # 4. 자막 JSON 요청
        resp = requests.get(transcript_url)
        if resp.status_code != 200:
            return {"error": f"Transcript URL request failed with status code {resp.status_code}"}

        try:
            transcript_json = resp.json()
        except Exception as e:
            return {"error": f"Failed to parse transcript JSON: {str(e)}"}

        # 5. 자막 텍스트 조합
        transcript_text = ' '.join([
            seg["text"]
            for event in transcript_json.get("events", [])
            if "segs" in event
            for seg in event["segs"]
        ])

        return {"transcript": transcript_text}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
