import asyncio, json, os, re, subprocess, sys, argparse
import edge_tts

VOICE = "ar-SA-HamedNeural"   # صوت رجالي من مايكروسوفت
p = argparse.ArgumentParser()
p.add_argument("--shard", type=int, default=0)
p.add_argument("--of", type=int, default=1)
p.add_argument("--out", default="out")
p.add_argument("--limit", type=int, default=0)
p.add_argument("--workers", type=int, default=6)
a = p.parse_args()

items = json.load(open(os.path.join(os.path.dirname(__file__), "texts.json"), encoding="utf8"))
items = [x for i, x in enumerate(items) if i % a.of == a.shard]
if a.limit:
    items = items[:a.limit]
os.makedirs(a.out, exist_ok=True)

def clean(t):
    t = t.replace("ﷺ", " صلى الله عليه وسلم ")
    t = re.sub(r"[«»‏]", " ", t)
    t = t.replace(".‏.", ".").replace("...", "،")
    return re.sub(r"\s+", " ", t).strip()

async def one(sem, it, stats):
    path = os.path.join(a.out, it["h"] + ".mp3")
    if os.path.exists(path) and os.path.getsize(path) > 500:
        stats["skip"] += 1
        return
    async with sem:
        for attempt in range(5):
            try:
                raw = path + ".raw.mp3"
                await edge_tts.Communicate(clean(it["t"]), VOICE, rate="-5%").save(raw)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-ac", "1",
                                "-ar", "22050", "-b:a", "16k", path], check=True)
                os.remove(raw)
                stats["ok"] += 1
                if (stats["ok"] + stats["fail"]) % 50 == 0:
                    print(stats, flush=True)
                return
            except Exception as e:
                await asyncio.sleep(3 * (attempt + 1))
        stats["fail"] += 1
        print("FAILED", it["h"], flush=True)

async def main():
    sem = asyncio.Semaphore(a.workers)
    stats = {"ok": 0, "skip": 0, "fail": 0}
    await asyncio.gather(*[one(sem, it, stats) for it in items])
    print("DONE", stats)

asyncio.run(main())
