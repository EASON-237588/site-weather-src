"""工地環境安全即時監控｜營造學院成果影片（橫向 1920x1080）
錄的是線上網頁版（上傳這個_手機版/m.html，四案場輪播）的副本；副本插入 sim.js 做模擬情境與馬賽克。
不修改專案原有檔案，產物全部在「影片製作」資料夾。字幕 ＝ 口白同一句話。

  python make_video.py --bake     產生 site/demo.html（插入 sim.js）與模擬雷達回波圖
  python make_video.py --tts      依 腳本.json 產生口白並量長度（錄影的節奏以此為準）
  python make_video.py --record   背景 Chrome 逐格擷取畫面（不錄桌面，不受通知與滑鼠干擾）
  python make_video.py --frames   抽每一句的畫面做檢查
  python make_video.py --build    剪成成品
  python make_video.py --all      以上依序全跑
"""
import asyncio, base64, hashlib, json, os, queue, re, shutil, socket, struct, subprocess, sys, threading, time
import urllib.parse, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import edge_tts, imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
WORK = os.path.join(HERE, "_work"); SITE = os.path.join(HERE, "site")
for d in (WORK, SITE, os.path.join(SITE, "radar"), os.path.join(WORK, "audio"), os.path.join(WORK, "clips")): os.makedirs(d, exist_ok=True)
SRC = os.path.join(ROOT, "上傳這個_手機版", "m.html")
SCRIPT = os.path.join(HERE, "腳本.json"); TIMING = os.path.join(WORK, "timing.json"); MARKS = os.path.join(WORK, "marks.json")
FRAMES = os.path.join(WORK, "frames"); RAW = os.path.join(WORK, "raw.mp4")
OUT = os.path.join(HERE, "工地環境安全即時監控 成果影片.mp4")
FF = imageio_ffmpeg.get_ffmpeg_exe()
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = os.path.join(os.environ["TEMP"], "rain_demo_chrome")
PORT, DBG = 8125, 9333
VW, VH, DSF = 1600, 900, 1.6            # 網頁的 CSS 視窗與縮放 → 擷取 2560x1440，放大特寫時仍清楚
CW, CH = int(VW * DSF), int(VH * DSF)
W, H, FPS = 1920, 1080, 30
VOICE, RATE = "zh-TW-HsiaoChenNeural", "+15%"
LEAD, TAIL = 0.25, 0.45                  # 每句口白前後留白秒數

def load_script(): return json.load(open(SCRIPT, encoding="utf-8"))
def font(s, b=True): return ImageFont.truetype("C:/Windows/Fonts/" + ("msjhbd.ttc" if b else "msjh.ttc"), s)

# ======================================================================
# 1. 副本與模擬雷達
# ======================================================================
def bake():
    s = open(SRC, encoding="utf-8").read()
    anchor = "\nloadCfg();\ndocument.body.dataset.fx=SITE_FX;"
    assert s.count(anchor) == 1, "找不到插入點，網頁版程式結構可能改了"
    sim = open(os.path.join(HERE, "sim.js"), encoding="utf-8").read()
    s = s.replace(anchor, "\n" + sim + anchor, 1)
    open(os.path.join(SITE, "demo.html"), "w", encoding="utf-8", newline="\n").write(s)
    print("已輸出 site/demo.html")
    radar_frames()

def ll2px(lat, lon):
    """氣象署 CV1_TW_1000 底圖：經緯度等距，每度約 166.7 px；(121E, 24N) 在 (500, 416.7)。用七股、南屯雷達站位置驗算過"""
    return 500 + (lon - 121) * 166.7, 416.7 - (lat - 24) * 166.7

def radar_frames():
    base_p = os.path.join(WORK, "CV1_TW_1000.png")
    if not os.path.exists(base_p):
        urllib.request.urlretrieve("https://www.cwa.gov.tw/Data/radar/CV1_TW_1000.png", base_p)
    im = Image.open(base_p).convert("RGB"); a = np.array(im).astype(int)
    # 圖例色階：右下色條，0 dBZ 在下、65 在上
    pal = []
    for y in range(700, 991):
        c = a[y, 956]; pal.append(((990 - y) / 290 * 65, tuple(int(v) for v in c)))
    pal.sort()
    def color(db):
        for d, c in pal:
            if d >= db: return c
        return pal[-1][1]
    # 把真實回波洗掉：彩色像素（排除圖例、標誌、左上站名）換成周圍底色
    sat = a.max(axis=2) - a.min(axis=2)
    m = sat > 45
    m[880:, :150] = False; m[660:, 930:] = False; m[:210, :130] = False
    clean = im.copy(); filled = im.filter(ImageFilter.MedianFilter(11))
    ca = np.array(clean); fa = np.array(filled)
    for _ in range(3):
        ca[m] = fa[m]; fa = np.array(Image.fromarray(ca).filter(ImageFilter.MedianFilter(11)))
    ca[m] = fa[m]
    sat2 = ca.max(axis=2).astype(int) - ca.min(axis=2)
    ca[m & (sat2 > 30)] = 255
    clean = Image.fromarray(ca)
    rng = np.random.default_rng(7)
    def noise(r):
        n = Image.fromarray((rng.random((1000, 1000)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
        n = np.array(n).astype(float); return (n - n.mean()) / (n.std() + 1e-6)
    N1, N2 = noise(9), noise(2.5)
    Y, X = np.mgrid[0:1000, 0:1000].astype(float)
    nx, ny = 0.82, 0.57; L = (nx * nx + ny * ny) ** .5; nx, ny = nx / L, ny / L      # 雨帶往東南東移動
    tx, ty = ny, -nx                                                               # 雨帶本身沿西南—東北
    def frame(name, site, d, peak, stamp, along=230):
        sx, sy = ll2px(*site); cx, cy = sx - d * nx, sy - d * ny
        s = (X - cx) * nx + (Y - cy) * ny; u = (X - cx) * tx + (Y - cy) * ty
        sig = np.where(s > 0, 13.0, 38.0)                                          # 前緣陡、後方拖一片層狀雨
        sh = int(round(d)); n1 = np.roll(N1, (-int(sh * ny), -int(sh * nx)), (0, 1)); n2 = np.roll(N2, (-int(sh * ny), -int(sh * nx)), (0, 1))
        env = np.exp(-(s / sig) ** 2) * np.exp(-(u / along) ** 2)
        db = peak * env * (1 + 0.22 * n1) + 4.5 * n2 * np.clip(env * 3, 0, 1)            # 細紋理只留在雨帶裡，避免滿圖雜點
        db += 9 * np.exp(-(s / 9) ** 2) * np.clip(n1, 0, None) * np.exp(-(u / along) ** 2)   # 前緣對流胞
        out = np.array(clean).copy(); mask = (db >= 12) & (env > 0.05)
        lut = np.array([color(v) for v in range(0, 66)], dtype=np.uint8)
        out[mask] = lut[np.clip(db[mask], 0, 65).astype(int)]
        img = Image.fromarray(out); dr = ImageDraw.Draw(img)
        dr.rectangle((18, 10, 350, 58), fill=(255, 255, 255)); dr.text((26, 14), stamp, font=font(30), fill=(200, 40, 30))
        r = 10; dr.ellipse((sx - r, sy - r, sx + r, sy + r), outline=(220, 20, 20), width=4); dr.ellipse((sx - 3, sy - 3, sx + 3, sy + 3), fill=(220, 20, 20))
        f = font(26); dr.text((sx + 15, sy - 32), "工地", font=f, fill=(220, 20, 20), stroke_width=4, stroke_fill=(255, 255, 255))
        img.save(os.path.join(SITE, "radar", name + ".png"))
    sc = load_script()["sims"]; tc = (24.1560, 120.6999); il = (24.7523, 121.7594)
    for i, d in enumerate((120, 84, 52, 24)):
        frame(f"ra{i}", tc, d, 44, f"模擬回波　+{i * 10} 分")
    frame("rb", tc, -8, 52, "模擬回波　雨帶通過")
    frame("rc", il, 0, 40, "模擬回波　強風豪雨", along=320)
    print("已輸出模擬雷達回波", sorted(os.listdir(os.path.join(SITE, "radar"))))

# ======================================================================
# 2. 口白
# ======================================================================
def probe(p):
    r = subprocess.run([FF, "-hide_banner", "-i", p], capture_output=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr); return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
async def _tts(text, p): await edge_tts.Communicate(text, VOICE, rate=RATE).save(p)
def voice(text):
    h = hashlib.md5((VOICE + RATE + text).encode("utf-8")).hexdigest()[:12]
    mp3 = os.path.join(WORK, "audio", h + ".mp3"); wav = mp3[:-4] + ".wav"
    if not os.path.exists(wav):
        if not os.path.exists(mp3): asyncio.run(_tts(text, mp3))
        trim = "silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.04,areverse,silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.08,areverse"
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3, "-af", trim, "-ar", "44100", "-ac", "2", wav], check=True)
    return wav, probe(wav)

def tts():
    sc = load_script(); out = []
    for si, seg in enumerate(sc["segments"]):
        rows = []
        for li, ln in enumerate(seg["lines"]):
            wav, d = voice(ln["t"]); dur = max(LEAD + d + TAIL, ln.get("min", 0))
            rows.append({"wav": wav, "voice": round(d, 3), "dur": round(dur, 3)})
        out.append(rows)
    json.dump(out, open(TIMING, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tot = sum(r["dur"] for seg in out for r in seg)
    print("口白完成，共", sum(len(s) for s in out), "句，總長", round(tot, 1), "秒")

# ======================================================================
# 3. 錄影：背景 Chrome ＋ 內建除錯介面（自寫的最小 websocket，不需另裝套件）
# ======================================================================
class CDP:
    def __init__(self, url):
        u = urllib.parse.urlparse(url); self.s = socket.create_connection((u.hostname, u.port))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf: buf += self.s.recv(4096)
        head, rest = buf.split(b"\r\n\r\n", 1); assert b" 101 " in head.split(b"\r\n")[0], head
        self.buf = bytearray(rest); self.n = 0; self.idl = threading.Lock(); self.wl = threading.Lock()
        self.wait = {}; self.on = {}
        threading.Thread(target=self._loop, daemon=True).start()
    def _need(self, k):
        while len(self.buf) < k:
            d = self.s.recv(1 << 20)
            if not d: raise EOFError
            self.buf += d
        r = bytes(self.buf[:k]); del self.buf[:k]; return r
    def _frame(self):
        msg = b""
        while True:
            b1, b2 = self._need(2); op, n = b1 & 15, b2 & 127
            if n == 126: n = struct.unpack(">H", self._need(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._need(8))[0]
            if b2 & 128: self._need(4)
            data = self._need(n)
            if op == 8: raise EOFError
            if op == 9: self._send(data, 10); continue
            msg += data
            if b1 & 128: return msg
    def _send(self, data, op=1):
        mk = os.urandom(4); n = len(data); h = bytes([128 | op])
        h += bytes([128 | n]) if n < 126 else (bytes([254]) + struct.pack(">H", n) if n < 65536 else bytes([255]) + struct.pack(">Q", n))
        arr = np.frombuffer(data, dtype=np.uint8); m = np.frombuffer((mk * (n // 4 + 1))[:n], dtype=np.uint8)
        with self.wl: self.s.sendall(h + mk + (arr ^ m).tobytes())
    def _loop(self):
        while True:
            try: m = json.loads(self._frame())
            except Exception: break
            if "id" in m:
                q = self.wait.pop(m["id"], None)
                if q: q.put(m)
            elif m.get("method") in self.on: self.on[m["method"]](m.get("params", {}))
    def send(self, method, **p):
        with self.idl: self.n += 1; i = self.n
        self._send(json.dumps({"id": i, "method": method, "params": p}).encode()); return i
    def call(self, method, timeout=60, **p):
        with self.idl: self.n += 1; i = self.n
        q = queue.Queue(); self.wait[i] = q
        self._send(json.dumps({"id": i, "method": method, "params": p}).encode())
        r = q.get(timeout=timeout)
        if "error" in r: raise RuntimeError(f"{method}: {r['error']}")
        return r.get("result", {})
    def js(self, expr, wait=True, timeout=60):
        if not wait: return self.send("Runtime.evaluate", expression=expr)
        r = self.call("Runtime.evaluate", timeout=timeout, expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r: raise RuntimeError("網頁執行錯誤：" + json.dumps(r["exceptionDetails"], ensure_ascii=False)[:400])
        return r.get("result", {}).get("value")

def kill_chrome():
    subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*rain_demo_chrome*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"], capture_output=True)

def open_page():
    kill_chrome(); time.sleep(1)
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", SITE],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={DBG}", f"--user-data-dir={PROFILE}",
                      f"--window-size={VW},{VH}", "--hide-scrollbars", "--mute-audio", "--no-first-run",
                      "--disable-background-timer-throttling", "--disable-renderer-backgrounding", "about:blank"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    for _ in range(60):
        try:
            lst = json.load(urllib.request.urlopen(f"http://127.0.0.1:{DBG}/json/list", timeout=2))
            ws = next(x["webSocketDebuggerUrl"] for x in lst if x.get("type") == "page"); break
        except Exception: time.sleep(0.5)
    assert ws, "背景 Chrome 沒有啟動"
    c = CDP(ws)
    c.call("Emulation.setDeviceMetricsOverride", width=VW, height=VH, deviceScaleFactor=DSF, mobile=False)
    c.call("Page.enable"); c.call("Runtime.enable")
    c.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/demo.html")
    t0 = time.time()
    while time.time() - t0 < 90:
        try:
            if c.js("window.SIM&&SIM.ready()"): break
        except Exception: pass
        time.sleep(0.5)
    else: raise RuntimeError("網頁 90 秒內沒有載入完成（氣象資料抓取可能失敗）")
    c.js("SIM.stop()")
    return c, srv

def shot(name):
    """不錄影，只拍一張整頁，檢查版面與馬賽克用"""
    c, srv = open_page()
    try:
        time.sleep(3); d = c.call("Page.captureScreenshot", format="png")["data"]
        p = os.path.join(WORK, name + ".png"); open(p, "wb").write(base64.b64decode(d)); print("已拍", p)
        print(json.dumps(c.js("SIM.rects()"), ensure_ascii=False))
    finally:
        kill_chrome(); srv.terminate()

def record():
    sc = load_script(); tm = json.load(open(TIMING, encoding="utf-8")); sims = sc["sims"]
    if os.path.isdir(FRAMES): shutil.rmtree(FRAMES)
    os.makedirs(FRAMES)
    c, srv = open_page(); stamps = []
    try:
        for i in (1, 2, 3, 0):              # 先把四個案場的資料抓進快取，錄影中切換就不必等網路
            c.js(f"SIM.go({i})", timeout=90); time.sleep(1.2)
        time.sleep(2)
        def on_frame(p):
            n = len(stamps); open(os.path.join(FRAMES, f"{n:06d}.jpg"), "wb").write(base64.b64decode(p["data"]))
            stamps.append(p["metadata"].get("timestamp") or time.time())
            c.send("Page.screencastFrameAck", sessionId=p["sessionId"])
        c.on["Page.screencastFrame"] = on_frame
        c.call("Page.startScreencast", format="jpeg", quality=88, maxWidth=CW, maxHeight=CH, everyNthFrame=1)
        time.sleep(1.5)
        marks = {"lines": {}, "rects": {}}
        loop = {"list": None, "every": 1.4, "i": 0, "next": 0}
        def act(a):
            if "loop" in a:
                loop["list"] = a["loop"]; loop["every"] = a.get("every", 1.4); loop["i"] = 0; loop["next"] = 0
            if "prep" in a: c.js("SIM.prep(%s)" % json.dumps(sims.get(a["prep"]) if a["prep"] else None, ensure_ascii=False))
            if "set" in a: c.js("SIM.set(%s)" % json.dumps(sims[a["set"]], ensure_ascii=False))
            if "close" in a: c.js("SIM.close()")
            if "go" in a: c.js(f"SIM.go({a['go']})", wait=False)
            if "radar" in a: c.js("SIM.radar(%s)" % json.dumps(a["radar"]))
            if "hl" in a: c.js("SIM.hl(%s)" % json.dumps(a["hl"]))
            if "report" in a: c.js("SIM.report()")
            if "rscroll" in a: c.js(f"SIM.rscroll({a['rscroll']})")
        for si, seg in enumerate(sc["segments"]):
            if "card" in seg: continue
            for li, ln in enumerate(seg["lines"]):
                dur = tm[si][li]["dur"]; st = time.time(); key = f"{si}_{li}"
                marks["lines"][key] = st
                ev = sorted(ln.get("do", []), key=lambda x: x.get("at", 0)); done_rect = False
                while time.time() - st < dur:
                    el = time.time() - st
                    while ev and el >= ev[0].get("at", 0): act(ev.pop(0))
                    if loop["list"] and time.time() >= loop["next"]:
                        c.js("SIM.radar(%s)" % json.dumps(loop["list"][loop["i"] % len(loop["list"])]))
                        loop["i"] += 1; loop["next"] = time.time() + loop["every"]
                    if not done_rect and el > min(dur - 0.2, 1.6):
                        marks["rects"][key] = c.js("SIM.rects()"); done_rect = True
                    time.sleep(0.03)
                print("  錄完", key, ln["t"][:18], flush=True)
        marks["nowcast"] = c.js("SIM.nowcast()")
        time.sleep(1.0); c.call("Page.stopScreencast"); time.sleep(0.5)
    finally:
        kill_chrome(); srv.terminate()
    t0 = stamps[0]
    marks["lines"] = {k: v - t0 for k, v in marks["lines"].items()}
    lst = os.path.join(WORK, "frames.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for i, t in enumerate(stamps):
            d = (stamps[i + 1] - t) if i + 1 < len(stamps) else 0.5
            f.write(f"file 'frames/{i:06d}.jpg'\nduration {max(d, 0.001):.4f}\n")
        f.write(f"file 'frames/{len(stamps) - 1:06d}.jpg'\n")
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"fps={FPS},format=yuv420p",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "16", RAW], check=True, cwd=WORK)
    json.dump(marks, open(MARKS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("錄影完成：", len(stamps), "格，長", round(stamps[-1] - t0, 1), "秒")

# ======================================================================
# 4. 剪輯
# ======================================================================
TEAL, WHT, DIM, RED, YEL = (111, 211, 192), (240, 244, 248), (150, 162, 178), (230, 70, 60), (255, 213, 74)
def card_png(kind):
    im = Image.new("RGB", (W, H), (9, 12, 18)); d = ImageDraw.Draw(im)
    if kind == "title":
        d.text((W // 2, 360), "工地環境安全即時監控", font=font(104), fill=WHT, anchor="mm")
        d.text((W // 2, 500), "一個網頁　同時監控四個工地", font=font(54, False), fill=TEAL, anchor="mm")
        tags = ["降雨", "熱危害", "風速", "颱風", "地震"]; x = W // 2 - (len(tags) * 200 - 40) // 2
        for t in tags:
            d.rounded_rectangle((x, 620, x + 160, 690), 14, outline=TEAL, width=3); d.text((x + 80, 655), t, font=font(36), fill=WHT, anchor="mm"); x += 200
    else:
        d.text((W // 2, 150), "停工研判門檻（一般參考值）", font=font(64), fill=WHT, anchor="mm")
        rows = [("混凝土澆置", "時雨量 ≥ 4 mm　停止澆置"), ("塔吊／起重機", "陣風 ≥ 10 m/s 停止高處作業　≥ 15 m/s 停止吊掛"),
                ("當日累積雨量", "≥ 80 mm 大雨　≥ 200 mm 豪雨"), ("地震", "震度 4 級立即檢查　5 弱以上停工檢查"), ("熱危害", "依職安署熱指數分級")]
        for i, (a, b) in enumerate(rows):
            y = 290 + i * 110; d.rounded_rectangle((260, y - 42, W - 260, y + 42), 12, fill=(20, 27, 38))
            d.text((300, y), a, font=font(40), fill=TEAL, anchor="lm"); d.text((690, y), b, font=font(38, False), fill=WHT, anchor="lm")
        d.text((W // 2, 900), "影片中的達標數據為模擬情境", font=font(40), fill=YEL, anchor="mm")
    p = os.path.join(WORK, f"card_{kind}.png"); im.save(p); return p

def sim_badge():
    p = os.path.join(WORK, "badge.png")
    if os.path.exists(p): return p
    f = font(34); t = "模擬情境　示範用，非實測數據"; tw = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(t, font=f)
    im = Image.new("RGBA", (int(tw) + 60, 66), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((3, 3, im.width - 4, 62), 12, fill=(179, 38, 30, 240), outline=YEL, width=4)
    d.text((im.width // 2, 33), t, font=f, fill=(255, 255, 255), anchor="mm"); im.save(p); return p

def wrap(t, n=26):
    if len(t) <= n: return [t]
    k = (len(t) + 1) // 2; return [t[:k], t[k:]] if len(t) <= 2 * n else [t[i:i + n] for i in range(0, len(t), n)]
def sub_png(key, text):
    f = font(48); lines = wrap(text); tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tw = max(tmp.textlength(l, font=f) for l in lines); h = 30 + 64 * len(lines)
    im = Image.new("RGBA", (int(tw) + 70, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, h - 1), 16, fill=(0, 0, 0, 190))
    for i, l in enumerate(lines): d.text((im.width // 2, 15 + 64 * i + 32), l, font=f, fill=(255, 255, 255), anchor="mm")
    p = os.path.join(WORK, "clips", f"s_{key}.png"); im.save(p); return p

def raw_size():
    r = subprocess.run([FF, "-hide_banner", "-i", RAW], capture_output=True, encoding="utf-8", errors="replace")
    m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", r.stderr); return int(m[1]), int(m[2])

def crop_for(r):
    # 逐格擷取實際給的是 CSS 像素（不吃 deviceScaleFactor），所以依錄到的實際尺寸換算
    cw, ch = raw_size(); dsf = cw / VW
    x, y, w, h = [v * dsf for v in r]; pad = 22 * dsf
    x -= pad; y -= pad; w += 2 * pad; h += 2 * pad
    if w / h < 16 / 9: nw = h * 16 / 9; x -= (nw - w) / 2; w = nw
    else: nh = w * 9 / 16; y -= (nh - h) / 2; h = nh
    w = max(w, cw * 0.38); h = w * 9 / 16
    if w > cw: w, h = cw, ch
    x = min(max(0, x), cw - w); y = min(max(0, y), ch - h)
    return int(x) // 2 * 2, int(y) // 2 * 2, int(w) // 2 * 2, int(h) // 2 * 2

def line_clip(key, vin, vf, text, wav, voice_d, dur, badge=False):
    subs = []; parts = [p for p in re.split(r"(?<=[，、；：。])", text) if p.strip()]; tot = sum(len(p) for p in parts); t = LEAD
    for p in parts:
        span = voice_d * len(p) / tot; subs.append((t, t + span + (TAIL * 0.6 if p is parts[-1] else 0.05), re.sub(r"[，。、；：]+$", "", p))); t += span
    ins, flt = [], [f"[0:v]{vf},fps={FPS},format=yuv420p[v0]"]; last = "v0"; k = 1
    if badge:
        ins += ["-i", sim_badge()]; flt.append(f"[{last}][{k}:v]overlay=30:26[v{k}]"); last = f"v{k}"; k += 1
    for n, (a, b, s) in enumerate(subs):
        ins += ["-i", sub_png(f"{key}_{n}", s)]
        flt.append(f"[{last}][{k}:v]overlay=(W-w)/2:H-h-54:enable='between(t,{a:.2f},{b:.2f})'[v{k}]"); last = f"v{k}"; k += 1
    flt.append(f"[{k}:a]adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad[a]")
    out = os.path.join(WORK, "clips", f"c_{key}.mp4")
    subprocess.run([FF, "-y", "-loglevel", "error", *vin, *ins, "-i", wav, "-filter_complex", ";".join(flt), "-map", f"[{last}]", "-map", "[a]",
                    "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", out], check=True)
    return out

def build():
    sc = load_script(); tm = json.load(open(TIMING, encoding="utf-8")); mk = json.load(open(MARKS, encoding="utf-8"))
    clips = []; sim_on = False
    for si, seg in enumerate(sc["segments"]):
        for li, ln in enumerate(seg["lines"]):
            key = f"{si}_{li}"; T = tm[si][li]
            for a in ln.get("do", []):
                if "prep" in a: sim_on = bool(a["prep"])
                if "set" in a: sim_on = True
            if "card" in seg:
                vin = ["-loop", "1", "-framerate", str(FPS), "-t", f"{T['dur']:.3f}", "-i", card_png(seg["card"])]; vf = f"scale={W}:{H}"; badge = False
            else:
                vin = ["-ss", f"{mk['lines'][key]:.3f}", "-t", f"{T['dur']:.3f}", "-i", RAW]
                z = ln.get("zoom"); r = mk["rects"].get(key, {}).get(z) if z else None
                if r:
                    x, y, w, h = crop_for(r); vf = f"crop={w}:{h}:{x}:{y},scale={W}:{H}:flags=lanczos"; badge = sim_on
                else:
                    vf = f"scale={W}:{H}:flags=lanczos"; badge = False      # 全畫面時網頁自己的模擬標籤就在上方
            clips.append(line_clip(key, vin, vf, ln["t"], T["wav"], T["voice"], T["dur"], badge)); print("  ", key, round(T["dur"], 1), "秒", flush=True)
    lst = os.path.join(WORK, "clips.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{c.replace(chr(92), '/')}'\n" for c in clips))
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", OUT], check=True)
    print("完成", OUT, round(os.path.getsize(OUT) / 1048576, 1), "MB，長", round(probe(OUT), 1), "秒")

def frames():
    tm = json.load(open(TIMING, encoding="utf-8")); mk = json.load(open(MARKS, encoding="utf-8")); out = os.path.join(WORK, "chk"); os.makedirs(out, exist_ok=True)
    for key, t in mk["lines"].items():
        si, li = map(int, key.split("_")); d = tm[si][li]["dur"]
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{t + min(d * 0.7, d - 0.3):.2f}", "-i", RAW, "-frames:v", "1", "-vf", "scale=960:-1", os.path.join(out, f"{key}.jpg")])
    print("已輸出", out)

if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    steps = {"--bake": bake, "--tts": tts, "--record": record, "--frames": frames, "--build": build,
             "--shot": lambda: shot(sys.argv[2] if len(sys.argv) > 2 else "shot"),
             "--all": lambda: (bake(), tts(), record(), frames(), build())}
    steps.get(a, lambda: print(__doc__))()
