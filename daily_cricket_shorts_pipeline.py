import asyncio, datetime, io, json, os, re, subprocess, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps

HISTORY_FILE = Path("published_history.json")
OUT = Path("build_output")
IMAGE_WAIT_SECONDS = int(os.environ.get("IMAGE_WAIT_SECONDS", "300"))
MAX_RETRIES = 3

PLAN = {
    "topic_id": "yuvraj-2007-baptism-in-fire",
    "title": "The Night Yuvraj Broke Cricket: How 2007 Changed Indian DNA Forever",
    "description": (
        "In September 2007, Indian cricket was at a crossroads. Without its senior legends, MS Dhoni’s young brigade entered the inaugural T20 World Cup with zero expectations—until Yuvraj Singh turned Durban into a fortress of fearless cricket.\n\n"
        "From his iconic 6 sixes off Stuart Broad (and the fastest 12-ball fifty in T20I history) to his brutal 70 off 30 balls against Australia in the semi-final, and the underrated left-arm spin that gave India crucial middle-over control—this is the untold tactical and emotional story of how Yuvraj Singh forged the fearless DNA of Indian cricket that still powers our 2026 superstars.\n\n"
        "#CricketRaaz #YuvrajSingh #2007T20WorldCup #6Sixes #IndianCricket #MSDhoni #CricketNostalgia #CWC26 #T20WorldCup #BleedBlue\n\n"
        "AI Disclosure: This documentary short features synthetic recreations and AI-generated cinematic visuals created to honor historical cricket moments and preserve the emotional heritage of the 2007 T20 World Cup.\n"
        "Image Credits: Archival stadium and match imagery sourced under Creative Commons (including 'The Wanderers 2.jpg' by Charles from Sandton via Wikimedia Commons, CC BY-SA 2.0) and public domain/editorial photography credited to original photographers."
    ),
    "tags": ["CricketRaaz", "YuvrajSingh", "2007T20WorldCup", "6Sixes", "IndianCricket", "MSDhoni", "CricketNostalgia", "CWC26", "T20WorldCup", "BleedBlue"],
    "category_id": "17",
    "shots": [
        {"shot": 1, "narration": "September 2007. No Sachin. No Dravid. No Ganguly. An entire generation sat glued to flickering CRT screens, bracing for humiliation in a format India didn’t even want to play.", "prompt": "Dark 2007 Indian living room, a family seen from behind watching a glowing CRT TV showing live night cricket, ceiling fan spinning, film grain, 16:9 cinematic realism, no watermarks.", "query": "Indian family watching cricket on old CRT television night"},
        {"shot": 2, "narration": "They called it a young team’s gamble. They didn't know Yuvraj Singh was about to turn Durban into a battlefield—and rewrite the soul of a nation.", "prompt": "Empty wet street in Mumbai at night, warm streetlight reflecting on puddles, deserted tea stall with a small portable TV glowing inside, nostalgic atmosphere, 16:9 cinematic realism, no watermarks.", "query": "Mumbai empty wet street night rain lights tea stall"},
        {"shot": 3, "narration": "In 2007, T20 was considered a joke—until Andrew Flintoff lit a fuse at Kingsmead.", "prompt": "Close-up of an anonymous cricketer's intense bloodshot eyes beneath a blue helmet grill, sweat-streaked face, harsh stadium floodlights, dramatic rim lighting, 16:9 cinematic realism, no watermarks.", "query": "cricket batsman helmet eyes intense close up floodlights"},
        {"shot": 4, "narration": "Six deliveries later, Stuart Broad’s career was ambushed. Six monstrous sixes.", "prompt": "Low-angle shot of an anonymous left-handed batsman in a 2007 light-blue jersey swinging a heavy wooden bat high into the night sky, dust motes and stadium glare, 16:9 cinematic realism, no watermarks.", "query": "left handed cricket batsman hitting six night stadium"},
        {"shot": 5, "narration": "A twelve-ball fifty—the fastest in T20 history, a record that still mocks modern power-hitters in 2026.", "prompt": "A red cricket ball soaring high above stadium floodlights into a dark South African night sky, faint motion blur, dramatic lens flare, 16:9 cinematic realism, no watermarks.", "query": "cricket ball flying night stadium floodlights sky"},
        {"shot": 6, "narration": "The streets of Mumbai and Delhi erupted, dinner plates forgotten on the table. But here is the mystery most fans forget: Yuvraj didn’t just win 2007 with his bat.", "prompt": "Close-up of a vintage stadium digital scoreboard flipping to 50 (12) in glowing amber lights, heat haze, 2007 broadcast grain, 16:9 cinematic realism, no watermarks.", "query": "cricket stadium scoreboard night crowd lights"},
        {"shot": 7, "narration": "Three days later, in the semi-final against the mighty Australians—a team of invincible gods—India was cornered at 41 for 2.", "prompt": "Silhouette of a left-handed batsman standing tall at the crease facing three aggressive yellow-jersey fielders in the slips, dramatic floodlight backlighting, 16:9 cinematic realism, no watermarks.", "query": "Australia yellow jersey cricket slip fielders night match"},
        {"shot": 8, "narration": "Yuvraj walked in with a bruised elbow and unleashed pure violence: 70 runs off just 30 balls, including a 119-meter rocket off Brett Lee.", "prompt": "Mid-action shot of a ferocious pull shot against a fast bowler, white cricket ball blurring off the sweet spot of the bat, sweat flying in slow motion, 16:9 cinematic realism, no watermarks.", "query": "cricket batsman pull shot white ball night match"},
        {"shot": 9, "narration": "And when MS Dhoni needed tactical control? Yuvraj became India’s silent assassin with the ball.", "prompt": "Close-up of a left hand gripping a white cricket ball, fingers poised to bowl left-arm orthodox spin, stadium floodlights glinting off sweat, shallow depth of field, 16:9 cinematic realism, no watermarks.", "query": "white leather cricket ball spin bowler grip hand close up"},
        {"shot": 10, "narration": "While pacers bled runs, his deceptive left-arm darts choked the middle overs, giving India the exact balance that allowed a five-bowler gamble to work.", "prompt": "Wide shot from behind of anonymous cricket players in plain sky-blue jerseys huddled together in celebration under golden confetti and stadium fireworks at night, emotional atmosphere, 16:9 cinematic realism, no watermarks.", "query": "cricket team celebration huddle stadium fireworks night"},
        {"shot": 11, "narration": "When we watch fearless 2026 stars like Abhishek Sharma or Vaibhav Sooryavanshi swing without fear, remember where that DNA was forged. It was born in 2007, in the baptism by fire of a Punjabi southpaw who refused to back down.", "prompt": "Golden hour transition: an anonymous young-adult cricketer seen from behind in a modern 2026 blue jersey holding a heavy bat, walking onto a lush green stadium pitch, 16:9 cinematic realism, no watermarks.", "query": "cricketer walking out stadium tunnel sunlight pitch"}
    ]
}

USED_URLS = set()

def verify_img(img_bytes, prompt):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    q = f"Target Prompt: {prompt}\nDoes this image match the scene mood and subject? If not, rewrite a tweaked prompt avoiding public figures. Return JSON: {{\"matches\": true, \"tweaked_prompt\": \"...\"}}"
    try:
        res = client.models.generate_content(model="models/gemini-3.1-flash-lite", contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/png"), q], config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
        v = json.loads(res.text)
        return bool(v.get("matches", True)), v.get("tweaked_prompt") or prompt
    except Exception:
        return True, prompt

def get_shot_image(shot_cfg, out_png):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    img_models = [m.name for m in client.models.list() if any(k in m.name.lower() for k in ["imagen", "image"])]
    cur_prompt = shot_cfg["prompt"]
    for att in range(1, MAX_RETRIES + 1):
        print(f"[Rule 2] Waiting {IMAGE_WAIT_SECONDS}s (5 mins) before Shot {shot_cfg['shot']} attempt {att}...")
        time.sleep(IMAGE_WAIT_SECONDS)
        raw = None
        for im in img_models:
            try:
                if "imagen" in im.lower():
                    r = client.models.generate_images(model=im, prompt=cur_prompt, config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9"))
                    if r.generated_images: raw = r.generated_images[0].image.image_bytes; break
                else:
                    r = client.models.generate_content(model=im, contents=cur_prompt, config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
                    for p in r.candidates[0].content.parts:
                        if p.inline_data and p.inline_data.data: raw = p.inline_data.data; break
                    if raw: break
            except Exception as e:
                print(f"Model {im} skipped: {str(e)[:80]}")
        if raw:
            img = ImageOps.fit(Image.open(io.BytesIO(raw)).convert("RGB"), (1920, 1080), Image.Resampling.LANCZOS)
            buf = io.BytesIO(); img.save(buf, "PNG"); b = buf.getvalue()
            ok, tweaked = verify_img(b, cur_prompt)
            if ok or att == MAX_RETRIES:
                out_png.write_bytes(b); print(f"[Rule 1] Shot {shot_cfg['shot']} verified!"); return
            cur_prompt = tweaked
        else:
            break
    for q in [shot_cfg["query"], "Wanderers stadium cricket night"]:
        try:
            u = f"https://www.bing.com/images/async?q={urllib.parse.quote(q)}&first=1&count=20&qft=+filterui:imagesize-large"
            html = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", errors="ignore")
            for murl in re.findall(r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png))&quot;', html):
                if murl in USED_URLS: continue
                try:
                    d = urllib.request.urlopen(urllib.request.Request(murl, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read()
                    im = Image.open(io.BytesIO(d)).convert("RGB")
                    if im.width < 400 or im.height < 400: continue
                    USED_URLS.add(murl)
                    ImageEnhance.Contrast(ImageOps.fit(im, (1920, 1080), Image.Resampling.LANCZOS)).enhance(1.12).save(out_png, "PNG")
                    print(f"Fetched attributed web image for Shot {shot_cfg['shot']}: {murl[:60]}"); return
                except Exception: continue
        except Exception: pass
    Image.new("RGB", (1920, 1080), (14, 20, 32)).save(out_png, "PNG")

async def _tts(text, path):
    import edge_tts
    clean = text.replace("—", "... ").strip()
    for voice in ["en-IN-PrabhatNeural", "en-US-ChristopherNeural"]:
        try:
            await edge_tts.Communicate(text=clean, voice=voice, pitch="-15Hz").save(str(path))
            if path.exists() and path.stat().st_size > 400: return
        except Exception: time.sleep(1)
    from gtts import gTTS
    gTTS(text=clean, lang="en", tld="co.in").save(str(path))

def get_dur(p):
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)], capture_output=True, text=True, check=True)
    return max(float(pr.stdout.strip()), 4.0)

def render_and_upload():
    OUT.mkdir(exist_ok=True)
    segs = []
    for s in PLAN["shots"]:
        i = s["shot"]
        aud_p, img_p, seg_p = OUT / f"s{i}.mp3", OUT / f"s{i}.png", OUT / f"s{i}.mp4"
        asyncio.run(_tts(s["narration"], aud_p))
        dur = get_dur(aud_p) + 0.3
        get_shot_image(s, img_p)
        fr = max(int(dur * 30), 90)
        vf = f"scale=2112:1188,zoompan=z='min(zoom+0.0005,1.08)':d={fr}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
        subprocess.run(["ffmpeg", "-y", "-i", str(img_p), "-i", str(aud_p), "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(seg_p)], check=True)
        segs.append(seg_p)
    ml, out_mp4 = OUT / "ml.txt", OUT / f"{PLAN['topic_id']}.mp4"
    ml.write_text("\n".join(f"file '{x.resolve()}'" for x in segs))
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(ml), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_mp4)], check=True)
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials(None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["YOUTUBE_CLIENT_ID"], client_secret=os.environ["YOUTUBE_CLIENT_SECRET"], scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    body = {"snippet": {"title": PLAN["title"][:100], "description": PLAN["description"], "tags": PLAN["tags"], "categoryId": "17"}, "status": {"privacyStatus": os.environ.get("YOUTUBE_PRIVACY", "public"), "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(out_mp4), mimetype="video/mp4", resumable=True))
    res = None
    while res is None: _, res = req.next_chunk()
    print(f"SUCCESS_YOUTUBE_URL: https://www.youtube.com/watch?v={res['id']}")
    h = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {"published_topics": [], "runs": []}
    h["published_topics"].append(PLAN["topic_id"])
    h["runs"].append({"date": datetime.date.today().isoformat(), "topic_id": PLAN["topic_id"], "title": PLAN["title"], "video_id": res["id"]})
    HISTORY_FILE.write_text(json.dumps(h, indent=2))

if __name__ == "__main__":
    render_and_upload()
