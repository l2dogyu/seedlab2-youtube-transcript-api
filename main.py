from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import json
import re

app = FastAPI()

SCRAPERAPI_KEY = "f70288fff3436aca9b43f553e6676805"  # ← 여기에 본인의 키 입력

@app.get("/transcript")
def get_transcript(videoId: str = Query(...)):
    try:
        youtube_url = f"https://www.youtube.com/watch?v={videoId}"
        proxy_url = f"https://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url={youtube_url}"

        html = requests.get(proxy_url).text

        # 자막 JSON URL 추출
        match = re.search(r'"captionTracks":(\[.*?\])', html)
        if not match:
            return JSONResponse(status_code=404, content={"error": "No transcript found."})

        tracks = json.loads(match.group(1))
        transcript_url = tracks[0]["baseUrl"]

        # 자막 JSON 가져오기
        transcript_json = requests.get(transcript_url).json()
        transcript_text = ' '.join([item["text"] for item in transcript_json["events"] if "segs" in item for seg in item["segs"]])

        return {"transcript": transcript_text}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
