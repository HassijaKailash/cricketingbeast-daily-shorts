import argparse, asyncio, datetime, io, json, os, re, subprocess, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps

CHANNEL_HANDLE = "@CricketingBeastHK"
HISTORY_FILE = Path("published_history.json")
OUT = Path("build_output")

PROMPT = """You are the documentary scriptwriter and visual director for the YouTube Shorts channel CricketingBeast (@CricketingBeastHK), modeled on "Why Australia Still Hates These 2 Legends 🤔😤🇦🇺".
Write a gripping 7-scene cricket documentary Short (70-85 seconds total) about an iconic cricket comeback, rivalry, or untold match story:
Scene 1: The Intimidating Opponent / Impossible Odds
Scene 2: The Collapse / Humiliation
Scene 3: The Captain's Gamble or Turning Point
Scene 4: The Opponent's Arrogance / Premature Celebration
Scene 5: Pure Defiance & Grit on the Pitch
Scene 6: Breaking the World-Class Attack
Scene 7: The Historic Finale & Immortal Legacy
For EVERY scene provide:
- narration: 2-3 dramatic documentary sentences for a deep narrator.
- image_prompts: EXACTLY 2 hyper-detailed 9:16 photorealistic image prompts per scene (14 images total, changing every ~5 seconds). End each prompt with "8K photorealistic, 70mm film grain, dramatic lighting, vertical 9:16".
- search_queries: EXACTLY 2 specific real-world photo search queries matching the 2 shots (e.g. "Rishabh Pant batting Gabba 2021 Test cricket HD", "Australia cricket bowlers exhausted Test match").
Return STRICT JSON:
{"topic_id":"slug","title":"High-CTR Title under 70 chars 🤔🔥🇮🇳 #Shorts","description":"3-paragraph story summary + 10 hashtags (#IndianCricket #CricketHistory #TestCricket #TeamIndia #CricketingBeast)","tags":["cricket","cricketshorts","indiancricket","cricketingbeast","cricketlegends"],"category_id":"17","scenes":[{"scene_number":1,"narration":"Spoken line","image_prompts":["Prompt 1","Prompt 2"],"search_queries":["Query 1","Query 2"]}]}"""

def load_history():
    if HISTORY_FILE.exists():
        try: return json.loads(HISTORY_FILE.read_text()).get("published_topics", [])
        except Exception: pass
    return ["eden-gardens-2001-laxman-dravid-kolkata-test"]

def save_history(topic_id, title, video_id):
    h = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {"published_topics": [], "runs": []}
    if topic_id not in h["published_topics"]: h["published_topics"].append(topic_id)
    h["runs"].append({"date": datetime.date.today().isoformat(), "topic_id": topic_id, "title": title, "video_id": video_id})
    HISTORY_FILE.write_text(json.dumps(h, indent=2))

def generate_plan(excluded):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    all_ex = list(set(excluded + ["eden-gardens-2001-laxman-dravid-kolkata-test"]))
    candidates = ["models/gemini-3.1-flash-lite"] + [m.name for m in client.models.list() if "gemini" in m.name.lower() and not any(x in m.name.lower() for x in ["embedding", "imagen", "veo", "tts", "audio", "vision", "image"])]
    for model_name in candidates:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=f"Create today's 7-scene Cricket Documentary Short for {CHANNEL_HANDLE}. Exclude: {all_ex[-40:]}.",
                config=types.GenerateContentConfig(system_instruction=PROMPT, response_mime_type="application/json", temperature=0.85),
            )
            plan = json.loads(res.text)
            if "scenes" in plan and len(plan["scenes"]) >= 5: return plan
        except Exception as e:
            print(f"Skipping {model_name}: {e}")
    raise RuntimeError("No compatible Gemini model succeeded")

USED_URLS = set()

def generate_image(prompt, search_query, out_png, seed):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    img_models = [m.name for m in client.models.list() if any(k in m.name.lower() for k in ["imagen", "image"])]
    for im in img_models:
        try:
            if "imagen" in im.lower():
                res = client.models.generate_images(model=im, prompt=prompt, config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="9:16"))
                if res.generated_images:
                    img = Image.open(io.BytesIO(res.generated_images[0].image.image_bytes)).convert("RGB")
                    ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS).save(out_png, "PNG")
                    print(f"Generated AI image with {im}")
                    return
            else:
                res = client.models.generate_content(model=im, contents=prompt, config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
                for part in res.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        img = Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                        ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS).save(out_png, "PNG")
                        print(f"Generated AI image with {im}")
                        return
        except Exception as e:
            print(f"AI image model {im} skipped: {str(e)[:90]}")

    for q in [search_query, f"{search_query} cricket match", "Test cricket stadium dramatic"]:
        try:
            url = f"https://www.bing.com/images/async?q={urllib.parse.quote(q)}&first=1&count=20&qft=+filterui:imagesize-large"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
            matches = re.findall(r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png))&quot;', html)
            for murl in matches:
                if murl in USED_URLS: continue
                try:
                    ireq = urllib.request.Request(murl, headers={"User-Agent": "Mozilla/5.0"})
                    data = urllib.request.urlopen(ireq, timeout=15).read()
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    if img.width < 400 or img.height < 400: continue
                    USED_URLS.add(murl)
                    fitted = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
                    fitted = ImageEnhance.Contrast(fitted).enhance(1.15)
                    fitted = ImageEnhance.Color(fitted).enhance(1.1)
                    fitted.save(out_png, "PNG")
                    print(f"Fetched high-res cricket image for '{q}': {murl[:65]}")
                    return
                except Exception:
                    continue
        except Exception as e:
            print(f"Search fallback error ({q}): {e}")
    Image.new("RGB", (1080, 1920), (14, 20, 32)).save(out_png, "PNG")

async def _tts(text, path, pitch=None, voice_only=None):
    import edge_tts
    clean = text.replace("—", "... ").replace('"', "").strip() or "Cricket history."
    voices = [voice_only] if voice_only else ["en-IN-PrabhatNeural", "en-US-ChristopherNeural", "en-GB-RyanNeural"]
    for voice in voices:
        try:
            kw = {"rate": "-4%"}
            if pitch: kw["pitch"] = pitch
            await edge_tts.Communicate(text=clean, voice=voice, **kw).save(str(path))
            if path.exists() and path.stat().st_size > 400: return
        except Exception as e:
            print(f"TTS retry ({voice}): {e}"); time.sleep(1)
    from gtts import gTTS
    gTTS(text=clean, lang="en", tld="co.in").save(str(path))

def get_dur(p):
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)], capture_output=True, text=True, check=True)
    return max(float(pr.stdout.strip()), 4.0)

def render_short(plan, out_mp4):
    OUT.mkdir(exist_ok=True)
    is_16_9 = plan.get("aspect_ratio") == "16:9"
    pitch = "-15Hz" if is_16_9 else None
    voice_only = "en-IN-PrabhatNeural" if is_16_9 else None
    segs, seed_b = [], int(time.time()) % 100000
    for i, sc in enumerate(plan["scenes"], 1):
        aud_p = OUT / f"sc{i}.mp3"
        asyncio.run(_tts(sc["narration"], aud_p, pitch=pitch, voice_only=voice_only))
        dur = get_dur(aud_p) + 0.35
        subs = []
        if "image" in sc:
            img_p, sub_v = Path(sc["image"]), OUT / f"s{i}_1.mp4"
            frames = max(int(dur * 30), 90)
            vf = f"scale=2134:1200:force_original_aspect_ratio=increase,crop=2134:1200,zoompan=z='min(zoom+0.0005,1.08)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30" if is_16_9 else f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
            subprocess.run(["ffmpeg", "-y", "-i", str(img_p), "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{dur:.2f}", str(sub_v)], check=True)
            subs.append(sub_v)
        prompts = [] if "image" in sc else (sc.get("image_prompts") or [sc["narration"]])
        queries = sc.get("search_queries") or prompts
        p_dur = dur / max(len(prompts), 1)
        for j, prm in enumerate(prompts, 1):
            sq = queries[j - 1] if j - 1 < len(queries) else prm[:60]
            img_p, sub_v = OUT / f"s{i}_{j}.png", OUT / f"s{i}_{j}.mp4"
            generate_image(prm, sq, img_p, seed_b + i * 10 + j)
            frames = max(int(p_dur * 30), 90)
            vf = f"scale=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
            subprocess.run(["ffmpeg", "-y", "-i", str(img_p), "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{p_dur:.2f}", str(sub_v)], check=True)
            subs.append(sub_v)
        sl = OUT / f"sl{i}.txt"
        sl.write_text("\n".join(f"file '{c.resolve()}'" for c in subs))
        sv, sf = OUT / f"sv{i}.mp4", OUT / f"sf{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(sl), "-c", "copy", str(sv)], check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(sv), "-i", str(aud_p), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(sf)], check=True)
        segs.append(sf)
    ml = OUT / "ml.txt"
    ml.write_text("\n".join(f"file '{s.resolve()}'" for s in segs))
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(ml), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_mp4)], check=True)

def upload(mp4, plan, privacy):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials(None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["YOUTUBE_CLIENT_ID"], client_secret=os.environ["YOUTUBE_CLIENT_SECRET"], scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    body = {"snippet": {"title": plan["title"][:100], "description": plan["description"], "tags": plan.get("tags", ["cricket", "shorts"]), "categoryId": "17"}, "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(mp4), mimetype="video/mp4", resumable=True))
    res = None
    while res is None: _, res = req.next_chunk()
    print(f"SUCCESS_YOUTUBE_URL: https://www.youtube.com/shorts/{res['id']}")
    return res["id"]

if __name__ == "__main__":
    history = load_history()
    plan_file = Path("yuvraj_2007_plan.json")
    if plan_file.exists():
        custom_plan = json.loads(plan_file.read_text(encoding="utf-8"))
        plan = custom_plan if custom_plan.get("topic_id") not in history else generate_plan(history)
    else:
        plan = generate_plan(history)
    mp4 = OUT / f"{plan['topic_id']}.mp4"
    render_short(plan, mp4)
    vid = upload(mp4, plan, os.environ.get("YOUTUBE_PRIVACY", "public"))
    save_history(plan["topic_id"], plan["title"], vid)
