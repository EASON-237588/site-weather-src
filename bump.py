# -*- coding: utf-8 -*-
"""工地氣象監控 — 版本自動跳號

用法：
    python bump.py          小版號 +1（1.0 -> 1.1 -> ... -> 1.9 -> 2.0）
    python bump.py major    大版號 +1，小版號歸零（1.3 -> 2.0）
    python bump.py 3.5      直接指定版本

會同時：
  1. 改寫 index.html 裡的 const VER="x.y"
  2. 把舊版備份到 versions/index_vX.Y.html
"""
import io, os, re, sys, shutil

try:                                    # Windows 主控台預設 cp950，中文訊息會亂碼
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "index.html")
VERDIR = os.path.join(HERE, "versions")
PAT = re.compile(r'(const VER=")(\d+)\.(\d+)(";)')


def main():
    s = io.open(SRC, encoding="utf-8").read()
    m = PAT.search(s)
    if not m:
        print("找不到版本字串 const VER=\"x.y\"，請確認 index.html 未被改動格式")
        return 1
    cur_major, cur_minor = int(m.group(2)), int(m.group(3))
    cur = "%d.%d" % (cur_major, cur_minor)

    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if re.match(r"^\d+\.\d+$", arg):
        new_major, new_minor = [int(x) for x in arg.split(".")]
    elif arg == "major":
        new_major, new_minor = cur_major + 1, 0
    else:
        new_major, new_minor = cur_major, cur_minor + 1
        if new_minor > 9:
            new_major, new_minor = new_major + 1, 0
    new = "%d.%d" % (new_major, new_minor)

    # 備份舊版
    if not os.path.isdir(VERDIR):
        os.makedirs(VERDIR)
    bak = os.path.join(VERDIR, "index_v%s.html" % cur)
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)

    s = PAT.sub(lambda x: x.group(1) + new + x.group(4), s, count=1)
    io.open(SRC, "w", encoding="utf-8").write(s)
    print("版本編號 %s -> %s（舊版備份：versions/index_v%s.html）" % (cur, new, cur))
    return 0


if __name__ == "__main__":
    sys.exit(main())
