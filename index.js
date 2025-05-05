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
    const captionMatch = content.match(/"captionTracks":(\[.*?\])/);

    if (!captionMatch) {
      await browser.close();
      return res.status(404).json({ error: "No captionTracks found" });
    }

    const tracks = JSON.parse(captionMatch[1]);
    let transcriptUrl = null;

    for (const track of tracks) {
      if (track.languageCode === "ko") {
        transcriptUrl = track.baseUrl;
        break;
      }
    }

    if (!transcriptUrl && tracks.length > 0) {
      transcriptUrl = tracks[0].baseUrl;
    }

    if (!transcriptUrl) {
      await browser.close();
      return res.status(404).json({ error: "Transcript URL not found" });
    }

    const transcriptRes = await page.goto(transcriptUrl);
    const transcriptText = await transcriptRes.text();
    const transcriptJson = JSON.parse(transcriptText);

    const transcript = transcriptJson.events
      .filter((e) => e.segs)
      .map((e) => e.segs.map((s) => s.text).join(""))
      .join(" ");

    await browser.close();
    return res.json({ transcript });

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server started on port ${PORT}`));
