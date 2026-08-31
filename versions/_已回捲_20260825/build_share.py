# -*- coding: utf-8 -*-
"""工地氣象監控 — 產生可散布的檔案

用法：
    python build_share.py

會依 index.html 目前版號產生兩種版本：

  分享用/          內含金鑰，對方打開就能看到測站實測值，不需任何設定
    工地氣象監控_vX.Y.html                    ← 雲端硬碟、Email、隨身碟
    工地氣象監控_vX.Y_LINE用_改副檔名為html.txt ← LINE 傳送（.txt 不會被打包成壓縮檔）

  公開上線用/      金鑰已清空，適合放 GitHub Pages 等公開網址
    index.html

⚠ 分享用的檔案含有你的授權碼，拿到檔案的人都能從原始碼取出。
  不要放到公開網站或公開群組；公開場合請用「公開上線用」那份。
"""
import io, os, re, sys, shutil

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "index.html")
SHARE = os.path.join(HERE, "分享用")
PUBLIC = os.path.join(HERE, "公開上線用")

KEY_PAT = re.compile(r'(const EMBEDDED_KEY=")([^"]*)(";)')
VER_PAT = re.compile(r'const VER="(\d+\.\d+)";')


def fresh(d):
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)


def main():
    s = io.open(SRC, encoding="utf-8").read()

    mv = VER_PAT.search(s)
    mk = KEY_PAT.search(s)
    if not mv or not mk:
        print("找不到 const VER 或 const EMBEDDED_KEY，請確認 index.html 未被改動格式")
        return 1
    ver, key = mv.group(1), mk.group(2)

    fresh(SHARE)
    fresh(PUBLIC)

    # --- 分享用（含金鑰，原樣輸出）---
    name = "工地氣象監控_v%s" % ver
    share_html = os.path.join(SHARE, name + ".html")
    share_txt = os.path.join(SHARE, name + "_LINE用_改副檔名為html.txt")
    io.open(share_html, "w", encoding="utf-8").write(s)
    io.open(share_txt, "w", encoding="utf-8").write(s)

    # --- 公開上線用（清空金鑰）---
    pub = KEY_PAT.sub(lambda m: m.group(1) + m.group(3), s, count=1)
    io.open(os.path.join(PUBLIC, "index.html"), "w", encoding="utf-8").write(pub)

    # --- 驗證 ---
    def has_key(path):
        return key != "" and key in io.open(path, encoding="utf-8").read()

    ok = True
    print("版本 v%s" % ver)
    print("")
    print("分享用/（含金鑰，開啟即用）")
    for f in (share_html, share_txt):
        good = has_key(f) if key else True
        ok = ok and good
        print("  %-46s %6.0f KB  金鑰:%s" % (
            os.path.basename(f), os.path.getsize(f) / 1024.0,
            "有 ✓" if has_key(f) else ("無 ✗ 應該要有" if key else "（未設定）")))
    print("")
    print("公開上線用/（無金鑰，可公開）")
    pf = os.path.join(PUBLIC, "index.html")
    leaked = has_key(pf)
    ok = ok and not leaked
    print("  %-46s %6.0f KB  金鑰:%s" % (
        "index.html", os.path.getsize(pf) / 1024.0,
        "!! 有殘留，請勿上線" if leaked else "無 ✓ 可安全公開"))
    print("")
    if not key:
        print("提醒：index.html 的 EMBEDDED_KEY 是空的，分享版不會內建金鑰。")
    print("完成。" if ok else "!! 驗證未通過，請檢查。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
