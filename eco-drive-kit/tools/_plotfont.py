"""Register a Korean-capable font for matplotlib (portable: found via fc-match)."""
import subprocess
import matplotlib
from matplotlib import font_manager as fm

def setup():
    for fam in ("NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"):
        try:
            path = subprocess.run(["fc-match", "-f", "%{file}", f"{fam}:lang=ko"], capture_output=True, text=True).stdout.strip()
        except FileNotFoundError:
            path = ""
        if path:
            fm.fontManager.addfont(path)
            name = fm.FontProperties(fname=path).get_name()
            matplotlib.rcParams["font.family"] = ["DejaVu Sans", name]   # DejaVu first: \mathdefault minus glyph; Hangul falls back
            break
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["mathtext.fontset"] = "dejavusans"   # log-axis minus signs

setup()
