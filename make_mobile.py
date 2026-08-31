# -*- coding: utf-8 -*-
"""由 index.html（v2.9 定版）產生手機版 工地氣象監控_手機版.html

原則：**內容與版面結構完全不動**，只做三件事
  1. 移除原本 max-width:900px 的「堆疊可捲動」手機樣式
     —— 那個版本會把版面拆成一長條，跟桌機版長得不一樣
  2. 放寬字級下限，讓同一套六欄版面能整個縮進手機螢幕
  3. 研判列欄數的判斷不再看螢幕寬度，任何尺寸都排成一列

結果：手機看到的每一張卡、每一個數字都和桌機版一模一樣，只是等比縮小。

用法：
    python make_mobile.py
"""
import io, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "index.html")
OUT = os.path.join(HERE, "工地氣象監控_手機版.html")

o = io.open(SRC, encoding="utf-8").read()
s = o

# ---------- 1) 移除原本的窄螢幕堆疊樣式 ----------
i = s.find("  @media (max-width:900px){")
if i < 0:
    raise SystemExit("找不到 @media (max-width:900px) 區塊")
j = s.index("{", i)
depth, k = 0, j
while k < len(s):
    if s[k] == "{":
        depth += 1
    elif s[k] == "}":
        depth -= 1
        if depth == 0:
            break
    k += 1
removed = k + 1 - i
s = s[:i] + "  /* 手機版：不使用堆疊樣式，改以整體縮放呈現與桌機相同的版面 */" + s[k + 1:]

# ---------- 2) 放寬字級下限，讓版面縮得進手機 ----------
old_clamp = "html{font-size:clamp(8.5px,min(1.12vh,0.85vw),14px)}"
new_clamp = "html{font-size:clamp(3.2px,min(1.12vh,0.85vw),14px)}"
if old_clamp not in s:
    raise SystemExit("找不到根字級設定")
s = s.replace(old_clamp, new_clamp, 1)

# ---------- 直向分頁排版（橫向完全不受影響） ----------
PORTRAIT_CSS = """
  /* ============================================================
     直向手機：六欄版面塞不進 375px，硬縮字會小到看不見。
     改成分四頁顯示 —— 內容一張卡都不刪，只是不同時出現在同一畫面，
     這樣字級才夠大，也維持「不捲頁」。橫向完全不受這段影響。
     ============================================================ */
  .tabs{display:none}
  /* 手機版不顯示 LOGO（橫向、直向皆同），空間留給監控內容 */
  .brand #logo,.brand #logoFb{display:none}
  /* --- iOS 安全區域 ---
     viewport-fit=cover 會讓畫面延伸到瀏海／動態島與圓角底下，
     必須用 env(safe-area-inset-*) 把內容推回可視範圍，否則標題會被蓋住。
     高度改用 dvh：iOS Safari 的 100% 算的是版面視窗，與實際可視高度不符，
     會在畫面下方留一段空白。 */
  html,body{height:100vh;height:100dvh}
  body{padding:calc(.45rem + env(safe-area-inset-top))
               calc(.45rem + env(safe-area-inset-right))
               calc(.45rem + env(safe-area-inset-bottom))
               calc(.45rem + env(safe-area-inset-left))}

  /* --- 「目前位置」按鈕：手機上最常按的鈕，做成醒目的發光脈動 --- */
  #geo{background:var(--accent);color:#06202b;border-color:var(--accent);
       font-weight:800;position:relative;
       animation:geoPulse 1.9s ease-out infinite}
  @keyframes geoPulse{
    0%  {box-shadow:0 0 0 0 rgba(76,201,240,.75), 0 0 .5rem rgba(76,201,240,.55)}
    70% {box-shadow:0 0 0 .85rem rgba(76,201,240,0), 0 0 .9rem rgba(76,201,240,.85)}
    100%{box-shadow:0 0 0 0 rgba(76,201,240,0), 0 0 .5rem rgba(76,201,240,.55)}
  }
  #geo:active{transform:scale(.95)}
  /* 使用者若在系統設定關閉動畫效果，就只保留顏色與光暈，不跳動 */
  @media (prefers-reduced-motion:reduce){
    #geo{animation:none;box-shadow:0 0 .6rem rgba(76,201,240,.7)}
  }

  /* 橫向時鐘數字縮為原本的 0.75 倍（18.4→13.8rem、11→8.25vw）
     直向本來就不顯示時鐘，不受影響 */
  .clock .t{font-size:min(13.8rem,8.25vw)}
  .clock .t i{font-size:min(6rem,3.6vw)}
  @media (orientation:portrait){
    html{font-size:clamp(9px,min(1.45vh,3.05vw),16px)}

    /* --- 頂列壓縮：時鐘與標題同排，控制項縮小，把高度讓給主內容 --- */
    .top{flex-wrap:wrap;padding:.4rem .6rem;gap:.35rem;align-items:flex-start}
    .tl{flex:1 1 100%;order:1;gap:.35rem}
    .brand{font-size:1.35rem;gap:.45rem}
    .brand #logo,.brand #logoFb{height:2.6rem}
    .brand .bt b{font-size:.85rem;letter-spacing:.03em}
    .ctrl{flex-wrap:wrap;gap:.35rem}
    .ctrl .f label{font-size:.8rem}
    input,select{padding:.25rem .4rem;font-size:.95rem}
    .btn{padding:.28rem .6rem;font-size:.95rem}
    .w-q{width:7.2rem}.w-c{width:4.8rem}
    .stabox{min-width:0;flex:1 1 100%;white-space:normal;font-size:.95rem;padding:.3rem .5rem}
    .ctrl2{order:2;flex:1 1 100%;justify-content:flex-start;padding-top:0}
    .ctrl2 #lastup{font-size:.9rem;margin-bottom:0}
    /* 直向不顯示：時鐘、版本編號、地名搜尋、LOGO
       —— 手機本身就有時鐘，這幾項讓出高度給實際監控內容 */
    .clock{display:none}
    .ctrl .sugg{display:none}

    .place{padding:.3rem .6rem;gap:.4rem}
    .place .nm{font-size:1.3rem}
    .place .mt{font-size:.88rem;white-space:normal}
    .tag{font-size:.85rem;padding:.08rem .5rem}

    /* --- 分頁按鈕 --- */
    .tabs{display:flex;flex:0 0 auto;gap:.3rem}
    .tabs button{flex:1;background:var(--panel);border:1px solid var(--line);
                 color:var(--tx2);border-radius:.6rem;padding:.4rem .15rem;
                 font-size:1rem;font-weight:700;font-family:inherit;cursor:pointer;
                 white-space:nowrap}
    .tabs button.on{background:var(--accent);color:#06202b;border-color:var(--accent)}

    /* --- 主網格：每頁兩個面板，各佔滿整個高度 --- */
    .main{display:grid;gap:.45rem;grid-template-columns:1fr 1fr;
          grid-template-rows:minmax(0,1fr)!important}
    .main>.panel{display:none!important;grid-column:auto!important;grid-row:auto!important}
    body[data-p="p1"] .g-rain,body[data-p="p1"] .g-env,
    body[data-p="p2"] .g-wind,body[data-p="p2"] .g-cw{display:flex!important}
    /* 雷達與趨勢圖需要寬度，改上下堆疊 */
    body[data-p="p3"] .main{grid-template-columns:1fr;
                            grid-template-rows:minmax(0,1.15fr) minmax(0,1fr)!important}
    body[data-p="p3"] .g-rdr,body[data-p="p3"] .g-cr{display:flex!important}
    body[data-p="p4"] .main{grid-template-columns:1fr}
    body[data-p="p4"] .g-al{display:flex!important}

    /* 面板標題不換行（否則「降雨監控」會斷成兩行），副標超出以省略號處理 */
    .ph{flex-wrap:nowrap;white-space:nowrap;overflow:hidden;
        font-size:1.05rem;margin-bottom:.35rem}
    .ph em{min-width:0;flex:0 1 auto}
    .ph em{font-size:.82rem}

    .card{padding:.35rem .5rem}
    .card .k{font-size:1rem}
    .card .v{font-size:2.8rem}
    .card .v small{font-size:1.15rem}
    .card .n{font-size:.88rem;white-space:normal}

    /* 研判卡單欄堆疊，字級回到正常大小 */
    .alerts{grid-auto-rows:minmax(0,1fr)}
    .alerts.dense .al{padding:.45rem .8rem;border-left-width:.45rem}
    .alerts.dense .al .t{font-size:1.1rem}
    .alerts.dense .al .m{font-size:1.7rem}
    .alerts.dense .al .d{font-size:1.05rem;-webkit-line-clamp:3}

    /* --- 底列：日期與跑馬燈各佔一排，否則跑馬燈會被擠成 0 寬 --- */
    .botbar{flex-wrap:wrap;padding:.35rem .6rem;gap:.3rem}
    .bdate{font-size:1.25rem;flex:1 1 100%}
    .banner{flex:1 1 100%;font-size:1.15rem;padding:.25rem .6rem;gap:.5rem}
    .banner .bx{font-size:.95rem;padding:.22rem .6rem}
  }
"""
s = s.replace("</style>", PORTRAIT_CSS + "</style>", 1)

# 分頁按鈕（插在地點列之後）
TABS_HTML = """
  <div class="tabs" id="tabs">
    <button data-p="p1" class="on">降雨・氣溫</button>
    <button data-p="p2">風速・地震</button>
    <button data-p="p3">雷達・趨勢</button>
    <button data-p="p4">安全研判</button>
  </div>
"""
anchor = "  <!-- 主網格 -->"
if anchor not in s:
    raise SystemExit("找不到主網格註解")
s = s.replace(anchor, TABS_HTML + anchor, 1)

# 分頁切換
TAB_JS = """
/* ---------- 直向分頁切換（橫向時分頁列隱藏，不影響版面） ---------- */
document.body.dataset.p="p1";
$("tabs").addEventListener("click",function(e){
  const b=e.target.closest("button"); if(!b) return;
  document.body.dataset.p=b.dataset.p;
  [...this.children].forEach(function(x){ x.className=(x===b)?"on":""; });
  layoutAlerts();
});
window.addEventListener("orientationchange",function(){ setTimeout(layoutAlerts,250); });

loadCfg();"""
s = s.replace("loadCfg();", TAB_JS, 1)

# ---------- 3) 研判列欄數不再看螢幕寬度 ----------
old_js = '(window.innerWidth>900) ? ("repeat("+alertCount+",minmax(0,1fr))") : "";'
new_js = ('window.matchMedia("(orientation:portrait)").matches\n'
          '    ? "1fr 1fr"                                 // 直向：兩欄，說明才放得下\n'
          '    : ("repeat("+alertCount+",minmax(0,1fr))"); // 橫向：一整排')
if old_js not in s:
    raise SystemExit("找不到研判列欄數判斷")
s = s.replace(old_js, new_js, 1)

# ---------- 4) 標題與手機 meta ----------
# 手機版標題文字（桌機定版不受影響）
s = s.replace('<span class="bt">工地環境安全即時監控系統<b>',
              '<span class="bt">現地環境氣象監測<b>', 1)

s = s.replace("<title>工地環境安全即時監控系統</title>",
              "<title>現地環境氣象監測</title>\n"
              '<meta name="robots" content="noindex,nofollow,noarchive">\n'
              '<meta name="theme-color" content="#15181d">\n'
              '<meta name="mobile-web-app-capable" content="yes">\n'
              '<meta name="apple-mobile-web-app-capable" content="yes">\n'
              '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
              '<meta name="apple-mobile-web-app-title" content="現地氣象">', 1)

s = s.replace('<meta name="viewport" content="width=device-width, initial-scale=1">',
              '<meta name="viewport" content="width=device-width,initial-scale=1,'
              'viewport-fit=cover,user-scalable=no">', 1)

io.open(OUT, "w", encoding="utf-8").write(s)

print("已產生：%s（%.0f KB）" % (os.path.basename(OUT), os.path.getsize(OUT) / 1024.0))
print("移除堆疊樣式 %d 字元，其餘內容未更動。" % removed)
print("")
print("內容一致性檢查（手機版 vs 桌機定版）：")


def count(txt, pat):
    return len(re.findall(pat, txt))


ok = True
for label, pat in [("數據卡 card(", r"card\("),
                   ("研判 alertBox(", r"alertBox\("),
                   ("面板 panel", r'class="panel'),
                   ("疊層 ov", r'class="ov '),
                   ("圖表 bars(", r"bars\(")]:
    a, b = count(o, pat), count(s, pat)
    same = (a == b)
    ok = ok and same
    print("  %-16s 原檔 %3d ／ 手機版 %3d  %s" % (label, a, b, "一致" if same else "!! 不一致"))
print("")
print("內容完全一致。" if ok else "!! 內容有落差，請檢查。")
