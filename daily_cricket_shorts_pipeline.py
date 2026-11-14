import argparse, asyncio, datetime, json, os, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CHANNEL_HANDLE = "@CricketingBeastHK"
HISTORY_FILE = Path("published_history.json")
OUT = Path("build_output")

PROMPT = """You are the scriptwriter for YouTube Shorts channel CricketingBeast (@CricketingBeastHK).
Create a 45-second high-retention 5-beat cricket Short (hook, setup, rapid stat escalation, climax reveal, debate question that loops back into Beat 1).
Return STRICT JSON:
{"topic_id":"slug","title":"Title under 65 chars #Shorts #Cricket","description":"SEO summary + question + #Cricket #Shorts","tags":["cricket","cricketshorts","cricketingbeast"],"category_id":"17","beats":[{"beat_number":1,"phase_label":"HOOK","headline_stat":"BIG STAT","sub_stat":"MATCH • YEAR","narration":"Spoken line","accent_hex":"#FF9933"}]}"""

def load_history():
    return json.loads(HISTORY_FILE.read_text()).get("published_topics", []) if HISTORY_FILE.exists() else []

def save_history(topic_id, title, video_id):
    h = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {"published_topics": [], "runs": []}
    if topic_id not in h["published_topics"]: h["published_topics"].append(topic_id)
    h["runs"].append({"date": datetime.date.today().isoformat(), "topic_id": topic_id, "title": title, "video_id": video_id})
    HISTORY_FILE.write_text(json.dumps(h, indent=2))

def generate_plan(excluded):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    res = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=f"Create today's Cricket Short for {CHANNEL_HANDLE}. Exclude topics: {excluded[-40:]}.",
        config=types.GenerateContentConfig(system_instruction=PROMPT, response_mime_type="application/json", temperature=0.8),
    )
    return json.loads(res.text)

async def _tts(text, path):
    import edge_tts
    await edge_tts.Communicate(text=text, voice="en-IN-PrabhatNeural", rate="+8%").save(str(path))

def render_short(plan, out_mp4):
    OUT.mkdir(exist_ok=True)
    f_b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    f_h = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 82)
    f_n = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 46)
    segs = []
    for i, b in enumerate(plan["beats"], 1):
        img_p, aud_p, seg_p = OUT / f"b{i}.png", OUT / f"b{i}.mp3", OUT / f"s{i}.mp4"
        asyncio.run(_tts(b["narration"], aud_p))
        img = Image.new("RGB", (1080, 1920), (12, 18, 34))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([60, 80, 1020, 175], radius=24, fill=(22, 32, 58), outline=(255, 153, 51), width=4)
        d.text((95, 108), f"CRICKETING BEAST • {CHANNEL_HANDLE}", fill=(255, 255, 255), font=f_b)
        d.rounded_rectangle([60, 260, 1020, 960], radius=36, fill=(18, 26, 48), outline=(255, 153, 51), width=5)
        d.text((100, 310), b.get("phase_label", f"BEAT {i}").upper(), fill=(255, 153, 51), font=f_b)
        y = 410
        for line in textwrap.wrap(b["headline_stat"].upper(), 14)[:3]:
            d.text((100, y), line, fill=(255, 255, 255), font=f_h); y += 100
        d.text((100, 830), b.get("sub_stat", "").upper()[:34], fill=(0, 229, 255), font=f_b)
        d.rounded_rectangle([60, 1020, 1020, 1640], radius=32, fill=(24, 36, 64), outline=(80, 105, 155), width=3)
        yn = 1080
        for line in textwrap.wrap(b["narration"], 28)[:7]:
            d.text((100, yn), line, fill=(245, 247, 252), font=f_n); yn += 68
        img.save(img_p)
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img_p), "-i", str(aud_p), "-c:v", "libx264", "-tune", "stillimage", "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(seg_p)], check=True)
        segs.append(seg_p)
    lst = OUT / "list.txt"
    lst.write_text("\n".join(f"file '{s.resolve()}'" for s in segs))
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out_mp4)], check=True)

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
    return res["id"]

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--get-refresh-token", metavar="JSON")
    args = p.parse_args()
    if args.get_refresh_token:
        from google_auth_oauthlib.flow import InstalledAppFlow
        c = InstalledAppFlow.from_client_secrets_file(args.get_refresh_token, scopes=["https://www.googleapis.com/auth/youtube.upload"]).run_local_server(port=8080, access_type="offline", prompt="consent")
        print(f"YOUTUBE_CLIENT_ID={c.client_id}\nYOUTUBE_CLIENT_SECRET={c.client_secret}\nYOUTUBE_REFRESH_TOKEN={c.refresh_token}")
    else:
        plan = generate_plan(load_history())
        mp4 = OUT / f"{plan['topic_id']}.mp4"
        render_short(plan, mp4)
        vid = upload(mp4, plan, os.environ.get("YOUTUBE_PRIVACY", "public"))
        save_history(plan["topic_id"], plan["title"], vid)
