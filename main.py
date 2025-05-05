from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import json
import re

app = FastAPI()

# 🔑 여기에 ScrapingBee API 키를 입력하세요
SCRAPINGBEE_KEY = "VXEIQ8X952V450QAU4OP3JLZO241KLU16CX79Y8RXAEZYK7WG47UBUG3UT49PN9VZQ2LS2DX58UQBUCM"

@app.get("/transcript")
def get_transcript(videoId: str = Query(..., description="YouTube video ID")):
    try:
        youtube_url = f"https://www.youtube.com/watch?v={videoId}&gl=KR&hl=ko"
        proxy_url = "https://app.scrapingbee.com/api/v1"
        params = {
            "api_key": SCRAPINGBEE_KEY,
            "url": youtube_url,
            "render_js": "true",  # 자막 포함된 HTML 로딩 위해 필수
            "block_resources": "false",
            "country_code": "kr"
        }

        headers = {
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        # 1. 유튜브 HTML 가져오기
        response = requests.get(proxy_url, params=params, headers=headers)
        html = response.text

        if "captionTracks" not in html:
            return {"error": "No captions found in HTML or request was blocked."}

        # 2. captionTracks JSON 추출
        match = re.search(r'"captionTracks":(\[.*?\])', html)
        if not match:
            return {"error": "Failed to parse captionTracks JSON block."}

        tracks = json.loads(match.group(1))

        # 3. 언어 우선순위: ko > en > 기타
        transcript_url = None
        for lang_code in ["ko", "en"]:
            for track in tracks:
                if track.get("languageCode") == lang_code:
                    transcript_url = track.get("baseUrl")
                    break
            if transcript_url:
                break

        if not transcript_url:
            transcript_url = tracks[0].get("baseUrl")

        if not transcript_url:
            return {"error": "Transcript URL not found in captionTracks."}

        # 4. 자막 JSON 요청
        transcript_resp = requests.get(transcript_url)
        transcript_json = transcript_resp.json()

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
