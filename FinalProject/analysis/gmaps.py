"""Doc bieu do "Gio dong khach" (Google Maps popular times) tu anh chup man hinh.

Moi anh la bieu do cua mot tram trong mot ngay, gom 24 cot tu 04:00 den 03:00
hom sau (cot i <-> gio (4 + i) mod 24; da doi chieu bang cot "Truc tiep" luc
00:30). Chieu cao cot ty le voi do dong tuong doi so voi gio dong nhat trong
tuan cua chinh tram do, nen 7 ngay cua mot tram dung chung mot thang do.

Cot "Truc tiep" (mau do) gom phan dam la muc luc chup va phan nhat la muc
thuong le; ham lay dinh cua toan bo phan mau, tuc muc thuong le khi muc luc
chup thap hon (truong hop cua ca 14 anh).

Chay tu thu muc goc repo:
    .venv/bin/python -m FinalProject.analysis.gmaps
"""
import colorsys
import csv
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "data", "gmaps")
CSV_PATH = os.path.join(HERE, "data", "gmaps_popular_times.csv")

STATIONS = {"tram1": "Trạm Xăng Dầu Mỹ Đình", "tram2": "Trạm Xăng Dầu ATS Mipecorp"}
DAYS = ["thu2", "thu3", "thu4", "thu5", "thu6", "thu7", "chunhat"]
DAY_NAME = {"thu2": "Thứ Hai", "thu3": "Thứ Ba", "thu4": "Thứ Tư", "thu5": "Thứ Năm",
            "thu6": "Thứ Sáu", "thu7": "Thứ Bảy", "chunhat": "Chủ nhật"}
FIRST_HOUR = 4          # cot dau tien la 04:00
N_BARS = 24


def _colored(p):
    r, g, b = (c / 255 for c in p)
    _, light, sat = colorsys.rgb_to_hls(r, g, b)
    return sat > 0.3 and light < 0.92


def read_bars(path):
    """Tra ve (chieu cao 24 cot tinh bang pixel, chieu cao vung ve)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    counts = [sum(_colored(px[x, y]) for x in range(w)) for y in range(h)]
    base = max(y for y in range(h) if counts[y] > 150) + 1      # ngay duoi day cot
    dash = min(y for y in range(h // 4, base)                    # duong ke dut phia tren
               if sum(1 for x in range(w) if px[x, y][0] < 215
                      and abs(px[x, y][0] - px[x, y][2]) < 8) > 100)
    row = base - 2
    segs, start = [], None
    for x in range(w + 1):
        on = x < w and _colored(px[x, row])
        if on and start is None:
            start = x
        elif not on and start is not None:
            if x - start >= 10:
                segs.append((start, x - 1))
            start = None
    # Cot "Truc tiep" co vien nhat nen co the bi sot o hang nay; dung luoi deu
    # neo vao cot dau, buoc lay tu cac cot lien ke tim duoc.
    steps = [b[0] - a[0] for a, b in zip(segs, segs[1:])]
    pitch = float(np.median([s for s in steps if s < 20]))
    x0, width = segs[0][0], segs[0][1] - segs[0][0]
    centers = [int(round(x0 + width / 2 + pitch * i)) for i in range(N_BARS)]
    if centers[-1] > w - 5 or abs(centers[-1] - (segs[-1][0] + width / 2)) > 3:
        raise ValueError(f"{os.path.basename(path)}: luoi cot khong khop ({len(segs)} cot tim thay)")
    heights = []
    for cx in centers:
        top = min(y for y in range(dash + 1, base) if _colored(px[cx, y]))
        heights.append(base - top)
    return heights, base - dash


def extract(write=True):
    """Doc 14 anh, ghi CSV dai (tram, ngay, gio, pixel). Tra ve dict tram -> mang 7x24."""
    out, rows = {}, []
    for st in STATIONS:
        mat = []
        for d in DAYS:
            hs, full = read_bars(os.path.join(IMG_DIR, f"{st}-{d}.png"))
            mat.append(hs)
            for i, v in enumerate(hs):
                rows.append([st, d, (FIRST_HOUR + i) % 24, v, full])
        out[st] = np.array(mat, float)
    if write:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["station", "day", "hour", "bar_px", "chart_px"])
            wr.writerows(rows)
    return out


def hourly_share(mat, open_hour=6, hours=16):
    """Ty trong luot den theo gio trong cua so phan tich (trung binh 7 ngay)."""
    i0 = open_hour - FIRST_HOUR
    m = mat[:, i0:i0 + hours].mean(axis=0)
    return m / m.sum()


def window_coverage(mat, open_hour=6, hours=16):
    """Phan do dong ca ngay (24 gio) roi vao cua so phan tich."""
    i0 = open_hour - FIRST_HOUR
    return float(mat[:, i0:i0 + hours].sum() / mat.sum())


if __name__ == "__main__":
    data = extract()
    for st, mat in data.items():
        print(STATIONS[st])
        for d, row in zip(DAYS, mat):
            print(f"  {d:<8}", " ".join(f"{int(v):>2}" for v in row))
        print("  ty trong 06-22:", np.round(hourly_share(mat), 3))
        print(f"  06-22 chiem {window_coverage(mat):.1%} do dong ca ngay")
