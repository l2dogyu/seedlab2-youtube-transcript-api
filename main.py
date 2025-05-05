from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import json
import re

app = FastAPI()

SCRAPINGBEE_KEY = "VXEIQ8X952V450QAU4OP3JLZO241KLU16CX79Y8RXAEZYK7WG47UBUG3UT49PN9VZQ2LS2DX58UQBUCM"

@app.get("/transcript")
def get_transcript(videoId: str = Query(...)):
    try:
        youtube_url = f"https://www.youtube.com/watch?v={videoId}&gl=KR&hl=ko"
        proxy_url = f"https://app.scrapingbee.com/api/v1"
        params = {
            "api_key": SCRAPINGBEE_KEY,
            "url": youtube_url,
            "render_js": "false",
            "country_code": "kr"
        }

        headers = {
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8"
        }

        response = requests.get(proxy_url, params=params, headers=headers)
        html = response.text

        if "captionTracks" not in html:
            return {"error": "No captions found or blocked."}

        match = re.search(r'"captionTracks":(\[.*?\])', html)
        if not match:
            return {"error": "Failed to parse captionTracks."}

        tracks = json.loads(match.group(1))

        # 자막 찾기 (우선순위: ko > en)
        transcript_url = None
        for track in tracks:
            lang = track.get("languageCode")
            if lang == "ko":
                transcript_url = track.get("baseUrl")
                break
        if not transcript_url:
            transcript_url = tracks[0].get("baseUrl")

        if not transcript_url:
            return {"error": "Transcript URL not found."}

        transcript_resp = requests.get(transcript_url)
        transcript_json = transcript_resp.json()

        transcript_text = ' '.join([
            seg["text"]
            for event in transcript_json.get("events", [])
            if "segs" in event
            for seg in event["segs"]
        ])

        return {"transcript": transcript_text}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
