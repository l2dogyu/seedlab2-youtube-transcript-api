const express = require("express");
const puppeteer = require("puppeteer");
const cors = require("cors");

const app = express();
app.use(cors());

app.get("/transcript", async (req, res) => {
  const videoId = req.query.videoId;
  if (!videoId) return res.status(400).json({ error: "videoId is required" });

  const url = `https://www.youtube.com/watch?v=${videoId}`;

  try {
    const browser = await puppeteer.launch({
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
      headless: "new"
    });
    const page = await browser.newPage();
    await page.setExtraHTTPHeaders({
      "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8"
    });
    await page.goto(url, { waitUntil: "networkidle2" });

    const content = await page.content();

    const captionTracksMatch = content.match(/"captionTracks":(\[.*?\])/);
    if (!captionTracksMatch) {
      await browser.close();
      return res.status(404).json({ error: "No captionTracks found" });
    }

    const captionTracks = JSON.parse(captionTracksMatch[1]);

    // 한국어 우선, 없으면 영어
    let transcriptUrl = null;
    for (const track of captionTracks) {
      if (track.languageCode === "ko") {
        transcriptUrl = track.baseUrl;
        break;
      }
    }
    if (!transcriptUrl && captionTracks.length > 0) {
      transcriptUrl = captionTracks[0].baseUrl;
    }

    if (!transcriptUrl) {
      await browser.close();
      return res.status(404).json({ error: "No transcript URL found" });
    }

    const transcriptRes = await page.goto(transcriptUrl);
    const transcriptText = await transcriptRes.text();

    await browser.close();

    const transcriptData = JSON.parse(transcriptText);
    const transcript = transcriptData.events
      .filter((e) => e.segs)
      .map((e) => e.segs.map((s) => s.text).join(""))
      .join(" ");

    return res.json({ transcript });

  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
