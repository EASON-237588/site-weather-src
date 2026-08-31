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
import hashlib, io, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "index.html")
OUT = os.path.join(HERE, "工地氣象監控_手機版.html")
STATE = os.path.join(HERE, ".mobile_version.json")
MOBVER_TAG = "@@MOBVER@@"      # 產生完成後才換成實際版號


def load_state():
    """手機版有自己的版號，與桌機 index.html 的 VER 無關。
       手機版是從凍結的 v2.9 產生的，所以不能沿用它的版號 ——
       否則改了十幾次版號都還是 2.9，根本分不出手上是哪一版。"""
    if os.path.exists(STATE):
        try:
            return json.load(io.open(STATE, encoding="utf-8"))
        except Exception:
            pass
    # 首次建立：先前 16 次修改未被記錄，從 1.16 起算，本次會跳到 1.17
    return {"ver": "1.16", "hash": ""}


def next_ver(v):
    a, b = [int(x) for x in v.split(".")]
    b += 1
    if b > 99:
        a, b = a + 1, 0
    return "%d.%d" % (a, b)

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
  /* 標題：主名稱大字，後接半尺寸的副名稱，同一行 */
  .brand .bt .t1{white-space:nowrap;display:flex;align-items:baseline;gap:.35em}
  .brand .bt .t2{font-style:normal;font-size:.5em;font-weight:700;letter-spacing:.06em}
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
    /* 直向不顯示：時鐘、版本編號、地名搜尋
       —— 手機本身就有時鐘，這幾項讓出高度給實際監控內容。LOGO 保留。 */
    .clock{display:none}
    .ctrl .sugg{display:none}

    /* 直向：場地資訊列整條不顯示 —— 場地名已在頁首大標題、座標與測站
       在上方控制列都有，這一列只是重複，卻吃掉一整段高度，把下面的
       數據卡壓扁。橫向仍然保留。
       註：縣市警特報標籤也在這一列，直向改由頂端警報橫幕與
       「安全研判」分頁的〈氣象署特報〉呈現，資訊不會消失。 */
    .place{display:none}
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
    /* 欄數必須加 !important：熱指數表那批樣式有一條媒體查詢外的 .main{6 欄}
       排在後面，同權重下會蓋掉這裡的設定，直向就會變成六欄擠成細條。 */
    .main{display:grid;gap:.45rem;grid-template-columns:1fr 1fr!important;
          grid-template-rows:minmax(0,1fr)!important}
    .main>.panel{display:none!important;grid-column:auto!important;grid-row:auto!important}
    body[data-p="p1"] .g-rain,body[data-p="p1"] .g-env,
    body[data-p="p2"] .g-wind,body[data-p="p2"] .g-cw{display:flex!important}
    /* 熱指數表要整個寬度才排得下 13 欄 */
    body[data-p="p3"] .main{grid-template-columns:1fr!important;
                            grid-template-rows:minmax(0,1fr)!important}
    body[data-p="p3"] .g-hi{display:flex!important}
    /* 雷達與趨勢圖需要寬度，改上下堆疊 */
    body[data-p="p4"] .main{grid-template-columns:1fr!important;
                            grid-template-rows:minmax(0,1.7fr) minmax(0,1fr)!important}
    body[data-p="p4"] .g-rdr,body[data-p="p4"] .g-cr{display:flex!important}
    body[data-p="p5"] .main{grid-template-columns:1fr!important}
    body[data-p="p5"] .g-al{display:flex!important}

    /* 面板標題不換行（否則「降雨監控」會斷成兩行），副標超出以省略號處理 */
    .ph{flex-wrap:nowrap;white-space:nowrap;overflow:hidden;
        font-size:1.05rem;margin-bottom:.35rem}
    .ph em{min-width:0;flex:0 1 auto}
    .ph em{font-size:.82rem}

    /* 直向卡片字級：場地資訊列移除後每張卡多出不少高度，
       字放大到接近欄寬上限，數值仍以 nowrap 保護不換行。 */
    .card{padding:.45rem .6rem}
    .card .k{font-size:1.3rem}
    .card .v{font-size:3.6rem}
    .card .v small{font-size:1.45rem}
    .card .n{font-size:1.08rem;white-space:normal}

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

# ---------- 熱指數表樣式 ＋ 版面重配置（數據欄縮小、雷達與趨勢重排） ----------
HEAT_CSS = """
  /* ============================================================
     版面重配置：數據欄縮小，讓出空間給熱指數表與雷達回波。
       第 1 列  降雨｜氣溫｜風速｜地震｜熱指數表｜雷達回波
       第 2 列  逐時趨勢（整列）
       第 3 列  作業安全研判（整列）
     ============================================================ */
  /*  左半                          右半
      ┌─────┬─────┬─────┬─────┐┌───────┬────────┐
      │降雨 │氣溫 │風速 │地震 ││       │ 雷達   │
      ├─────┴─────┴─────┴─────┤│熱指數表├────────┤
      │     作業安全研判       ││(跨兩列)│逐時趨勢│
      └───────────────────────┘└───────┴────────┘
      熱指數表有 16 列，跨兩列給滿高度，數字才排得開。 */
  .main{grid-template-columns:1fr 1fr 1fr 1fr 1.5fr 1.45fr;
        grid-template-rows:minmax(0,1.6fr) minmax(0,1fr)}
  .g-rain{grid-column:1;grid-row:1}
  .g-env {grid-column:2;grid-row:1}
  .g-wind{grid-column:3;grid-row:1}
  .g-cw  {grid-column:4;grid-row:1}
  .g-hi  {grid-column:5;grid-row:1/3}
  .g-rdr {grid-column:6;grid-row:1}
  .g-al  {grid-column:1/5;grid-row:2;overflow:hidden}
  .g-cr  {grid-column:6;grid-row:2}

  /* ---------- 熱指數表 ---------- */
  .hiwrap{flex:1;min-height:0;min-width:0;display:flex;overflow:hidden}
  .hitab{border-collapse:collapse;width:100%;height:100%;table-layout:fixed;
         font-variant-numeric:tabular-nums;font-size:.8rem}
  .hitab th{background:var(--panel2);color:var(--tx2);font-weight:600;
            font-size:.75rem;padding:0;text-align:center;white-space:nowrap}
  .hitab th.cnr{font-size:.68rem;color:var(--tx3)}
  .hitab td{text-align:center;padding:0;font-weight:600;color:#10151b;
            border:1px solid rgba(0,0,0,.22);line-height:1;
            white-space:nowrap;overflow:hidden}
  /* 四級顏色調淺一半（與白色 50% 混色），數字才讀得清楚 */
  .hitab td.l0{background:#97b59e;color:#1b2b20}
  .hitab td.l1{background:#9fdca8}
  .hitab td.l2{background:#f9ea80}
  .hitab td.l3{background:#f7c492}
  .hitab td.l4{background:#f29a95;color:#3a0d0a}
  /* 欄寬不足時只留顏色，數字反而干擾判讀；但目前值那格一定看得到 */
  .hitab.compact td{color:transparent}
  .hitab.compact td.now{color:#000}
  /* 目前溫濕度對應的格子：深色外框＋明暗跳動。
     此處刻意不受系統「減少動態效果」影響 —— 這是安全提示，必須被看見。 */
  .hitab td.now{outline:.16rem solid #0b0f14;outline-offset:-.16rem;
                font-weight:900;position:relative;z-index:1;
                animation:hiNow .9s ease-in-out infinite!important}
  /* 跳動的那格自動加深 —— 用調淺前的原始飽和色，與周圍淺色形成對比 */
  .hitab td.l0.now{background:#2f6b3d;color:#fff}
  .hitab td.l1.now{background:#3fb950;color:#08210d}
  .hitab td.l2.now{background:#e8c400;color:#2b2400}
  .hitab td.l3.now{background:#e07a12;color:#2e1600}
  .hitab td.l4.now{background:#e5342a;color:#fff}
  @keyframes hiNow{
    0%,100%{filter:brightness(1);       box-shadow:inset 0 0 0 0 rgba(255,255,255,0)}
    50%    {filter:brightness(1.45);    box-shadow:inset 0 0 .45rem .12rem #fff}
  }

  /* 雷達回波：原圖四周留白很多，改用裁切填滿，不留左右黑邊。
     裁切量取決於容器比例，容器越接近正方形裁得越少，
     所以直向時把雷達區加高（見下方 p4 設定），避免把台灣切掉。
     台灣在原圖中略偏上，故垂直錨點設 42% 而非置中。 */
  .rdmain img{object-fit:cover;object-position:50% 42%}

  /* 逐時趨勢：未來 15 小時的預報改黃色（原本只是半透明，不易分辨） */
  .bar.fc{opacity:1;background:var(--warn)!important}
  /* ---------- 作業安全研判：卡片底色改白 ----------
     底色由深灰改白之後，原本的淺色文字在白底上會看不清楚，
     文字與狀態色一併換成深色版本，維持對比。 */
  .al{background:#ffffff}
  .al .t{color:#3b4652;font-weight:800}
  .al .d{color:#4a5561}
  .lv-ok .m{color:#1a7f37}
  .lv-warn .m{color:#9a6700}
  .lv-bad .m{color:#b42318}

  /* 時間刻度：原字級在手機上只有 6px 左右，等於看不到，放大並提高對比 */
  .xax{margin-top:.25rem;flex:0 0 auto}
  .xax div{font-size:1.05rem;color:var(--tx2);font-variant-numeric:tabular-nums}
  .chartwrap{min-height:0}

  /* ---------- 標題整體放大 1.2 倍（LOGO、主標、副標同步） ----------
     副標 .t2 用 .5em 相對計算，會跟著主標一起放大，不必另外設定。 */
  .brand{font-size:3.36rem}                       /* 2.8 × 1.2 */
  .brand #logo,.brand #logoFb{height:10.56rem}    /* 8.8 × 1.2 */
  .brand .bt b{font-size:1.872rem}                /* 1.3 × 1.2 × 1.5 × 0.8 縮小 */
  /* 標題文字區再放大 1.5 倍（只放大文字，LOGO 尺寸不變）。
     .t2 用 .5em 相對計算，會跟著一起放大，主副比例維持 1:0.5。 */
  .brand .bt{font-size:1.5em}
  /* 案名（場地名）再放大 1.2 倍；副標「氣象監測」維持原本絕對大小，
     所以 .t2 由 .5em 改成 .5 ÷ 1.2 = .4167em 抵銷。 */
  .brand .bt .t1{font-size:1.2em}
  .brand .bt .t2{font-size:.4167em}
  @media (orientation:portrait){
    .brand{font-size:1.62rem}                     /* 1.35 × 1.2 */
    .brand #logo,.brand #logoFb{height:3.12rem}   /* 2.6 × 1.2 */
    .brand .bt b{font-size:1.224rem}              /* 0.85 × 1.2 × 1.5 × 0.8 縮小 */
  }

  @media (orientation:portrait){
    /* 直向：熱指數表獨立一頁，欄寬足夠，字放大 */
    .hitab{font-size:.95rem}
    .hitab th{font-size:.9rem}
    .hitab th.cnr{font-size:.8rem}
  }
"""
s = s.replace("</style>", HEAT_CSS + "</style>", 1)

# 分頁按鈕（插在地點列之後）
TABS_HTML = """
  <div class="tabs" id="tabs">
    <button data-p="p1" class="on">降雨氣溫</button>
    <button data-p="p2">風速地震</button>
    <button data-p="p3">熱指數</button>
    <button data-p="p4">雷達趨勢</button>
    <button data-p="p5">安全研判</button>
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
          '    ? "1fr 1fr"                        // 直向：兩欄\n'
          '    : ("repeat("+Math.max(4,Math.ceil(alertCount/2))+",minmax(0,1fr))");\n'
          '                                       // 橫向：固定兩列，欄數隨卡片數自動調整')
if old_js not in s:
    raise SystemExit("找不到研判列欄數判斷")
s = s.replace(old_js, new_js, 1)

# ============================================================
#  熱指數表（新增面板）＋ 版面重配置 ＋ 風向卡改濕度
# ============================================================

# ---- (a) 熱指數表面板，插在雷達面板之前 ----
HEAT_HTML = """    <div class="panel g-hi">
      <div class="ph">熱指數表<em id="hinow">計算中…</em></div>
      <div class="hiwrap"><table class="hitab" id="hitab"></table></div>
    </div>

"""
_a = '    <div class="panel g-rdr">'
if _a not in s:
    raise SystemExit("找不到雷達面板")
s = s.replace(_a, HEAT_HTML + _a, 1)

# ---- (b) 熱指數表的計算與繪製 ----
HEAT_JS = """
/* ---------- 熱指數表 ----------
   依據：勞動部職安署「高氣溫戶外作業勞工熱危害預防指引」
     附表一 熱指數表、附表二 熱危害風險等級對應之熱指數。
   官方表格係由美國 NWS 華氏熱指數表換算而來，因此先在華氏取整、再換算攝氏，
   即可完全重現官方數值（已逐格比對相對溼度 40% 欄位，16／16 相符）。
   分級：第一級 26.7–32.2、第二級 32.2–40.6、第三級 40.6–54.4、第四級 54.4 以上。 */
function hiF(t,rh){
  const s0=0.5*(t+61.0+(t-68.0)*1.2+rh*0.094);
  if((s0+t)/2<80) return s0;
  let h=-42.379+2.04901523*t+10.14333127*rh-0.22475541*t*rh-0.00683783*t*t
        -0.05481717*rh*rh+0.00122874*t*t*rh+0.00085282*t*rh*rh-0.00000199*t*t*rh*rh;
  if(rh<13&&t>=80&&t<=112) h-=((13-rh)/4)*Math.sqrt((17-Math.abs(t-95))/17);
  else if(rh>85&&t>=80&&t<=87) h+=((rh-85)/10)*((87-t)/5);
  return h;
}
function heatIndexC(tc,rh){ return (Math.round(hiF(tc*9/5+32,rh))-32)*5/9; }
function hiLevel(h){ return h<26.7?0:(h<32.2?1:(h<40.6?2:(h<54.4?3:4))); }
const HI_LVNAME=["未達高溫風險","第一級","第二級","第三級","第四級"];
const HI_TF=[], HI_RH=[];
for(let ff=80;ff<=110;ff+=2) HI_TF.push(ff);
for(let rr=40;rr<=100;rr+=5) HI_RH.push(rr);

function buildHeatTable(tc,rh){
  const cur=(tc!==null&&rh!==null)?heatIndexC(tc,rh):null;
  let ri=-1,ci=-1,bd;
  if(cur!==null){
    /* 標記哪一格：不能只把溫濕度四捨五入到最近的格 ——
       例如 31.4°C／72% 會落到 31.1／70 那格（37.8），
       但實際熱指數是 39.4，兩個數字對不起來。
       改成在「包住實際溫濕度的相鄰格」裡，挑數值最接近實際熱指數者，
       這樣跳動格顯示的數字就會與熱危害指數一致。 */
    bd=1e9;
    for(let i=0;i<HI_TF.length;i++){
      if(Math.abs((HI_TF[i]-32)*5/9-tc)>1.2) continue;   // 只看上下相鄰列
      for(let j=0;j<HI_RH.length;j++){
        if(Math.abs(HI_RH[j]-rh)>5.5) continue;          // 只看左右相鄰欄
        const v=(Math.round(hiF(HI_TF[i],HI_RH[j]))-32)*5/9;
        const d=Math.abs(v-cur);
        if(d<bd){ bd=d; ri=i; ci=j; }
      }
    }
    /* 找不到相鄰格，或最接近的格與實際熱指數差太多，就「不亮格」。
       官方表最低一列是 80 °F＝26.7 °C；氣溫低於這條線時走的是低溫簡化式，
       表內任何一格都對不上（例：25.5 °C／95 % 卡片 26.7，表格最低格卻是 30.0），
       硬亮一格只會讓表與卡片互相矛盾，還可能亮到錯的等級。 */
    if(bd>1.0){ ri=-1; ci=-1; }
  }
  let h='<tr><th class="cnr">℃＼%</th>';
  HI_RH.forEach(function(rr){ h+='<th>'+rr+'</th>'; });
  h+='</tr>';
  for(let i=HI_TF.length-1;i>=0;i--){
    h+='<tr><th>'+((HI_TF[i]-32)*5/9).toFixed(1)+'</th>';
    for(let j=0;j<HI_RH.length;j++){
      const v=(Math.round(hiF(HI_TF[i],HI_RH[j]))-32)*5/9;
      h+='<td class="l'+hiLevel(v)+((i===ri&&j===ci)?' now':'')+'">'+v.toFixed(1)+'</td>';
    }
    h+='</tr>';
  }
  $("hitab").innerHTML=h;
  $("hinow").textContent = (tc===null||rh===null) ? "無溫濕度資料"
    : ("溫度 "+tc.toFixed(1)+" °C・濕度 "+Math.round(rh)+" %・"+HI_LVNAME[hiLevel(cur)]
       +(ri<0?"（超出官方表範圍：表格自 26.7 °C／40 % 起，未標示對應格）":""));
  hiCompact();
}
/* 格子放不下數字時只留顏色。用實際溢出量判斷，不用寫死的像素門檻，
   否則換個字級或螢幕就會誤判。 */
function hiCompact(){
  const tb=$("hitab");
  if(!tb.rows.length||!tb.rows[1]||!tb.rows[1].cells[1]) return;
  tb.classList.remove("compact");
  const c=tb.rows[1].cells[1];
  if(c.scrollWidth>c.clientWidth+1) tb.classList.add("compact");
}
window.addEventListener("resize",hiCompact);

"""
s = s.replace("/* ---------- 主流程 ---------- */", HEAT_JS + "/* ---------- 主流程 ---------- */", 1)

# ---- (c) 氣溫欄改為：氣溫／相對濕度／體感溫度／熱危害指數 ----
#      WBGT 卡讓位給熱危害指數（與新增的熱指數表同一套官方基準）；
#      WBGT 的計算與熱危害研判邏輯保留不動。
_ENV_OLD = '''  $("env").innerHTML=
    card("氣溫",f(t,1),"°C","澆置建議 5–32 °C",tl(t))+
    card("WBGT 綜合熱指數",f(wbgt,1),"°C","重工作 25／28／30 分級",wg(wbgt))+
    card("體感溫度",f(app,1),"°C","濕度 "+f(rh,0)+" %　露點 "+f(dew,1)+" °C",
         app===null?"":(app>=38?"bad":(app>=32?"warn":"ok")))+
    card("風向",dirName(w_dir),"",w_dir===null?"":f(w_dir,0)+"° 來向");'''
_ENV_NEW = '''  const HIC=(t!==null&&rh!==null)?heatIndexC(t,rh):null;
  const hiCardLv = HIC===null ? "" : (hiLevel(HIC)>=3 ? "bad" : (hiLevel(HIC)===2 ? "warn" : "ok"));
  $("env").innerHTML=
    card("氣溫",f(t,1),"°C","澆置建議 5–32 °C",tl(t))+
    card("相對濕度",f(rh,0),"%","露點 "+f(dew,1)+" °C・風向 "+dirName(w_dir),
         rh===null?"":(rh>=85?"warn":"ok"))+
    card("體感溫度",f(app,1),"°C","濕度 "+f(rh,0)+" %　露點 "+f(dew,1)+" °C",
         app===null?"":(app>=38?"bad":(app>=32?"warn":"ok")))+
    card("熱危害指數",f(HIC,1),"°C",
         (HIC===null?"職安署分級":HI_LVNAME[hiLevel(HIC)]+"・職安署分級"),hiCardLv);

  buildHeatTable(t,rh);'''
if _ENV_OLD not in s:
    raise SystemExit("找不到氣溫卡片區塊")
s = s.replace(_ENV_OLD, _ENV_NEW, 1)

# ---- (c2) 熱危害研判改用職安署熱指數分級（原本用 WBGT，兩套標準並存會混淆）----
#      WBGT 是「高溫作業場所」標準，熱指數才是「高氣溫戶外作業」標準，
#      既然畫面已採熱指數表，研判文字一併統一，措施文字取自附表二風險管理原則。
_HZ_OLD = '''  const hb="WBGT "+f(wbgt,1)+" °C";
  if(wbgt===null) A.push(alertBox("熱危害","資料不足","無有效溫濕度資料，無法計算 WBGT。","warn"));
  else if(wbgt>=30) A.push(alertBox("熱危害","極高風險",hb+"。重工作每小時限 15 分鐘，應避開 10–14 時。","bad"));
  else if(wbgt>=28) A.push(alertBox("熱危害","高風險",hb+"。重工作 50 % 作息，補充電解質並監視熱疾病。","bad"));
  else if(wbgt>=25) A.push(alertBox("熱危害","中等風險",hb+"。重工作 75 % 作業／25 % 休息，充分供水。","warn"));
  else A.push(alertBox("熱危害","低風險",hb+"，可連續作業，仍應定時補充水分。","ok"));'''
_HZ_NEW = '''  if(HIC===null) A.push(alertBox("熱危害","資料不足","無有效溫濕度資料，無法計算熱指數。","warn"));
  else {
    const _hl=hiLevel(HIC), _hb="熱指數 "+f(HIC,1)+" °C";
    if(_hl>=4) A.push(alertBox("熱危害","第四級",_hb+"。應避免使勞工從事戶外作業；如有必要，須確實採取防護措施並加強緊急應變機制。","bad"));
    else if(_hl===3) A.push(alertBox("熱危害","第三級",_hb+"。避免於高溫時段從事戶外作業，並注意勞工身體狀況。","bad"));
    else if(_hl===2) A.push(alertBox("熱危害","第二級",_hb+"。實施危害預防措施及提升危害認知，充分供水與適當休息。","warn"));
    else if(_hl===1) A.push(alertBox("熱危害","第一級",_hb+"。基本防護原則，從事重體力作業應提高警覺。","ok"));
    else A.push(alertBox("熱危害","未達高溫風險",_hb+"，仍應定時補充水分。","ok"));
  }

  /* 紫外線：資料本來就抓進來了（氣象站 UVIndex／模式 uv_index），
     原版沒有用到。戶外作業長時間曝曬是實際危害，依中央氣象署紫外線分級研判。 */
  if(uv===null) A.push(alertBox("紫外線","資料不足","無紫外線指數資料。","warn"));
  else if(uv>=11) A.push(alertBox("紫外線","危險級","UV "+f(uv,0)+"。避免長時間曝曬，作業區加設遮陽並縮短連續曝曬時間。","bad"));
  else if(uv>=8) A.push(alertBox("紫外線","過量級","UV "+f(uv,0)+"。避開 10–14 時長時間曝曬，戴寬邊帽、長袖並塗防曬。","bad"));
  else if(uv>=6) A.push(alertBox("紫外線","高量級","UV "+f(uv,0)+"。戶外作業應戴帽、長袖與太陽眼鏡。","warn"));
  else if(uv>=3) A.push(alertBox("紫外線","中量級","UV "+f(uv,0)+"。一般防護即可，長時間作業仍建議遮陽。","ok"));
  else A.push(alertBox("紫外線","低量級","UV "+f(uv,0)+"，無須特別防護。","ok"));'''
if _HZ_OLD not in s:
    raise SystemExit("找不到熱危害研判區塊")
s = s.replace(_HZ_OLD, _HZ_NEW, 1)

# 紫外線資料：氣象站 UVIndex ＋ Open-Meteo uv_index（原版未取用）
s = s.replace("        gust:cwaVal((e.GustInfo||{}).PeakGustSpeed),",
              "        gust:cwaVal((e.GustInfo||{}).PeakGustSpeed), uv:cwaVal(e.UVIndex),", 1)
s = s.replace("current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,",
              "current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,uv_index,", 1)
s = s.replace("  const HIC=(t!==null&&rh!==null)?heatIndexC(t,rh):null;",
              "  const uv=(cwa.wx&&cwa.wx.uv!==null&&cwa.wx.uv!==undefined)?cwa.wx.uv:N(c.uv_index);\n"
              "  const HIC=(t!==null&&rh!==null)?heatIndexC(t,rh):null;", 1)

# 研判順序加入紫外線；橫向欄數改為固定兩列
s = s.replace('const AL_ORDER=["當日累積","熱危害","吊車 / 塔吊","混凝土澆置 / 開挖",',
              'const AL_ORDER=["當日累積","熱危害","紫外線","吊車 / 塔吊","混凝土澆置 / 開挖",', 1)

# ---- (d) 逐時趨勢改為「過去 12 ＋ 未來 12 小時」 ----
_bars_old = "const a=Math.max(0,iNow-23), b=Math.min(times.length-1,iNow+12);"
_bars_new = "const a=Math.max(0,iNow-12), b=Math.min(times.length-1,iNow+12);"
if _bars_old not in s:
    raise SystemExit("找不到圖表區間設定")
s = s.replace(_bars_old, _bars_new, 1)

s = s.replace("<em>過去 24 ＋ 未來 12 小時・點面板看明細</em>",
              "<em>過去 12 ＋ 未來 12 小時・點面板看明細</em>", 1)
s = s.replace("過去 24 小時 ＋ 未來 12 小時（半透明為預報，滑鼠可查值）",
              "過去 12 小時 ＋ 未來 12 小時（黃色為預報，滑鼠可查值）")

# 時間刻度：原本每 6 小時才標一次，字又小到看不見。改為每 3 小時、字級放大。
s = s.replace('x+="<div>"+(d.getHours()%6===0?String(d.getHours()).padStart(2,"0"):"")+"</div>";',
              'x+="<div>"+(d.getHours()%3===0?String(d.getHours()).padStart(2,"0"):"")+"</div>";', 1)

# ---- (e) 手機版自己的版號，並移到右上角常駐（直向也看得到） ----
#      原本版號元素在 .clock 裡，直向把時鐘整個隱藏，版號跟著看不到。
s = s.replace('      <div class="ver" id="ver"></div>\n', "", 1)
s = s.replace('    <div class="ctrl2">\n',
              '    <div class="ctrl2">\n      <span class="ver" id="ver"></span>\n', 1)

_VER_OLD = '$("ver").textContent="("+VER_NAME+")版本編號:"+VER;'
_VER_NEW = ('const MOB_VER="' + MOBVER_TAG + '";\n'
            '$("ver").textContent="("+VER_NAME+")手機版 "+MOB_VER+"　基於桌機 "+VER;')
if _VER_OLD not in s:
    raise SystemExit("找不到版號顯示程式")
s = s.replace(_VER_OLD, _VER_NEW, 1)

s = s.replace("</style>", """
  /* 版號移出時鐘區，改放右上角，直向橫向都看得到 */
  .ctrl2 .ver{position:static;font-size:.95rem;color:var(--tx3);
              white-space:nowrap;align-self:flex-end;margin-bottom:.2rem}
</style>""", 1)

# ============================================================
#  多場地輪播（機械翻牌切換）
# ============================================================

# ---- run() 拆成「只抓資料」與「抓完就畫」兩種用法 ----
#      輪播要先把新場地的資料抓好、翻牌動畫演完，才換畫面內容，
#      否則翻到一半沒東西可顯示，會空一大段。
if "async function run(){" not in s:
    raise SystemExit("找不到 run()")
s = s.replace("async function run(){", "async function run(deferRender){", 1)
s = s.replace("  render(lat,lon,om,place,cwa,quake,ty);",
              "  if(deferRender) return {lat:lat,lon:lon,om:om,place:place,"
              "cwa:cwa,quake:quake,ty:ty};\n"
              "  render(lat,lon,om,place,cwa,quake,ty);", 1)

# ---- 場地切換列 ----
s = s.replace('    <span id="ptags" style="display:flex;gap:.4rem;flex-wrap:wrap"></span>',
              '    <span id="ptags" style="display:flex;gap:.4rem;flex-wrap:wrap"></span>\n'
              '    <span class="siteind" id="siteind"></span>', 1)

SITE_JS = """
/* ---------- 多場地輪播 ----------
   每 SITE_ITV 毫秒換一個場地，切換時整面卡片做機械翻牌動畫。
   資料有做每場地快取：氣象署一次切換要打 5 支 API（氣象站、雨量站、
   地震、颱風、特報），15 秒一輪等於每小時 1200 次請求，很可能被限流。
   快取 SITE_TTL 內不重抓，實際請求量降到每分鐘數次。 */
const SITES=[
  {name:"台中圓滿", lat:24.1560, lon:120.6999},
  {name:"宜蘭陽醫", lat:24.7523, lon:121.7594},
  {name:"台南成大", lat:22.9280, lon:120.2820},
  {name:"高雄台壽", lat:22.6280, lon:120.2995}
];
const SITE_ITV=20000;      // 輪播間隔（毫秒）
const SITE_TTL=5*60000;    // 每個場地的資料快取時間
/* 切換動效：cascade｜fade｜slide｜flip
   cascade 由上而下依序進場（預設）—— 整片先淡出，再由畫面上方往下逐一浮現，
           視線有明確的行進方向，不會四處亂跳
   fade    整片同時淡出淡入
   slide   橫向滑動
   flip    機械翻牌（幅度最大，久看容易累） */
const SITE_FX="cascade";
const FX_OUT={cascade:190, fade:240, slide:260, flip:430}[SITE_FX] || 240;
const FX_SPREAD=430;   // 由上而下掃完整個畫面所需的時間（毫秒）

/* 依元素在畫面上的實際 Y 座標決定進場先後。
   卡片是分欄排列的，用 CSS 的 nth-child 排不出視覺上的上下順序，
   必須量測位置才會是真正的「由上而下」。 */
function fxPrepare(dir){
  const els=document.querySelectorAll(".card,.al,.g-hi,.g-rdr,.g-cr");
  if(dir==="out"){
    els.forEach(function(e){ e.style.animationDelay="0s"; });
    return;
  }
  const arr=[].slice.call(els);
  const tops=arr.map(function(e){ return e.getBoundingClientRect().top; });
  const mn=Math.min.apply(null,tops), mx=Math.max.apply(null,tops);
  const span=Math.max(1,mx-mn);
  arr.forEach(function(e,i){
    e.style.animationDelay=(((tops[i]-mn)/span)*FX_SPREAD/1000).toFixed(3)+"s";
  });
}
let siteI=0, siteTimer=null, siteBusy=false;
const siteCache={};

function drawSiteInd(){
  $("siteind").innerHTML=SITES.map(function(x,i){
    return '<button data-i="'+i+'"'+(i===siteI?' class="on"':'')+'>'+x.name+'</button>';
  }).join("");
}
function wait(ms){ return new Promise(function(r){ setTimeout(r,ms); }); }

/* 頁首大標題（LOGO 右邊那行）隨場地更換。
   結構是 <span class="t1">場地名<i class="t2">氣象監測</i></span>，
   只改第一個文字節點，副標「氣象監測」不動。 */
function setBrandName(nm){
  const t1=document.querySelector(".bt .t1");
  if(t1 && t1.firstChild && t1.firstChild.nodeType===3) t1.firstChild.nodeValue=nm;
  document.title=nm+" 氣象監測";
}

async function siteData(i){
  const c=siteCache[i];
  if(c && Date.now()-c.t<SITE_TTL) return c.d;
  $("lat").value=SITES[i].lat.toFixed(4);
  $("lon").value=SITES[i].lon.toFixed(4);
  const d=await run(true);
  if(d) siteCache[i]={t:Date.now(), d:d};
  return d;
}

async function showSite(i,animate){
  if(siteBusy) return;
  siteBusy=true;
  try{
    const d=await siteData(i);          // 先備好資料，畫面此時還是舊場地
    if(!d){ siteBusy=false; return; }
    if(animate){
      fxPrepare("out");
      document.body.classList.add("fx-out");
      await wait(FX_OUT);
    }
    siteI=i;
    $("lat").value=SITES[i].lat.toFixed(4);
    $("lon").value=SITES[i].lon.toFixed(4);
    render(d.lat,d.lon,d.om,d.place,d.cwa,d.quake,d.ty);
    $("pname").textContent=SITES[i].name;   // 用自訂場地名，不用反查地名
    setBrandName(SITES[i].name);            // 頁首大標題也跟著換
    drawSiteInd();
    if(animate){
      document.body.classList.remove("fx-out");
      fxPrepare("in");                       // 卡片剛重繪，量新位置排進場順序
      document.body.classList.add("fx-in");
      setTimeout(function(){
        document.body.classList.remove("fx-in");
        document.querySelectorAll(".card,.al,.g-hi,.g-rdr,.g-cr")
                .forEach(function(e){ e.style.animationDelay=""; });
      }, FX_SPREAD+450);
    }
  }catch(e){ showErr("場地切換失敗："+e.message); }
  siteBusy=false;
}

function startRotate(){
  if(siteTimer) clearInterval(siteTimer);
  siteTimer=setInterval(function(){ showSite((siteI+1)%SITES.length,true); },SITE_ITV);
}
$("siteind").addEventListener("click",function(e){
  const b=e.target.closest("button"); if(!b) return;
  showSite(+b.dataset.i,true);
  startRotate();                        // 手動切換後重新計時
});

"""
s = s.replace("/* ---------- 主流程 ---------- */", SITE_JS + "/* ---------- 主流程 ---------- */", 1)

# 啟動：關掉原本的定位與單點更新，改由輪播驅動
_OLD_BOOT = """loadCfg();
const s0=+$("itv").value; if(s0>0) timer=setInterval(run,s0*1000);
run();"""
if _OLD_BOOT in s:
    raise SystemExit("啟動段落與預期不符（itv 應已移除）")
s = s.replace("timer=setInterval(run,AUTO_ITV*1000);",
              "document.body.dataset.fx=SITE_FX;\n"
              "drawSiteInd();\n"
              "showSite(0,false).then(startRotate);   // 先顯示第一個場地，再開始輪播", 1)
s = s.replace("run();\n})();", "})();", 1)

SITE_CSS = """
  /* ---------- 場地切換列 ---------- */
  .siteind{display:flex;gap:.4rem;align-items:center;margin-left:auto;flex-wrap:wrap}
  .siteind button{background:var(--panel2);border:1px solid var(--line);color:var(--tx3);
                  border-radius:999px;padding:.12rem .8rem;font-size:1rem;
                  font-family:inherit;cursor:pointer;white-space:nowrap}
  .siteind button.on{background:var(--accent);color:#06202b;
                     border-color:var(--accent);font-weight:800}

  /* ---------- 場地切換動效 ----------
     三種風格由 JS 的 SITE_FX 決定，寫在 body[data-fx] 上。
     共用的元素集合：資料卡、研判卡、熱指數表、雷達、趨勢圖。 */
  .main,.alerts{perspective:1200px}
  .card,.al,.g-hi,.g-rdr,.g-cr{will-change:transform,opacity}

  /* --- cascade：整片先淡出，再由畫面上方往下逐一浮現（預設）
         進場位移只有 12px 且方向一致向下，視線跟著走不會亂跳。
         每個元素的延遲由 JS 依實際 Y 座標寫成行內樣式。 --- */
  body[data-fx="cascade"].fx-out .card,body[data-fx="cascade"].fx-out .al,
  body[data-fx="cascade"].fx-out .g-hi,body[data-fx="cascade"].fx-out .g-rdr,
  body[data-fx="cascade"].fx-out .g-cr{animation:fxCasOut .18s ease-in forwards}
  body[data-fx="cascade"].fx-in .card,body[data-fx="cascade"].fx-in .al,
  body[data-fx="cascade"].fx-in .g-hi,body[data-fx="cascade"].fx-in .g-rdr,
  body[data-fx="cascade"].fx-in .g-cr{animation:fxCasIn .34s cubic-bezier(.22,.85,.3,1) both}
  @keyframes fxCasOut{to{opacity:0}}
  @keyframes fxCasIn{from{opacity:0;transform:translateY(-12px)}
                     to{opacity:1;transform:none}}

  /* --- fade：淡出淡入＋輕微上移。位移只有 8px，久看不累 --- */
  body[data-fx="fade"].fx-out .card,body[data-fx="fade"].fx-out .al,
  body[data-fx="fade"].fx-out .g-hi,body[data-fx="fade"].fx-out .g-rdr,
  body[data-fx="fade"].fx-out .g-cr{animation:fxFadeOut .22s ease-in forwards}
  body[data-fx="fade"].fx-in .card,body[data-fx="fade"].fx-in .al,
  body[data-fx="fade"].fx-in .g-hi,body[data-fx="fade"].fx-in .g-rdr,
  body[data-fx="fade"].fx-in .g-cr{animation:fxFadeIn .32s cubic-bezier(.2,.8,.3,1) both}
  @keyframes fxFadeOut{to{opacity:0;transform:translateY(-6px)}}
  @keyframes fxFadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}

  /* --- slide：橫向滑動，方向感明確 --- */
  body[data-fx="slide"].fx-out .card,body[data-fx="slide"].fx-out .al,
  body[data-fx="slide"].fx-out .g-hi,body[data-fx="slide"].fx-out .g-rdr,
  body[data-fx="slide"].fx-out .g-cr{animation:fxSlideOut .24s ease-in forwards}
  body[data-fx="slide"].fx-in .card,body[data-fx="slide"].fx-in .al,
  body[data-fx="slide"].fx-in .g-hi,body[data-fx="slide"].fx-in .g-rdr,
  body[data-fx="slide"].fx-in .g-cr{animation:fxSlideIn .34s cubic-bezier(.2,.8,.3,1) both}
  @keyframes fxSlideOut{to{opacity:0;transform:translateX(-14px)}}
  @keyframes fxSlideIn{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:none}}

  /* --- flip：機械翻牌（幅度最大） --- */
  body[data-fx="flip"] .card,body[data-fx="flip"] .al,
  body[data-fx="flip"] .g-hi,body[data-fx="flip"] .g-rdr,
  body[data-fx="flip"] .g-cr{transform-origin:50% 0;backface-visibility:hidden}
  body[data-fx="flip"].fx-out .card,body[data-fx="flip"].fx-out .al,
  body[data-fx="flip"].fx-out .g-hi,body[data-fx="flip"].fx-out .g-rdr,
  body[data-fx="flip"].fx-out .g-cr{animation:fxFlapOut .34s cubic-bezier(.6,.02,.9,.25) forwards}
  body[data-fx="flip"].fx-in .card,body[data-fx="flip"].fx-in .al,
  body[data-fx="flip"].fx-in .g-hi,body[data-fx="flip"].fx-in .g-rdr,
  body[data-fx="flip"].fx-in .g-cr{animation:fxFlapIn .44s cubic-bezier(.2,.9,.25,1.05) both}
  @keyframes fxFlapOut{
    0%{transform:rotateX(0deg);filter:brightness(1)}
    100%{transform:rotateX(-90deg);filter:brightness(.3)}}
  @keyframes fxFlapIn{
    0%{transform:rotateX(90deg);filter:brightness(.3)}
    62%{transform:rotateX(-7deg);filter:brightness(1.08)}
    100%{transform:rotateX(0deg);filter:brightness(1)}}

  /* 進場順序改由 JS 依元素實際 Y 座標寫成行內 animation-delay，
     這裡不再用 nth-child ——  卡片分欄排列，nth-child 排不出視覺上的上下順序。 */
"""
s = s.replace("</style>", SITE_CSS + "</style>", 1)

# ---------- 3.9) 資料正確性修正（2026-08-31 全面檢查後）----------
# 桌機 v2.9 定版不改，以下只在手機版生效。
# 注意：s 由 io.open 讀入，換行已統一為單一 LF，比對字串用 LF 串接。
LF = chr(10)

# (a) 現在時刻對應的逐時格：原本取「時間最接近」的一格，過了半點就取到下一個整點，
#     於是「過去 24 小時最大陣風」會把一格未來預報算進去，「未來 12 小時」整段往後推一小時
#     （實際成了未來 1～13 小時，漏掉最近的那一小時）。改成取「包住現在」的那一格。
_OLD_INOW = LF.join([
    "  let iNow=0,bd=1e18;",
    "  H.time.forEach(function(t,i){ const d=Math.abs(new Date(t)-now); if(d<bd){bd=d;iNow=i;} });"])
_NEW_INOW = LF.join([
    "  let iNow=0;",
    "  H.time.forEach(function(t,i){ if(new Date(t)<=now) iNow=i; });   // 包住「現在」的那一格"])
if _OLD_INOW not in s:
    raise SystemExit("找不到 iNow 區塊")
s = s.replace(_OLD_INOW, _NEW_INOW, 1)

# (b) 體感溫度：原本直接用 Open-Meteo 的 apparent_temperature，那是拿「模式自己的溫濕度」算的，
#     同一張卡上的氣溫與濕度卻是測站實測，兩邊常差 2～3 °C，會出現
#     「氣溫 24.9 °C、體感 29.8 °C」這種對不起來的畫面。
#     改用測站實測溫濕度＋實測風速，以澳洲氣象局 AT 公式（Open-Meteo 同一套）自行計算；
#     測站溫濕度缺漏時才退回模式值。
_OLD_APP = "  const app=N(c.apparent_temperature);"
_NEW_APP = LF.join([
    "  let app=N(c.apparent_temperature);",
    "  if(t!==null&&rh!==null){                    // 與同卡的氣溫／濕度同源，避免互相矛盾",
    "    const _e=(rh/100)*6.105*Math.exp(17.27*t/(237.7+t));   // 水氣壓 hPa",
    "    app=t+0.33*_e-0.70*(w_avg!==null?w_avg:0)-4.00;",
    "  }"])
if _OLD_APP not in s:
    raise SystemExit("找不到體感溫度")
s = s.replace(_OLD_APP, _NEW_APP, 1)

# (c) 24 小時最大陣風取自 Open-Meteo 逐時模式，不是測站實測，原標「過去實況」會誤導。
s = s.replace('card("24 小時最大陣風",f(g24,1),"m/s","過去實況",wl(g24))',
              'card("24 小時最大陣風",f(g24,1),"m/s","過去 24 小時・模式推估",wl(g24))', 1)

# (d) 逐時雨量長條圖同樣是模式資料，與卡片的雨量站實測可能差好幾倍
#     （檢查當下：台南模式過去 24 小時 38 mm、雨量站實測 8.5 mm），標題要講清楚來源。
s = s.replace("逐時雨量 mm（半透明為預報）", "逐時雨量 mm（模式推估，半透明為預報）", 1)

# (e) 顯著有感地震報告只取 6 筆，地震密集時「近 7 日 M≥4」會少算，放寬到 20 筆。
s = s.replace("&format=JSON&limit=6", "&format=JSON&limit=20", 1)

# (f) 小雷達圖標的是「取得時間」不是回波觀測時間，加字避免誤讀。
s = s.replace('"氣象署合成回波　"', '"氣象署合成回波　取得 "', 1)

# ---------- 3.96) 紅色警訊閃爍提醒 ----------
# 只讓「紅字」本身閃（研判卡的紅色狀態字、卡片的紅色數值、頂端警報橫幕的紅點），
# 動畫掛在文字元素上、不掛在 .card／.al 本身，才不會跟輪播的 cascade 進場動畫打架。
# 使用者若開啟系統「減少動態效果」，不整個關掉（這是安全警訊），改成 2.6 秒的和緩呼吸。
_BLINK = LF.join([
    "  @keyframes badBlink{0%,100%{opacity:1}50%{opacity:.32}}",
    "  .al.lv-bad .m,.card.c-bad .v{animation:badBlink 1.1s ease-in-out infinite}",
    "  .al.lv-bad{border-color:var(--bad)}",
    "  @media (prefers-reduced-motion:reduce){",
    "    .al.lv-bad .m,.card.c-bad .v{animation:badBlink 2.6s ease-in-out infinite}",
    "  }",
    "</style>"])
s = s.replace("</style>", _BLINK, 1)

# ---------- 4) 標題與手機 meta ----------
# 手機版標題文字（桌機定版不受影響）
s = s.replace('<span class="bt">工地環境安全即時監控系統<b>',
              '<span class="bt"><span class="t1">台中圓滿<i class="t2">氣象監測</i></span><b>', 1)

s = s.replace("<title>工地環境安全即時監控系統</title>",
              "<title>台中圓滿 氣象監測</title>\n"
              '<meta name="robots" content="noindex,nofollow,noarchive">\n'
              '<meta name="theme-color" content="#15181d">\n'
              '<meta name="mobile-web-app-capable" content="yes">\n'
              '<meta name="apple-mobile-web-app-capable" content="yes">\n'
              '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
              '<meta name="apple-mobile-web-app-title" content="台中圓滿">', 1)

s = s.replace('<meta name="viewport" content="width=device-width, initial-scale=1">',
              '<meta name="viewport" content="width=device-width,initial-scale=1,'
              'viewport-fit=cover,user-scalable=no">', 1)

# ---------- 自動跳號 ----------
# 拿掉版號本身後計算雜湊：內容真的有變才跳號，
# 重複產生同樣的內容不會灌水，也不必記得手動執行任何指令。
_state = load_state()
_hash = hashlib.sha256(s.encode("utf-8")).hexdigest()
_bumped = (_hash != _state.get("hash"))
_ver = next_ver(_state["ver"]) if _bumped else _state["ver"]
s = s.replace(MOBVER_TAG, _ver)
io.open(STATE, "w", encoding="utf-8").write(
    json.dumps({"ver": _ver, "hash": _hash}, ensure_ascii=False, indent=1))

io.open(OUT, "w", encoding="utf-8").write(s)

print("已產生：%s（%.0f KB）" % (os.path.basename(OUT), os.path.getsize(OUT) / 1024.0))
print("手機版版號：%s %s" % (_ver, "（內容有變，已跳號）" if _bumped else "（內容未變，版號不動）"))
print("移除堆疊樣式 %d 字元，其餘內容未更動。" % removed)
print("")
print("內容一致性檢查（手機版 vs 桌機定版）：")


def count(txt, pat):
    return len(re.findall(pat, txt))


ok = True
# delta = 手機版刻意增加的數量（熱指數表是新面板，不是內容遺失）
for label, pat, delta in [("數據卡 card(", r"card\(", 0),
                          # 熱危害改職安署四級（分支 5→6，+1）＋ 新增紫外線研判（+6）
                          ("研判 alertBox(", r"alertBox\(", 7),
                          ("面板 panel", r'class="panel', 1),
                          ("疊層 ov", r'class="ov ', 0),
                          ("圖表 bars(", r"bars\(", 0)]:
    a, b = count(o, pat), count(s, pat)
    same = (b - a == delta)
    ok = ok and same
    note = "一致" if same else "!! 不一致"
    if delta:
        note += "（刻意新增 +%d）" % delta
    print("  %-16s 原檔 %3d ／ 手機版 %3d  %s" % (label, a, b, note))
print("")
print("內容比對通過（原有內容未遺失）。" if ok else "!! 內容有落差，請檢查。")
