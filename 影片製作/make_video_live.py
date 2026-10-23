"""工地環境安全即時監控｜今日版成果影片（真實資料，不插模擬）
與 make_video.py 共用錄影、口白、剪輯函式；不改 make_video.py，也不動原本的成品影片。

  python make_video_live.py --probe    讀取今日四個工地的即時數值（口白依此撰寫）
  python make_video_live.py --record   依 腳本_今日.json 錄製今日畫面
  python make_video_live.py --build    剪成今日版成品
"""
import asyncio, base64, json, os, re, shutil, subprocess, sys, time, urllib.request
import make_video as mv

HERE = mv.HERE
SRC = os.path.join(os.path.dirname(HERE), "上傳這個_手機版", "m.html")
LIVE = os.path.join(HERE, "site_live"); os.makedirs(LIVE, exist_ok=True)
LIVE_HTML = os.path.join(LIVE, "live.html")
SCRIPT = os.path.join(HERE, "腳本_今日.json")
WORK = os.path.join(mv.WORK, "live"); os.makedirs(os.path.join(WORK, "clips"), exist_ok=True)
TIMING = os.path.join(WORK, "timing.json"); MARKS = os.path.join(WORK, "marks.json")
RAW = os.path.join(WORK, "raw.mp4"); FRAMES = os.path.join(WORK, "frames")
OUT = os.path.join(HERE, "工地環境安全即時監控 今日版 成果影片.mp4")
PORT = 8127

def prepare_live():
    # 直接複製網頁版，不插入 sim.js：錄到的就是網頁現在顯示的真實資料
    shutil.copyfile(SRC, LIVE_HTML)

def open_live():
    mv.kill_chrome(); time.sleep(1)
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", LIVE],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.Popen([mv.CHROME, "--headless=new", f"--remote-debugging-port={mv.DBG}", f"--user-data-dir={mv.PROFILE}",
                      f"--window-size={mv.VW},{mv.VH}", "--hide-scrollbars", "--mute-audio", "--no-first-run",
                      "--disable-background-timer-throttling", "--disable-renderer-backgrounding", "about:blank"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    for _ in range(60):
        try:
            lst = json.load(urllib.request.urlopen(f"http://127.0.0.1:{mv.DBG}/json/list", timeout=2))
            ws = next(x["webSocketDebuggerUrl"] for x in lst if x.get("type") == "page"); break
        except Exception: time.sleep(0.5)
    assert ws, "背景 Chrome 沒有啟動"
    c = mv.CDP(ws)
    c.call("Emulation.setDeviceMetricsOverride", width=mv.VW, height=mv.VH, deviceScaleFactor=mv.DSF, mobile=False)
    c.call("Page.enable"); c.call("Runtime.enable")
    c.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/live.html")
    t0 = time.time()
    while time.time() - t0 < 120:
        try:
            if c.js("(()=>{const r=document.querySelector('#rain');return !!r && r.textContent.trim().length>20 && !!document.querySelector('#wind').textContent.trim()})()"): break
        except Exception: pass
        time.sleep(0.5)
    else: raise RuntimeError("網頁 120 秒內沒有載入即時資料")
    return c, srv

PROBE_JS = """(async()=>{
  const out={};
  const pick=s=>{const e=document.querySelector(s);return e?e.innerText.replace(/\\s+/g,' ').trim():null};
  const btns=[...document.querySelectorAll('button[data-i]')];
  let prev=null;
  for(const b of btns){
    b.click();
    // 等測站資料換成這一場地的（資料要打 API，約 5～15 秒）
    for(let k=0;k<60;k++){ await new Promise(r=>setTimeout(r,1000)); const s=pick('#stainfo'); if(s && s!==prev && b.className.includes('on')) break; }
    await new Promise(r=>setTimeout(r,4000));
    prev=pick('#stainfo');
    out[b.innerText.trim()]={stainfo:pick('#stainfo'),rain:pick('#rain'),wind:pick('#wind'),alerts:pick('#alerts'),banner:pick('#banner'),lastup:pick('#lastup')};
  }
  const al=[...document.querySelectorAll('.al[data-t="颱風"]')].map(e=>e.innerText.replace(/\\s+/g,' ').trim());
  out.typhoonAlert=al;
  return out;
})()"""

def probe():
    prepare_live()
    c, srv = open_live()
    try:
        res = c.js(PROBE_JS, timeout=900)
        print(json.dumps(res, ensure_ascii=False, indent=1))
    finally:
        mv.kill_chrome(); srv.terminate()

# ======================================================================
# 口白（沿用 make_video 的語音設定；時間表寫進 _work/live）
# ======================================================================
def tts():
    sc = json.load(open(SCRIPT, encoding="utf-8")); out = []
    for seg in sc["segments"]:
        rows = []
        for ln in seg["lines"]:
            wav, d = mv.voice(ln["t"]); dur = max(mv.LEAD + d + mv.TAIL, ln.get("min", 0))
            rows.append({"wav": wav, "voice": round(d, 3), "dur": round(dur, 3)})
        out.append(rows)
    json.dump(out, open(TIMING, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("口白完成，共", sum(len(s) for s in out), "句，總長", round(sum(r["dur"] for s in out for r in s), 1), "秒")

# ======================================================================
# 錄影：真實網頁，只做點選與區塊定位（不插模擬）
# ======================================================================
# 點選場地按鈕：等測站資料換成該場地才繼續
WARM_JS = """(async(i)=>{
  const b=document.querySelector('button[data-i="'+i+'"]'); const before=document.querySelector('#stainfo').innerText;
  b.click();
  for(let k=0;k<90;k++){ await new Promise(r=>setTimeout(r,1000)); if(b.className.includes('on') && document.querySelector('#stainfo').innerText!==before) break; }
  await new Promise(r=>setTimeout(r,2500)); return true;
})(%d)"""
RECT_JS = """(s=>{const e=document.querySelector(s); if(!e) return null; const r=e.getBoundingClientRect();
  return {x:r.left,y:r.top,w:r.width,h:r.height};})(%s)"""

def do_action(c, a, zoom_marks):
    if "go" in a: c.js(WARM_JS % a["go"], timeout=120)
    if "ov" in a: c.js("document.querySelector('.al[data-t=\"颱風\"]').click()")
    if "close" in a: c.js("(()=>{const o=document.querySelector('#ovTy'); if(o) o.click();})()")
    if "scroll" in a: c.js("(()=>{const e=document.querySelector(%s); if(e) e.scrollIntoView({block:'center'});})()" % json.dumps(a["scroll"]))

def record():
    sc = json.load(open(SCRIPT, encoding="utf-8")); tm = json.load(open(TIMING, encoding="utf-8"))
    if os.path.isdir(FRAMES): shutil.rmtree(FRAMES)
    os.makedirs(FRAMES)
    c, srv = open_live(); stamps = []
    try:
        for i in (1, 2, 3, 0):                 # 先把四個場地的資料載入快取，錄影時切換才不必等網路
            c.js(WARM_JS % i, timeout=120)
        c.js(WARM_JS % 0, timeout=120)
        def on_frame(p):
            n = len(stamps); open(os.path.join(FRAMES, f"{n:06d}.jpg"), "wb").write(base64.b64decode(p["data"]))
            stamps.append(p["metadata"].get("timestamp") or time.time())
            c.send("Page.screencastFrameAck", sessionId=p["sessionId"])
        c.on["Page.screencastFrame"] = on_frame
        c.call("Page.startScreencast", format="jpeg", quality=88, maxWidth=mv.CW, maxHeight=mv.CH, everyNthFrame=1)
        time.sleep(1.5)
        marks = {"lines": {}, "rects": {}}
        for si, seg in enumerate(sc["segments"]):
            if "card" in seg: continue
            for li, ln in enumerate(seg["lines"]):
                dur = tm[si][li]["dur"]; st = time.time(); key = f"{si}_{li}"
                marks["lines"][key] = st
                ev = sorted(ln.get("do", []), key=lambda x: x.get("at", 0)); done_rect = False
                while time.time() - st < dur:
                    el = time.time() - st
                    while ev and el >= ev[0].get("at", 0):
                        do_action(c, ev.pop(0), marks)
                    if not done_rect and el > min(dur - 0.2, 1.6):
                        z = ln.get("zoom")
                        if z: marks["rects"].setdefault(key, {})[z] = c.js(RECT_JS % json.dumps(z))
                        done_rect = True
                    time.sleep(0.03)
                print("  錄完", key, ln["t"][:18], flush=True)
        time.sleep(1.0); c.call("Page.stopScreencast"); time.sleep(0.5)
    finally:
        mv.kill_chrome(); srv.terminate()
    t0 = stamps[0]
    marks["lines"] = {k: v - t0 for k, v in marks["lines"].items()}
    lst = os.path.join(WORK, "frames.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for i, t in enumerate(stamps):
            d = (stamps[i + 1] - t) if i + 1 < len(stamps) else 0.5
            f.write(f"file 'frames/{i:06d}.jpg'\nduration {max(d, 0.001):.4f}\n")
        f.write(f"file 'frames/{len(stamps) - 1:06d}.jpg'\n")
    subprocess.run([mv.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"fps={mv.FPS},format=yuv420p",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "16", RAW], check=True, cwd=WORK)
    json.dump(marks, open(MARKS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("錄影完成：", len(stamps), "格，長", round(stamps[-1] - t0, 1), "秒")

# ======================================================================
# 剪輯（與 make_video 相同的版式；裁切依本次錄到的 RAW）
# ======================================================================
def raw_size():
    r = subprocess.run([mv.FF, "-hide_banner", "-i", RAW], capture_output=True, encoding="utf-8", errors="replace")
    m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", r.stderr); return int(m[1]), int(m[2])

def crop_for(r):
    cw, ch = raw_size(); dsf = cw / mv.VW
    x, y, w, h = [v * dsf for v in (r["x"], r["y"], r["w"], r["h"])]; pad = 22 * dsf
    x -= pad; y -= pad; w += 2 * pad; h += 2 * pad
    if w / h < 16 / 9: nw = h * 16 / 9; x -= (nw - w) / 2; w = nw
    else: nh = w * 9 / 16; y -= (nh - h) / 2; h = nh
    w = max(w, cw * 0.38); h = w * 9 / 16
    if w > cw: w, h = cw, ch
    x = min(max(0, x), cw - w); y = min(max(0, y), ch - h)
    return int(x) // 2 * 2, int(y) // 2 * 2, int(w) // 2 * 2, int(h) // 2 * 2

def live_card(kind, sc):
    im = mv.Image.new("RGB", (mv.W, mv.H), (9, 12, 18)); d = mv.ImageDraw.Draw(im)
    lines = sc["cards"][kind]
    y = 330
    for i, (txt, sz, col) in enumerate(lines):
        d.text((mv.W // 2, y), txt, font=mv.font(sz, sz > 50), fill=tuple(col), anchor="mm"); y += sz + 40
    p = os.path.join(WORK, f"card_{kind}.png"); im.save(p); return p

def build():
    sc = json.load(open(SCRIPT, encoding="utf-8")); tm = json.load(open(TIMING, encoding="utf-8")); mk = json.load(open(MARKS, encoding="utf-8"))
    clips = []
    for si, seg in enumerate(sc["segments"]):
        for li, ln in enumerate(seg["lines"]):
            key = f"L{si}_{li}"; T = tm[si][li]
            if "card" in seg:
                vin = ["-loop", "1", "-framerate", str(mv.FPS), "-t", f"{T['dur']:.3f}", "-i", live_card(seg["card"], sc)]; vf = f"scale={mv.W}:{mv.H}"
            else:
                vin = ["-ss", f"{mk['lines'][f'{si}_{li}']:.3f}", "-t", f"{T['dur']:.3f}", "-i", RAW]
                z = ln.get("zoom"); r = mk["rects"].get(f"{si}_{li}", {}).get(z) if z else None
                if r:
                    x, y, w, h = crop_for(r); vf = f"crop={w}:{h}:{x}:{y},scale={mv.W}:{mv.H}:flags=lanczos"
                else:
                    vf = f"scale={mv.W}:{mv.H}:flags=lanczos"
            clips.append(mv.line_clip(key, vin, vf, ln["t"], T["wav"], T["voice"], T["dur"], False))
            print("  ", key, round(T["dur"], 1), "秒", flush=True)
    lst = os.path.join(WORK, "clips.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{c.replace(chr(92), '/')}'\n" for c in clips))
    subprocess.run([mv.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", OUT], check=True)
    print("完成", OUT, round(os.path.getsize(OUT) / 1048576, 1), "MB")

if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    steps = {"--probe": probe, "--tts": tts, "--record": record, "--build": build,
             "--all": lambda: (tts(), record(), build())}
    steps.get(a, lambda: print(__doc__))()
