# -*- coding: utf-8 -*-
"""工地氣象監控 — 產生上線用與傳送用檔案

用法：
    python build_web.py

不會修改 index.html（設計原檔保持不動），只從它產生：

  上線用/          放到 GitHub Pages 等靜態託管
    index.html     ← 注入 noindex 標籤，其餘與原檔相同
    robots.txt     ← 婉拒搜尋引擎收錄

  送出用/          直接把檔案傳給人（LINE、雲端硬碟）
    工地氣象監控_vX.Y.html
    工地氣象監控_vX.Y_LINE用_改副檔名為html.txt

⚠ 兩者都內含 CWA 授權碼。noindex 只能降低被搜尋引擎收錄的機會，
  擋不住連結被轉傳後有人查看原始碼。金鑰要作廢就到
  https://opendata.cwa.gov.tw/user/authkey 重新產生。
"""
import io, os, re, sys, shutil

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "index.html")
WEB = os.path.join(HERE, "上線用")
SEND = os.path.join(HERE, "送出用")

VER_PAT = re.compile(r'const VER="(\d+\.\d+)";')
KEY_PAT = re.compile(r'const EMBEDDED_KEY="([^"]*)";')
TITLE = "<title>工地環境安全即時監控系統</title>"
NOINDEX = '\n<meta name="robots" content="noindex,nofollow,noarchive">'

ROBOTS = "User-agent: *\nDisallow: /\n"


def fresh(d):
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)


def main():
    s = io.open(SRC, encoding="utf-8").read()
    mv, mk = VER_PAT.search(s), KEY_PAT.search(s)
    if not mv or not mk:
        print("找不到 const VER 或 const EMBEDDED_KEY，請確認 index.html 未被改動格式")
        return 1
    ver, key = mv.group(1), mk.group(1)
    if TITLE not in s:
        print("找不到 <title>，無法注入 noindex")
        return 1

    fresh(WEB)
    fresh(SEND)

    # --- 上線用 ---
    web = s.replace(TITLE, TITLE + NOINDEX, 1)
    # 上線版金鑰已內建，不會有 cwa_key.js，移掉它以免 console 出現 404
    # 注意：檔案為 CRLF 換行，行尾要寫成 \r?\n
    web = re.sub(r'[ \t]*<!--[^>]*個人金鑰[^>]*-->\r?\n', "", web)
    web = re.sub(r'[ \t]*<script src="cwa_key\.js"[^>]*></script>\r?\n', "", web)
    # 只檢查 script 標籤；JS 註解裡提到 cwa_key.js 是正常的
    if 'src="cwa_key.js"' in web:
        print("!! 上線版仍引用 cwa_key.js，移除規則未生效")
        return 1
    io.open(os.path.join(WEB, "index.html"), "w", encoding="utf-8").write(web)
    io.open(os.path.join(WEB, "robots.txt"), "w", encoding="utf-8").write(ROBOTS)

    # --- 上線用：手機版（獨立路徑 m.html，不覆蓋桌機版 index.html） ---
    mob_src = os.path.join(HERE, "工地氣象監控_手機版.html")
    if os.path.exists(mob_src):
        mob = io.open(mob_src, encoding="utf-8").read()
        mob = re.sub(r'[ \t]*<!--[^>]*個人金鑰[^>]*-->\r?\n', "", mob)
        mob = re.sub(r'[ \t]*<script src="cwa_key\.js"[^>]*></script>\r?\n', "", mob)
        if 'src="cwa_key.js"' in mob:
            print("!! 手機版仍引用 cwa_key.js，移除規則未生效")
            return 1
        io.open(os.path.join(WEB, "m.html"), "w", encoding="utf-8").write(mob)

    # --- 送出用 ---
    base = "工地氣象監控_v%s" % ver
    io.open(os.path.join(SEND, base + ".html"), "w", encoding="utf-8").write(s)
    io.open(os.path.join(SEND, base + "_LINE用_改副檔名為html.txt"), "w", encoding="utf-8").write(s)

    # --- 驗證 ---
    def check(path):
        t = io.open(path, encoding="utf-8").read()
        return (key != "" and key in t), ("noindex" in t)

    print("版本 v%s　金鑰：%s" % (ver, "已內建" if key else "未設定（將為 Open-Meteo 模式）"))
    print("")
    ok = True
    wp = os.path.join(WEB, "index.html")
    hk, ni = check(wp)
    ok = ok and hk and ni
    print("上線用/")
    print("  index.html   %5.0f KB   金鑰:%s   noindex:%s" % (
        os.path.getsize(wp) / 1024.0, "有" if hk else "無", "有" if ni else "無"))
    print("  robots.txt         已寫入 Disallow: /")
    print("")
    print("送出用/")
    for n in sorted(os.listdir(SEND)):
        pth = os.path.join(SEND, n)
        hk2, _ = check(pth)
        ok = ok and hk2
        print("  %-44s %5.0f KB   金鑰:%s" % (n, os.path.getsize(pth) / 1024.0, "有" if hk2 else "無"))
    print("")
    print("完成。" if ok else "!! 驗證未通過，請檢查。")
    print("提醒：上線後這把金鑰等同公開，連結請只在需要的群組流通。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
