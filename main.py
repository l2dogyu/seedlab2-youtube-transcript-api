from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import json
import re

app = FastAPI()

SCRAPERAPI_KEY = "f70288fff3436aca9b43f553e6676805"  # 예: abc123xyz456

@app.get("/transcript")
def get_transcript(videoId: str = Query(...)):
    try:
        youtube_url = f"https://www.youtube.com/watch?v={videoId}&gl=KR&hl=ko"
        proxy_url = f"https://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url={youtube_url}"
        headers = {
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8"
        }

        html = requests.get(proxy_url, headers=headers).text

        if "captionTracks" not in html:
            return {"error": "No captions found or blocked."}

        match = re.search(r'"captionTracks":(\[.*?\])', html)
        if not match:
            return {"error": "Failed to parse captionTracks"}

        tracks = json.loads(match.group(1))

        # 자막 URL 찾기
        en_url = None
        ko_url = None
        for track in tracks:
            lang = track.get("languageCode")
            if lang == "en" and not en_url:
                en_url = track.get("baseUrl")
            elif lang == "ko" and not ko_url:
                ko_url = track.get("baseUrl")

        if not en_url and not ko_url:
            return {"error": "No English or Korean subtitles available."}

        result = {}

        if en_url:
            en_resp = requests.get(en_url)
            try:
                en_json = en_resp.json()
                result["en"] = [
                    seg["text"]
                    for event in en_json.get("events", [])
                    if "segs" in event
                    for seg in event["segs"]
                ]
            except Exception as e:
                result["en_error"] = f"Failed to parse English subtitles: {str(e)}"

        if ko_url:
            ko_resp = requests.get(ko_url)
            try:
                ko_json = ko_resp.json()
                result["ko"] = [
                    seg["text"]
                    for event in ko_json.get("events", [])
                    if "segs" in event
                    for seg in event["segs"]
                ]
            except Exception as e:
                result["ko_error"] = f"Failed to parse Korean subtitles: {str(e)}"

        return {"transcript": result}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
