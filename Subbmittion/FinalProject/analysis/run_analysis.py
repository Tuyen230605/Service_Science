"""Chuong trinh phan tich chinh cho du an INT3501 - Nhom 8.
De tai: hang doi va phan bo nhan vien tai mot cua hang xang dau noi thanh Ha Noi.

Chay:  python3 run_analysis.py
Dau ra: data/*.csv, tables/*.tex, ../figures/*.png

DU LIEU: luot den theo gio la DU LIEU MO PHONG, nhung QUY MO nhu cau duoc hieu
chinh tu so lieu cong bo (Ha Noi tieu thu ~110.000 m3 xang/thang, 453 cua hang
ban le - So Cong Thuong Ha Noi; dung tich binh xang xe may 4,4-4,9 L; luong
nhan vien ban xang 8-12 trieu dong/thang theo tin tuyen dung). Cac tham so con
lai (phan bo theo gio, thoi gian phuc vu) la GIA DINH co can cu, ghi trong
CONFIG va trong bang tab_assumptions.tex de thay bang so do thuc khi co.
"""

from __future__ import annotations

import csv
import os
import re
from math import isfinite

import numpy as np

import queueing as q
from simulate import SimConfig, run, summarize

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TABLES = os.path.join(HERE, "tables")
FIGS = os.path.abspath(os.path.join(HERE, "..", "figures"))
for d in (DATA, TABLES, FIGS):
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------- CONFIG ----
OPEN_HOUR = 6                       # cua so phan tich 06:00-22:00
HOURS = 16
DAYS = 20                           # 20 ngay mo phong

# --- Hieu chinh quy mo tu so lieu cong bo (R = real/cong bo, E = uoc tinh) ---
HN_PETROL_M3_MONTH = 110_000        # R: m3 xang/thang toan Ha Noi (So Cong Thuong)
HN_STORES = 453                     # R: so cua hang ban le xang dau dang hoat dong
DAYS_PER_MONTH = 30
LITRES_PER_STORE_DAY = HN_PETROL_M3_MONTH * 1000 / HN_STORES / DAYS_PER_MONTH  # ~8.094 L
MOTO_VOLUME_SHARE = 0.75            # E: 5,6 trieu xe may xang (VnExpress 16/7/2025) x ~0,5 L/ngay ~ 84.000 m3/thang
LITRES_PER_VISIT = {1: 30.0, 2: 2.5}  # E: o to (binh 40-50 L); xe may (binh 4,4-4,9 L)

VISITS_CAR = LITRES_PER_STORE_DAY * (1 - MOTO_VOLUME_SHARE) / LITRES_PER_VISIT[1]
VISITS_MOTO = LITRES_PER_STORE_DAY * MOTO_VOLUME_SHARE / LITRES_PER_VISIT[2]
VISITS_DAY = VISITS_CAR + VISITS_MOTO

# Gia dinh G1: ty trong luot den theo gio 06-22 (hai dinh di lam / tan tam)
HOURLY_SHARE = [0.045, 0.075, 0.085, 0.065, 0.055, 0.055, 0.060, 0.050,
                0.050, 0.055, 0.065, 0.085, 0.090, 0.070, 0.050, 0.045]
HOURLY_LAMBDA = [int(round(VISITS_DAY * w)) for w in HOURLY_SHARE]  # xe/gio

# Gia dinh G2: co cau loai xe (theo so luot) suy tu hieu chinh tren
CLASS_MIX = {1: VISITS_CAR / VISITS_DAY, 2: VISITS_MOTO / VISITS_DAY}
CLASS_NAME = {1: "Ô tô", 2: "Xe máy"}

# Gia dinh G3: thoi gian phuc vu tai vi tri bom (phut/xe): mo nap, bom, thanh toan,
# xuat hoa don dien tu tung lan ban (ND 70/2025). Tai lieu: 1-4 phut/xe may.
SERVICE_ASIS = {1: 4.0, 2: 1.5}
DIGITAL_GAIN = 0.20                 # TO-BE: tra truoc QR/ung dung giam 20% thoi gian
SERVICE_TOBE = {k: v * (1 - DIGITAL_GAIN) for k, v in SERVICE_ASIS.items()}
CV_SERVICE = 0.8


def mix_mean(svc):
    return sum(CLASS_MIX[k] * svc[k] for k in svc)


MEAN_SERVICE_ASIS = mix_mean(SERVICE_ASIS)   # ~1,57 phut
MEAN_SERVICE_TOBE = mix_mean(SERVICE_TOBE)   # ~1,25 phut

# Gia dinh G4: lich hien tai, gioi han vat ly va chi phi
SERVERS_ASIS = [6] * HOURS          # 6 nhan vien bom moi gio
C_MAX = 8                           # 8 voi bom -> toi da 8 kenh
WAGE_MONTH = 10_000_000             # R: 8-12 trieu dong/thang (tin tuyen dung)
COST_PER_SERVER_HOUR = 58_000       # dong/gio = 10 trieu x 1,215 (BHXH) / 208 gio
TECH_COST_DAY = 250_000             # E: dong/ngay cho ung dung tra truoc + QR (TO-BE)
MARGIN_PER_LITRE = 1_500            # G: dong/L lai gop ban le; SGGP 29/7/2026: chiet khau co luc 0-150 d/L, can ~700 d/L de bu chi phi

# Gia dinh G5: khach bo di (balking) khi thay qua nhieu xe dang cho
BALK_QUEUE = 20                     # xe dang cho (~2,5-3 xe moi voi o gio cao diem)

# Muc dich vu nhom dat ra
TARGET_WQ_MEAN = 2.0                # phut
TARGET_T = 5.0                      # nguong "cho qua lau" (phut)
TARGET_TAIL = 0.05                  # P(Wq > 5 phut) <= 5%

PEAK = (11, 13)                     # chi so khung 17:00-19:00 (cao diem tan tam)
SEED = 20260117
LABEL = "Du lieu mo phong, quy mo hieu chinh tu so lieu cong bo"

# Mau ve (palette da kiem dinh, che do sang)
C_BLUE, C_ORANGE, C_AQUA = "#2a78d6", "#eb6834", "#1baf7a"
C_GRID, C_AXIS, C_INK, C_MUTED = "#e1e0d9", "#c3c2b7", "#2b2b28", "#6b6b63"


def hour_label(h: int) -> str:
    return f"{OPEN_HOUR + h:02d}-{OPEN_HOUR + h + 1:02d}"


def sim_config(servers, service, lam=None, days=DAYS, seed=SEED, cv=CV_SERVICE,
               balk=BALK_QUEUE):
    return SimConfig(hourly_lambda=lam or HOURLY_LAMBDA, class_mix=CLASS_MIX,
                     mean_service_min=mix_mean(service), cv_service=cv,
                     servers_by_hour=servers, priority_rule=False, days=days,
                     seed=seed, service_by_class=service, balk_queue=balk)


# ------------------------------------------------- 1. SINH DU LIEU & ETL ----
def generate_dataset():
    reqs, util = run(sim_config(SERVERS_ASIS, SERVICE_ASIS))
    path = os.path.join(DATA, "requests_asis_simulated.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data_label", "day", "vehicle_id", "vehicle_class", "hour_slot",
                    "t_arrival_min", "t_service_start_min", "t_service_end_min",
                    "service_min", "wait_min", "balked"])
        for r in reqs:
            w.writerow(["SIMULATED", r.day, r.rid, CLASS_NAME[r.priority],
                        hour_label(min(int(r.t_arrival // 60), HOURS - 1)),
                        round(r.t_arrival, 3), round(r.t_start, 3),
                        round(r.t_end, 3), round(r.service, 3), round(r.wq, 3), int(r.balked)])
    return reqs, util, path


def estimate_parameters(reqs):
    rows = []
    for h in range(HOURS):
        n = sum(1 for r in reqs if int(r.t_arrival // 60) == h)
        per_day = np.array([sum(1 for r in reqs if r.day == d and int(r.t_arrival // 60) == h)
                            for d in range(1, DAYS + 1)], dtype=float)
        rows.append({"hour": hour_label(h), "n_total": n, "lambda_hat": n / DAYS,
                     "lambda_assumed": HOURLY_LAMBDA[h],
                     "var_mean_ratio": float(per_day.var(ddof=1) / per_day.mean())})
    svc = np.array([r.service for r in reqs if not r.balked])
    stats = {"n": len(svc), "mean": float(svc.mean()), "sd": float(svc.std(ddof=1)),
             "cv": float(svc.std(ddof=1) / svc.mean()),
             "mu_per_hour": 60.0 / float(svc.mean())}
    return rows, stats


# -------------------------------------- 2. KIEM DINH CONG THUC M/M/s --------
def validate_formulas():
    """Erlang C so voi DES khi thoi gian phuc vu phan phoi mu (CV = 1), mot lop xe."""
    rows = []
    mu = 60.0 / MEAN_SERVICE_ASIS
    for lam, c in [(112, 4), (187, 6), (225, 6), (225, 7), (212, 5)]:
        if q.utilization(lam, mu, c) >= 1:
            rows.append({"lambda": lam, "c": c, "rho": q.utilization(lam, mu, c),
                         "Wq_analytic": float("inf"), "Wq_sim": float("nan"),
                         "gap_pct": float("nan")})
            continue
        ana = q.metrics(lam, mu, c, TARGET_T)
        cfg = SimConfig(hourly_lambda=[lam] * HOURS, class_mix={2: 1.0},
                        mean_service_min=MEAN_SERVICE_ASIS, cv_service=1.0,
                        servers_by_hour=[c] * HOURS, days=40, seed=SEED + c + lam)
        reqs, _ = run(cfg)
        reqs = [r for r in reqs if r.t_arrival >= 60]   # bo gio dau (lam nong)
        s = summarize(reqs, TARGET_T)
        rows.append({"lambda": lam, "c": c, "rho": ana["rho"], "Wq_analytic": ana["Wq"],
                     "Wq_sim": s["Wq_mean"],
                     "gap_pct": 100 * (s["Wq_mean"] - ana["Wq"]) / ana["Wq"]})
    return rows


# ------------------------------------------- 3. DANH GIA THEO GIO -----------
def feasible(m) -> bool:
    return (m["stable"] and m["Wq"] <= TARGET_WQ_MEAN + 1e-9
            and m["P_gt_target"] <= TARGET_TAIL + 1e-12)


def per_hour_table(servers, mean_service, lam=None):
    lam = lam or HOURLY_LAMBDA
    mu = 60.0 / mean_service
    rows = []
    for h in range(HOURS):
        m = q.metrics(lam[h], mu, servers[h], TARGET_T)
        rows.append({"hour": hour_label(h), "lambda": lam[h], "c": servers[h],
                     "rho": m["rho"], "Lq": m["Lq"], "Wq": m["Wq"], "Wq_p90": m["Wq_p90"],
                     "P_gt": m["P_gt_target"], "feasible": feasible(m)})
    return rows


# ----------------------------------------------- 4. BAI TOAN TOI UU HOA -----
def optimize_staffing(mean_service, lam=None, cmax=C_MAX):
    """min sum_t c_t  s.t. rho_t < 1, Wq_t <= 2 phut, P(Wq_t > 5) <= 5%, c_t <= 8.
    Tach duoc theo gio -> chon c nho nhat kha thi cho tung gio."""
    lam = lam or HOURLY_LAMBDA
    mu = 60.0 / mean_service
    rows = []
    for h in range(HOURS):
        chosen = None
        for c in range(1, cmax + 1):
            m = q.metrics(lam[h], mu, c, TARGET_T)
            if feasible(m):
                chosen = c
                break
        ok = chosen is not None
        chosen = chosen or cmax
        m = q.metrics(lam[h], mu, chosen, TARGET_T)
        rows.append({"hour": hour_label(h), "lambda": lam[h], "c_star": chosen,
                     "rho": m["rho"], "Wq": m["Wq"], "Wq_p90": m["Wq_p90"],
                     "P_gt": m["P_gt_target"], "feasible": ok})
    return rows


def staffing_cost(servers):
    hours = sum(servers)
    return hours, hours * COST_PER_SERVER_HOUR


# --------------------------------------------- 5. SO SANH BA PHUONG AN ------
def scenario(name, servers, service, days=DAYS, seed=SEED, lambda_scale=1.0):
    lam = [l * lambda_scale for l in HOURLY_LAMBDA]
    reqs, util = run(sim_config(servers, service, lam=lam, days=days, seed=seed))
    s = summarize(reqs, TARGET_T)
    pk = summarize([r for r in reqs if PEAK[0] * 60 <= r.t_arrival < PEAK[1] * 60], TARGET_T)
    s.update({"peak_Wq": pk["Wq_mean"], "peak_P": pk["P_wait_gt_target"], "peak_balk": pk["balk_rate"]})
    hours, cost = staffing_cost(servers)
    s.update({"name": name, "utilization": util["utilization"],
              "staff_hours": hours, "cost_per_day": cost, "lambda_scale": lambda_scale})
    return s, reqs


def sensitivity(plans):
    rows = []
    for scale in (0.8, 1.0, 1.2, 1.4):
        for name, servers, svc in plans:
            s, _ = scenario(name, servers, svc, days=30, seed=SEED + 7, lambda_scale=scale)
            peak = int(np.argmax(HOURLY_LAMBDA))
            m = q.metrics(HOURLY_LAMBDA[peak] * scale, 60.0 / mix_mean(svc),
                          servers[peak], TARGET_T)
            rows.append({"scale": scale, "name": name, "Wq_mean": s["Wq_mean"],
                         "Wq_p90": s["Wq_p90"], "P_gt": s["P_wait_gt_target"],
                         "balk": s["balk_rate"], "rho_peak": m["rho"]})
    return rows


# ----------------------------------------------------------- XUAT BANG ------
_DEC = re.compile(r"(?<=\d)\.(?=\d)")


def vn_decimal(s: str) -> str:
    """Dau thap phan kieu Viet Nam trong bang LaTeX: 0.64 -> 0{,}64 (CSV/log giu dau cham)."""
    return _DEC.sub("{,}", s)


def fmt(x, nd=2):
    return vn_decimal(_fmt(x, nd))


def _fmt(x, nd=2):
    if isinstance(x, bool):
        return "Đạt" if x else "Không đạt"
    if isinstance(x, (float, np.floating)):
        if not isfinite(x):
            return "--"
        return f"{x:,.{nd}f}".replace(",", "\\,")
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}".replace(",", "\\,")
    return str(x)


def write_tex_table(path, header, rows, nd=2, align=None):
    align = align or ("l" + "r" * (len(header) - 1))
    with open(path, "w") as f:
        f.write("\\begin{tabular}{" + align + "}\n\\toprule\n")
        f.write(" & ".join("\\textbf{" + h + "}" for h in header) + " \\\\\n\\midrule\n")
        for r in rows:
            f.write(" & ".join(fmt(v, nd) for v in r) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------- CHARTS ----
def setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.dpi": 200, "savefig.dpi": 200,
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.edgecolor": C_AXIS, "axes.labelcolor": C_INK,
        "text.color": C_INK, "xtick.color": C_MUTED, "ytick.color": C_MUTED,
        "axes.grid": True, "grid.color": C_GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "lines.linewidth": 2.0,
        "savefig.bbox": "tight", "figure.facecolor": "white",
    })
    return plt


def _finish(ax, plt, fname, rotate=False):
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    if rotate:
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.figure.savefig(os.path.join(FIGS, fname))
    plt.close(ax.figure)


def chart_arrivals(plt, est_rows):
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    labels = [r["hour"] for r in est_rows]
    vals = [r["lambda_hat"] for r in est_rows]
    ax.bar(labels, vals, color=C_BLUE, width=0.62)
    for x, v in zip(labels, vals):
        if v >= max(vals) - 3:
            ax.annotate(f"{v:.0f}", (x, v), textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=8, color=C_INK)
    ax.set_ylabel("Xe/giờ ($\\hat{\\lambda}$)")
    ax.set_xlabel("Khung giờ")
    ax.set_title("Lượt xe đến theo khung giờ (mô phỏng 20 ngày)")
    _finish(ax, plt, "fig_arrivals.png", rotate=True)


def chart_wq_by_hour(plt, rows_a0, rows_a1, rows_a2):
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    labels = [r["hour"] for r in rows_a0]
    cap = 20.0

    def clip(v):
        return min(v, cap) if isfinite(v) else cap

    for rows, col, mk, lab in [
            (rows_a0, C_BLUE, "o", "A0 – AS-IS (6 nhân viên cố định)"),
            (rows_a1, C_ORANGE, "s", "A1 – Lịch theo giờ, quy trình hiện tại"),
            (rows_a2, C_AQUA, "^", "A2 – Thanh toán số + lịch theo giờ")]:
        ax.plot(labels, [clip(r["Wq"]) for r in rows], color=col, marker=mk,
                markersize=4, label=lab)
    ax.axhline(TARGET_WQ_MEAN, color=C_MUTED, linestyle="--", linewidth=1.2)
    ax.annotate("Mục tiêu $W_q \\leq 2$ phút", (0.02, TARGET_WQ_MEAN + 0.6),
                xycoords=("axes fraction", "data"), fontsize=8, color=C_MUTED)
    ax.set_ylabel("$W_q$ (phút, cắt tại 20)")
    ax.set_xlabel("Khung giờ")
    ax.set_title("Thời gian chờ theo khung giờ (M/M/c) – ba phương án")
    ax.legend(loc="upper left", fontsize=8)
    _finish(ax, plt, "fig_wq_by_hour.png", rotate=True)


def chart_wq_vs_c(plt):
    fig, ax = plt.subplots(figsize=(5.4, 2.8))
    lam = max(HOURLY_LAMBDA)
    cs = list(range(4, C_MAX + 1))
    for ms, col, lab, mk in [(MEAN_SERVICE_ASIS, C_BLUE, f"E[S] = {MEAN_SERVICE_ASIS:.2f} phút (AS-IS)", "o"),
                             (MEAN_SERVICE_TOBE, C_AQUA, f"E[S] = {MEAN_SERVICE_TOBE:.2f} phút (TO-BE)", "^")]:
        mu = 60.0 / ms
        ys = [min(q.wq_min(lam, mu, c), 100) if q.utilization(lam, mu, c) < 1 else 100
              for c in cs]
        ax.plot(cs, ys, color=col, marker=mk, markersize=5, label=lab)
    ax.axhline(TARGET_WQ_MEAN, color=C_MUTED, linestyle="--", linewidth=1.2)
    ax.set_yscale("log")
    ax.set_xticks(cs)
    ax.set_xlabel("Số vị trí bơm có nhân viên $c$")
    ax.set_ylabel("$W_q$ (phút, trục log)")
    ax.set_title(f"Năng lực và thời gian chờ giờ cao điểm ($\\lambda$ = {lam} xe/giờ)")
    ax.legend(fontsize=8)
    _finish(ax, plt, "fig_wq_vs_c.png")


def chart_sensitivity(plt, rows):
    fig, ax = plt.subplots(figsize=(5.6, 2.8))
    names = list(dict.fromkeys(r["name"] for r in rows))
    for nm, col, mk in zip(names, (C_BLUE, C_ORANGE, C_AQUA), ("o", "s", "^")):
        xs = [r["scale"] for r in rows if r["name"] == nm]
        ys = [min(r["Wq_mean"], 30) for r in rows if r["name"] == nm]
        ax.plot(xs, ys, color=col, marker=mk, markersize=5, label=nm)
    ax.axhline(TARGET_WQ_MEAN, color=C_MUTED, linestyle="--", linewidth=1.2)
    ax.set_xticks([0.8, 1.0, 1.2, 1.4])
    ax.set_xlabel("Hệ số nhu cầu so với hiện tại")
    ax.set_ylabel("$W_q$ trung bình (phút, cắt tại 30)")
    ax.set_title("Độ nhạy theo mức nhu cầu (mô phỏng 30 ngày/kịch bản)")
    ax.legend(fontsize=8)
    _finish(ax, plt, "fig_sensitivity.png")


def chart_by_class(plt, sims):
    fig, ax = plt.subplots(figsize=(5.4, 2.7))
    x = np.arange(2)
    wd = 0.26
    for i, (s, col) in enumerate(zip(sims, (C_BLUE, C_ORANGE, C_AQUA))):
        vals = [s["Wq_mean_P1"], s["Wq_mean_P2"]]
        xs = x + (i - 1) * (wd + 0.02)
        ax.bar(xs, vals, wd, color=col, label=s["name"])
        for xi, v in zip(xs, vals):
            ax.annotate(f"{v:.2f}", (xi, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=7.5, color=C_INK)
    ax.set_xticks(x, [CLASS_NAME[1], CLASS_NAME[2]])
    ax.set_ylabel("$W_q$ trung bình (phút)")
    ax.set_title("Thời gian chờ theo loại xe (mô phỏng 20 ngày)")
    ax.legend(fontsize=8)
    _finish(ax, plt, "fig_by_class.png")


# ------------------------------------------------------------------ MAIN ----
def main():
    log = []

    def say(msg=""):
        print(msg)
        log.append(msg)

    say("=" * 78)
    say("DU AN INT3501 - NHOM 8 | Hang doi tai cua hang xang dau noi thanh Ha Noi")
    say(f"NHAN DU LIEU: {LABEL}")
    say("=" * 78)
    say("\n[0] Hieu chinh quy mo nhu cau")
    say(f"    {HN_PETROL_M3_MONTH:,} m3 xang/thang / {HN_STORES} cua hang / 30 ngay "
        f"= {LITRES_PER_STORE_DAY:,.0f} L/ngay/cua hang")
    say(f"    Xe may {MOTO_VOLUME_SHARE:.0%} san luong, {LITRES_PER_VISIT[2]} L/luot -> "
        f"{VISITS_MOTO:,.0f} luot/ngay; o to {LITRES_PER_VISIT[1]} L/luot -> "
        f"{VISITS_CAR:,.0f} luot/ngay; tong {VISITS_DAY:,.0f}")
    say(f"    Ty le o to theo luot = {CLASS_MIX[1]:.2%}; lambda theo gio = {HOURLY_LAMBDA} "
        f"(tong {sum(HOURLY_LAMBDA)})")
    say(f"    E[S] AS-IS = {MEAN_SERVICE_ASIS:.3f} phut; TO-BE = {MEAN_SERVICE_TOBE:.3f} phut")

    reqs, util, path = generate_dataset()
    est_rows, svc = estimate_parameters(reqs)
    say(f"\n[1] Du lieu mo phong AS-IS: {len(reqs)} luot / {DAYS} ngay -> {os.path.basename(path)}")
    say(f"    E[S] = {svc['mean']:.3f} phut; SD = {svc['sd']:.3f}; CV = {svc['cv']:.2f}; "
        f"mu = {svc['mu_per_hour']:.1f} xe/gio/kenh; muc su dung = {util['utilization']*100:.1f}%")
    write_csv(os.path.join(DATA, "lambda_by_hour.csv"),
              ["hour", "n_total", "lambda_hat", "lambda_assumed", "var_mean_ratio"],
              [[r["hour"], r["n_total"], round(r["lambda_hat"], 2), r["lambda_assumed"],
                round(r["var_mean_ratio"], 3)] for r in est_rows])
    write_tex_table(os.path.join(TABLES, "tab_lambda.tex"),
                    ["Khung giờ", "Số lượt (20 ngày)", "$\\hat{\\lambda}$ (xe/giờ)",
                     "$\\lambda$ giả định (xe/giờ)", "Var/Mean"],
                    [[r["hour"], r["n_total"], r["lambda_hat"], r["lambda_assumed"],
                      r["var_mean_ratio"]] for r in est_rows])

    val_rows = validate_formulas()
    say("\n[2] Kiem dinh Erlang C (CV = 1, mot lop xe, 40 ngay/cau hinh)")
    for r in val_rows:
        say(f"    lambda={r['lambda']:>4} c={r['c']}  rho={r['rho']:.3f}  "
            f"Wq_ct={r['Wq_analytic']:.3f}  Wq_mp={r['Wq_sim']:.3f}  lech={r['gap_pct']:.1f}%")
    write_tex_table(os.path.join(TABLES, "tab_validation.tex"),
                    ["$\\lambda$ (xe/giờ)", "$c$", "$\\rho$", "$W_q$ công thức (phút)",
                     "$W_q$ mô phỏng (phút)", "Chênh lệch (\\%)"],
                    [[r["lambda"], r["c"], r["rho"], r["Wq_analytic"], r["Wq_sim"],
                      r["gap_pct"]] for r in val_rows], nd=3)

    rows_a0 = per_hour_table(SERVERS_ASIS, MEAN_SERVICE_ASIS)
    say("\n[3] AS-IS theo gio (c = 6, M/M/c)")
    for r in rows_a0:
        say(f"    {r['hour']}  lambda={r['lambda']:>4}  rho={r['rho']:.2f}  Wq={_fmt(r['Wq'])}  "
            f"P(Wq>5)={r['P_gt']*100:.2f}%  {'DAT' if r['feasible'] else 'KHONG DAT'}")
    write_tex_table(os.path.join(TABLES, "tab_asis_hourly.tex"),
                    ["Khung giờ", "$\\lambda$ (xe/giờ)", "$c$", "$\\rho$", "$L_q$ (xe)",
                     "$W_q$ (phút)", "$W_q^{90}$ (phút)", "$P(W_q{>}5)$", "Mục tiêu"],
                    [[r["hour"], r["lambda"], r["c"], r["rho"], r["Lq"], r["Wq"],
                      r["Wq_p90"], r["P_gt"], r["feasible"]] for r in rows_a0])

    opt_a1 = optimize_staffing(MEAN_SERVICE_ASIS)
    opt_a2 = optimize_staffing(MEAN_SERVICE_TOBE)
    servers_a1 = [r["c_star"] for r in opt_a1]
    servers_a2 = [r["c_star"] for r in opt_a2]
    rows_a1 = per_hour_table(servers_a1, MEAN_SERVICE_ASIS)
    rows_a2 = per_hour_table(servers_a2, MEAN_SERVICE_TOBE)
    (h0, c0), (h1, c1), (h2, c2) = map(staffing_cost, (SERVERS_ASIS, servers_a1, servers_a2))
    say("\n[4] Toi uu lich theo gio")
    say(f"    A1 (E[S] AS-IS)  c* = {servers_a1}  -> {h1} gio-nhan vien/ngay")
    say(f"    A2 (E[S] TO-BE)  c* = {servers_a2}  -> {h2} gio-nhan vien/ngay")
    say(f"    Chi phi nhan luc/ngay: A0 {c0:,} | A1 {c1:,} | A2 {c2:,} (+ cong nghe {TECH_COST_DAY:,})")
    write_tex_table(os.path.join(TABLES, "tab_optimization.tex"),
                    ["Khung giờ", "$\\lambda$ (xe/giờ)", "$c^*$", "$\\rho$", "$W_q$ (phút)",
                     "$W_q^{90}$ (phút)", "$P(W_q{>}5)$", "Mục tiêu"],
                    [[r["hour"], r["lambda"], r["c_star"], r["rho"], r["Wq"], r["Wq_p90"],
                      r["P_gt"], r["feasible"]] for r in opt_a2])
    with open(os.path.join(TABLES, "tab_shift_plan.tex"), "w") as f:
        hrs = [hour_label(h)[:2] for h in range(HOURS)]
        f.write("\\begin{tabular}{l" + "c" * HOURS + "r}\n\\toprule\n")
        f.write("\\textbf{Giờ bắt đầu} & " + " & ".join(hrs) + " & \\textbf{Tổng} \\\\\n\\midrule\n")
        f.write("$\\lambda$ (xe/giờ) & " + " & ".join(str(l) for l in HOURLY_LAMBDA)
                + f" & {sum(HOURLY_LAMBDA)} \\\\\n")
        for nm, sv in [("A0 $c$", SERVERS_ASIS), ("A1 $c^*$", servers_a1), ("A2 $c^*$", servers_a2)]:
            f.write(nm + " & " + " & ".join(str(c) for c in sv) + f" & {sum(sv)} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    s_a0, _ = scenario("A0 – AS-IS", SERVERS_ASIS, SERVICE_ASIS)
    s_a1, _ = scenario("A1 – Lịch theo giờ", servers_a1, SERVICE_ASIS)
    s_a2, _ = scenario("A2 – Số hóa + lịch", servers_a2, SERVICE_TOBE)
    say("\n[5] So sanh ba phuong an (mo phong 20 ngay, CV = 0,8)")
    for s in (s_a0, s_a1, s_a2):
        say(f"    {s['name']:<20} Wq={s['Wq_mean']:.3f} p90={s['Wq_p90']:.3f} "
            f"P>5={s['P_wait_gt_target']*100:.2f}% bo={s['balk_rate']*100:.2f}% oto={s['Wq_mean_P1']:.3f} "
            f"xemay={s['Wq_mean_P2']:.3f} rho={s['utilization']*100:.1f}% gio={s['staff_hours']} | "
            f"17-19h: Wq={s['peak_Wq']:.3f} P>5={s['peak_P']*100:.2f}% bo={s['peak_balk']*100:.2f}%")
    tech = [0, 0, TECH_COST_DAY]
    sims = (s_a0, s_a1, s_a2)
    comp_header = ["Chỉ số (đơn vị)", "A0 -- AS-IS", "A1 -- Lịch theo giờ", "A2 -- Số hóa + lịch"]
    comp_rows = [
        ["Số lượt xe mô phỏng (lượt)"] + [s["n"] for s in sims],
        ["$W_q$ trung bình (phút)"] + [s["Wq_mean"] for s in sims],
        ["$W_q^{90}$ (phút)"] + [s["Wq_p90"] for s in sims],
        ["$W_q$ tối đa (phút)"] + [s["Wq_max"] for s in sims],
        ["Tỷ lệ phải chờ (\\%)"] + [s["P_wait_gt_0"] * 100 for s in sims],
        ["$P(W_q>5)$ (\\%)"] + [s["P_wait_gt_target"] * 100 for s in sims],
        ["Khách bỏ đi vì hàng dài (\\%)"] + [s["balk_rate"] * 100 for s in sims],
        ["$W_q$ giờ 17--19 (phút)"] + [s["peak_Wq"] for s in sims],
        ["$P(W_q>5)$ giờ 17--19 (\\%)"] + [s["peak_P"] * 100 for s in sims],
        ["Bỏ đi giờ 17--19 (\\%)"] + [s["peak_balk"] * 100 for s in sims],
        ["$W_q$ ô tô (phút)"] + [s["Wq_mean_P1"] for s in sims],
        ["$W_q$ xe máy (phút)"] + [s["Wq_mean_P2"] for s in sims],
        ["Mức sử dụng nhân viên (\\%)"] + [s["utilization"] * 100 for s in sims],
        ["Giờ--nhân viên/ngày (giờ)"] + [s["staff_hours"] for s in sims],
        ["Chi phí nhân lực (nghìn đ/ngày)"] + [s["cost_per_day"] / 1000 for s in sims],
        ["Chi phí công nghệ (nghìn đ/ngày)"] + [t / 1000 for t in tech],
    ]
    write_tex_table(os.path.join(TABLES, "tab_comparison.tex"), comp_header, comp_rows,
                    align="p{0.36\\linewidth}rrr")
    write_csv(os.path.join(DATA, "comparison.csv"), comp_header,
              [[c if isinstance(c, str) else round(float(c), 4) for c in r] for r in comp_rows])

    plans = [("A0 – AS-IS", SERVERS_ASIS, SERVICE_ASIS),
             ("A1 – Lịch theo giờ", servers_a1, SERVICE_ASIS),
             ("A2 – Số hóa + lịch", servers_a2, SERVICE_TOBE)]
    sens = sensitivity(plans)
    say("\n[6] Do nhay theo nhu cau (30 ngay, seed rieng)")
    for r in sens:
        say(f"    x{r['scale']:.1f}  {r['name']:<20} Wq={r['Wq_mean']:7.3f}  "
            f"p90={r['Wq_p90']:7.3f}  P>5={r['P_gt']*100:6.2f}%  bo={r['balk']*100:5.2f}%  rho_peak={r['rho_peak']:.2f}")
    write_tex_table(os.path.join(TABLES, "tab_sensitivity.tex"),
                    ["Hệ số nhu cầu", "Phương án", "$W_q$ (phút)", "$W_q^{90}$ (phút)",
                     "$P(W_q{>}5)$ (\\%)", "Bỏ đi (\\%)", "$\\rho$ cao điểm"],
                    [[f"$\\times${r['scale']:.1f}", r["name"], r["Wq_mean"], r["Wq_p90"],
                      r["P_gt"] * 100, r["balk"] * 100, r["rho_peak"]] for r in sens],
                    align="llrrrrr")

    reduced = [max(1, c - 1) for c in servers_a2]
    s_abs, _ = scenario("A2 thiếu 1 nhân viên", reduced, SERVICE_TOBE, days=30, seed=SEED + 11)
    svc_low = {k: v * 0.90 for k, v in SERVICE_ASIS.items()}
    s_low, _ = scenario("A2 số hóa chỉ giảm 10%", servers_a2, svc_low, days=30, seed=SEED + 13)
    say(f"\n[7] Rui ro: thieu 1 nhan vien moi gio -> Wq={s_abs['Wq_mean']:.3f}, "
        f"P>5={s_abs['P_wait_gt_target']*100:.2f}%, bo di={s_abs['balk_rate']*100:.2f}%")
    say(f"    So hoa chi giam 10% (E[S]={mix_mean(svc_low):.3f}) -> Wq={s_low['Wq_mean']:.3f}, "
        f"P>5={s_low['P_wait_gt_target']*100:.2f}%, bo di={s_low['balk_rate']*100:.2f}%")
    write_tex_table(os.path.join(TABLES, "tab_risk.tex"),
                    ["Tình huống rủi ro", "$W_q$ (phút)", "$W_q^{90}$ (phút)",
                     "$P(W_q{>}5)$ (\\%)", "Bỏ đi (\\%)"],
                    [["A2 theo thiết kế", s_a2["Wq_mean"], s_a2["Wq_p90"],
                      s_a2["P_wait_gt_target"] * 100, s_a2["balk_rate"] * 100],
                     ["Thiếu 1 nhân viên ở mọi khung giờ", s_abs["Wq_mean"], s_abs["Wq_p90"],
                      s_abs["P_wait_gt_target"] * 100, s_abs["balk_rate"] * 100],
                     ["Số hóa chỉ giảm 10\\% thời gian phục vụ", s_low["Wq_mean"], s_low["Wq_p90"],
                      s_low["P_wait_gt_target"] * 100, s_low["balk_rate"] * 100]],
                    align="p{0.40\\linewidth}rrrr")

    plt = setup_mpl()
    chart_arrivals(plt, est_rows)
    chart_wq_by_hour(plt, rows_a0, rows_a1, rows_a2)
    chart_wq_vs_c(plt)
    chart_sensitivity(plt, sens)
    chart_by_class(plt, sims)
    say(f"\n[8] Da xuat 5 hinh vao figures/")

    with open(os.path.join(DATA, "run_log.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    say("Hoan tat.")


if __name__ == "__main__":
    main()
