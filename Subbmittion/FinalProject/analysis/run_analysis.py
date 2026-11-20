"""Chuong trinh phan tich chinh cho du an INT3501 - Nhom 8.

Chay:  python3 run_analysis.py
Dau ra: data/*.csv, tables/*.tex, ../figures/*.png

CANH BAO VE DU LIEU: toan bo du lieu su dung trong bao cao la DU LIEU MO PHONG
duoc sinh bang `simulate.py` voi cac gia dinh ghi trong CONFIG duoi day. Du lieu
nay KHONG phai du lieu quan sat thuc te tai mot co so y te. Cac tham so dau vao
(cuong do den theo gio, thoi gian xu ly, ty le muc uu tien) duoc dat theo thu
nguyen hop ly cua mot phong kham ngoai tru quy mo vua va duoc khai bao minh bach
de nguoi doc co the thay the bang du lieu thuc khi co.
"""

from __future__ import annotations

import csv
import os
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
OPEN_HOUR = 7                       # cua so tiep nhan 07:00-19:00
HOURS = 12
DAYS = 20                           # 20 ngay lam viec mo phong

# Gia dinh G1: cuong do den theo gio (yeu cau/gio), tong ~100 yeu cau/ngay
HOURLY_LAMBDA = [6, 10, 12, 11, 8, 5, 7, 10, 11, 9, 7, 4]

# Gia dinh G2: co cau muc uu tien sau phan loai
CLASS_MIX = {1: 0.12, 2: 0.58, 3: 0.30}
CLASS_NAME = {1: "P1 – Khẩn", 2: "P2 – Thường", 3: "P3 – Thấp"}

# Gia dinh G3: thoi gian xu ly mot yeu cau tai tram dieu duong
MEAN_SERVICE_ASIS = 9.0             # phut, chua co ban tom tat tu dong
MEAN_SERVICE_TOBE = 6.0             # phut, co ban tom tat do AI chuan bi
CV_SERVICE = 1.25                   # he so bien thien quan sat tu du lieu mo phong

# Gia dinh G4: lich truc hien tai va chi phi
SERVERS_ASIS = [2] * HOURS
COST_PER_SERVER_HOUR = 120_000      # VND/gio/dieu duong

# Muc dich vu cam ket (service level targets)
TARGET_WQ_MEAN = 10.0               # phut
TARGET_T = 15.0                     # nguong "cho qua lau" (phut)
TARGET_TAIL = 0.05                  # P(Wq > 15 phut) <= 5%
TARGET_WQ_P1 = 5.0                  # phut, rieng nhom uu tien P1
C_MAX = 5

SEED = 20260117
LABEL = "Du lieu mo phong (simulated), khong phai du lieu thuc te"

# Mau ve (palette da kiem dinh, che do sang)
C_BLUE, C_ORANGE, C_AQUA = "#2a78d6", "#eb6834", "#1baf7a"
C_GRID, C_AXIS, C_INK, C_MUTED = "#e1e0d9", "#c3c2b7", "#2b2b28", "#6b6b63"


def hour_label(h: int) -> str:
    return f"{OPEN_HOUR + h:02d}-{OPEN_HOUR + h + 1:02d}"


# ------------------------------------------------- 1. SINH DU LIEU & ETL ----
def generate_dataset():
    cfg = SimConfig(
        hourly_lambda=HOURLY_LAMBDA, class_mix=CLASS_MIX,
        mean_service_min=MEAN_SERVICE_ASIS, cv_service=CV_SERVICE,
        servers_by_hour=SERVERS_ASIS, priority_rule=False,
        days=DAYS, seed=SEED,
    )
    reqs, util = run(cfg)
    path = os.path.join(DATA, "requests_asis_simulated.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data_label", "day", "request_id", "priority", "hour_slot",
                    "t_arrival_min", "t_service_start_min", "t_service_end_min",
                    "service_min", "wait_min"])
        for r in reqs:
            w.writerow(["SIMULATED", r.day, r.rid, r.priority,
                        hour_label(min(int(r.t_arrival // 60), HOURS - 1)),
                        round(r.t_arrival, 3), round(r.t_start, 3),
                        round(r.t_end, 3), round(r.service, 3), round(r.wq, 3)])
    return reqs, util, path


def estimate_parameters(reqs):
    """Uoc luong lambda theo gio, E[S], CV va kiem tra gia dinh Poisson."""
    rows = []
    for h in range(HOURS):
        n = sum(1 for r in reqs if int(r.t_arrival // 60) == h)
        lam_hat = n / DAYS
        # kiem tra Poisson tho: ty so phuong sai/trung binh cua so luot den
        per_day = [sum(1 for r in reqs if r.day == d and int(r.t_arrival // 60) == h)
                   for d in range(1, DAYS + 1)]
        arr = np.array(per_day, dtype=float)
        vmr = float(arr.var(ddof=1) / arr.mean()) if arr.mean() > 0 else float("nan")
        rows.append({"hour": hour_label(h), "n_total": n, "lambda_hat": lam_hat,
                     "lambda_assumed": HOURLY_LAMBDA[h], "var_mean_ratio": vmr})
    svc = np.array([r.service for r in reqs])
    svc_stats = {"n": len(svc), "mean": float(svc.mean()), "sd": float(svc.std(ddof=1)),
                 "cv": float(svc.std(ddof=1) / svc.mean()),
                 "p50": float(np.percentile(svc, 50)),
                 "p90": float(np.percentile(svc, 90)),
                 "mu_per_hour": 60.0 / float(svc.mean())}
    return rows, svc_stats


# -------------------------------------- 2. KIEM DINH CONG THUC M/M/s --------
def validate_formulas():
    """So sanh Erlang C voi DES khi thoi gian phuc vu la phan phoi mu (CV = 1)."""
    rows = []
    for lam, c in [(6, 2), (10, 2), (12, 2), (12, 3), (8, 1)]:
        mu = 60.0 / MEAN_SERVICE_ASIS
        if q.utilization(lam, mu, c) >= 1:
            rows.append({"lambda": lam, "c": c, "rho": q.utilization(lam, mu, c),
                         "Wq_analytic": float("inf"), "Wq_sim": float("nan"),
                         "gap_pct": float("nan")})
            continue
        ana = q.metrics(lam, mu, c, TARGET_T)
        cfg = SimConfig(hourly_lambda=[lam] * 12, class_mix={2: 1.0},
                        mean_service_min=MEAN_SERVICE_ASIS, cv_service=1.0,
                        servers_by_hour=[c] * 12, priority_rule=False,
                        days=200, seed=SEED + c + lam)
        reqs, _ = run(cfg)
        # bo 1 gio dau moi ngay de giam anh huong giai doan chuyen tiep
        reqs = [r for r in reqs if r.t_arrival >= 60]
        s = summarize(reqs, TARGET_T)
        rows.append({"lambda": lam, "c": c, "rho": ana["rho"],
                     "Wq_analytic": ana["Wq"], "Wq_sim": s["Wq_mean"],
                     "gap_pct": 100 * (s["Wq_mean"] - ana["Wq"]) / ana["Wq"]})
    return rows


# ------------------------------------------- 3. DANH GIA CAU HINH AS-IS -----
def per_hour_table(servers, mean_service):
    mu = 60.0 / mean_service
    rows = []
    for h in range(HOURS):
        lam = HOURLY_LAMBDA[h]
        c = servers[h]
        m = q.metrics(lam, mu, c, TARGET_T)
        rows.append({"hour": hour_label(h), "lambda": lam, "c": c, "rho": m["rho"],
                     "Lq": m["Lq"], "Wq": m["Wq"], "Wq_p90": m["Wq_p90"],
                     "P_gt_15": m["P_gt_target"], "feasible": feasible(m)})
    return rows


def feasible(m) -> bool:
    return (m["stable"] and m["Wq"] <= TARGET_WQ_MEAN + 1e-9
            and m["P_gt_target"] <= TARGET_TAIL + 1e-12)


# ----------------------------------------------- 4. BAI TOAN TOI UU HOA -----
def optimize_staffing(mean_service):
    """min sum_t c_t * cost  s.t. rho_t < 1, Wq_t <= 10 phut, P(Wq_t > 15) <= 5%.

    Bai toan tach duoc theo tung gio nen nghiem toi uu tim bang cach do dan
    c_t = 1..C_MAX va chon gia tri nho nhat con kha thi (chung minh trong bao cao).
    """
    mu = 60.0 / mean_service
    rows = []
    for h in range(HOURS):
        lam = HOURLY_LAMBDA[h]
        chosen, chosen_m = None, None
        for c in range(1, C_MAX + 1):
            m = q.metrics(lam, mu, c, TARGET_T)
            if feasible(m):
                chosen, chosen_m = c, m
                break
        if chosen is None:          # khong cau hinh nao kha thi -> "kenh ao"
            chosen = C_MAX
            chosen_m = q.metrics(lam, mu, C_MAX, TARGET_T)
        rows.append({"hour": hour_label(h), "lambda": lam, "c_star": chosen,
                     "rho": chosen_m["rho"], "Wq": chosen_m["Wq"],
                     "Wq_p90": chosen_m["Wq_p90"],
                     "P_gt_15": chosen_m["P_gt_target"],
                     "feasible": feasible(chosen_m)})
    return rows


def staffing_cost(servers):
    nurse_hours = sum(servers)
    return nurse_hours, nurse_hours * COST_PER_SERVER_HOUR


# --------------------------------------------- 5. SO SANH BA PHUONG AN ------
def scenario(name, servers, mean_service, priority_rule, days=DAYS, seed=SEED,
             lambda_scale=1.0):
    lam_profile = [l * lambda_scale for l in HOURLY_LAMBDA]
    cfg = SimConfig(hourly_lambda=lam_profile, class_mix=CLASS_MIX,
                    mean_service_min=mean_service, cv_service=CV_SERVICE,
                    servers_by_hour=servers, priority_rule=priority_rule,
                    days=days, seed=seed)
    reqs, util = run(cfg)
    s = summarize(reqs, TARGET_T)
    nurse_hours, cost = staffing_cost(servers)
    s.update({"name": name, "utilization": util["utilization"],
              "nurse_hours_per_day": nurse_hours,
              "cost_per_day": cost, "mean_service": mean_service,
              "priority": priority_rule, "lambda_scale": lambda_scale})
    return s, reqs


# ------------------------------------------------- 6. PHAN TICH DO NHAY -----
def sensitivity(scenarios):
    rows = []
    for scale in (0.8, 1.0, 1.2, 1.4):
        for name, servers, ms, pri in scenarios:
            s, _ = scenario(name, servers, ms, pri, days=30, seed=SEED + 7,
                            lambda_scale=scale)
            peak_h = int(np.argmax(HOURLY_LAMBDA))
            mu = 60.0 / ms
            m_peak = q.metrics(HOURLY_LAMBDA[peak_h] * scale, mu, servers[peak_h],
                               TARGET_T)
            rows.append({"scale": scale, "name": name,
                         "Wq_mean": s["Wq_mean"], "Wq_p90": s["Wq_p90"],
                         "P_gt_15": s["P_wait_gt_target"],
                         "rho_peak": m_peak["rho"],
                         "Wq_peak_analytic": m_peak["Wq"]})
    return rows


def robustness_absence(servers_tobe):
    """Mot dieu duong vang mat: kiem tra tinh kha thi cua lich truc TO-BE."""
    reduced = [max(1, c - 1) for c in servers_tobe]
    s, _ = scenario("TO-BE thieu 1 dieu duong", reduced, MEAN_SERVICE_TOBE,
                    True, days=30, seed=SEED + 11)
    return reduced, s


def partial_ai_benefit(servers_tobe):
    """AI chi giam 15% thoi gian xu ly thay vi 33%."""
    ms = MEAN_SERVICE_ASIS * 0.85
    s, _ = scenario("TO-BE voi loi ich AI thap", servers_tobe, ms, True,
                    days=30, seed=SEED + 13)
    return ms, s


# ----------------------------------------------------------- XUAT BANG ------
def fmt(x, nd=2):
    if isinstance(x, bool):
        return "Đạt" if x else "Không đạt"
    if isinstance(x, float):
        if not isfinite(x):
            return "$\\infty$"
        return f"{x:,.{nd}f}".replace(",", " ")
    return str(x)


def write_tex_table(path, header, rows, nd=2, align=None):
    ncol = len(header)
    align = align or ("l" + "r" * (ncol - 1))
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


def chart_arrivals(plt, est_rows):
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    labels = [r["hour"] for r in est_rows]
    vals = [r["lambda_hat"] for r in est_rows]
    ax.bar(labels, vals, color=C_BLUE, width=0.62)
    for x, v in zip(labels, vals):
        if v >= max(vals) - 0.3:
            ax.annotate(f"{v:.1f}", (x, v), textcoords="offset points",
                        xytext=(0, 3), ha="center", fontsize=8, color=C_INK)
    ax.set_ylabel("Yêu cầu/giờ ($\\hat{\\lambda}$)")
    ax.set_xlabel("Khung giờ")
    ax.set_title("Cường độ đến ước lượng theo khung giờ (dữ liệu mô phỏng, 20 ngày)")
    ax.set_axisbelow(True)
    ax.grid(axis="x", visible=False)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.savefig(os.path.join(FIGS, "fig_arrivals.png"))
    plt.close(fig)


def chart_wq_by_hour(plt, rows_a0, rows_a1, rows_tobe):
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    labels = [r["hour"] for r in rows_a0]
    cap = 60.0

    def clip(v):
        return min(v, cap) if isfinite(v) else cap

    ax.plot(labels, [clip(r["Wq"]) for r in rows_a0], color=C_BLUE,
            marker="o", markersize=4, label="A0 – AS-IS (2 điều dưỡng, 9 phút/yc)")
    ax.plot(labels, [clip(r["Wq"]) for r in rows_a1], color=C_ORANGE,
            marker="s", markersize=4, label="A1 – Chỉ tăng nhân lực giờ cao điểm")
    ax.plot(labels, [clip(r["Wq"]) for r in rows_tobe], color=C_AQUA,
            marker="^", markersize=4, label="A2 – TO-BE (AI + lịch trực tối ưu)")
    ax.axhline(TARGET_WQ_MEAN, color=C_MUTED, linestyle="--", linewidth=1.2)
    ax.annotate("Mức cam kết $W_q \\leq 10$ phút", (0.02, TARGET_WQ_MEAN + 1.5),
                xycoords=("axes fraction", "data"), fontsize=8, color=C_MUTED)
    ax.set_ylabel("$W_q$ (phút, cắt tại 60)")
    ax.set_xlabel("Khung giờ")
    ax.set_title("Thời gian chờ trung bình theo khung giờ – ba phương án")
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.savefig(os.path.join(FIGS, "fig_wq_by_hour.png"))
    plt.close(fig)


def chart_wq_vs_c(plt):
    fig, ax = plt.subplots(figsize=(5.4, 2.8))
    lam = max(HOURLY_LAMBDA)
    cs = list(range(1, C_MAX + 1))
    for mean_s, color, lab, mk in [
        (MEAN_SERVICE_ASIS, C_BLUE, f"E[S] = {MEAN_SERVICE_ASIS:.0f} phút (AS-IS)", "o"),
        (MEAN_SERVICE_TOBE, C_AQUA, f"E[S] = {MEAN_SERVICE_TOBE:.0f} phút (TO-BE)", "^"),
    ]:
        mu = 60.0 / mean_s
        ys = [min(q.wq_min(lam, mu, c), 120) if q.utilization(lam, mu, c) < 1 else 120
              for c in cs]
        ax.plot(cs, ys, color=color, marker=mk, markersize=5, label=lab)
    ax.axhline(TARGET_WQ_MEAN, color=C_MUTED, linestyle="--", linewidth=1.2)
    ax.set_yscale("log")
    ax.set_xticks(cs)
    ax.set_xlabel("Số điều dưỡng trực đồng thời $c$")
    ax.set_ylabel("$W_q$ (phút, trục log)")
    ax.set_title(f"Đánh đổi năng lực – thời gian chờ tại giờ cao điểm ($\\lambda$ = {lam} yc/giờ)")
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(FIGS, "fig_wq_vs_c.png"))
    plt.close(fig)


def chart_sensitivity(plt, sens_rows):
    fig, ax = plt.subplots(figsize=(5.6, 2.8))
    names = []
    for r in sens_rows:
        if r["name"] not in names:
            names.append(r["name"])
    colors = {names[0]: C_BLUE, names[1]: C_ORANGE, names[2]: C_AQUA}
    marks = {names[0]: "o", names[1]: "s", names[2]: "^"}
    for nm in names:
        xs = [r["scale"] for r in sens_rows if r["name"] == nm]
        ys = [min(r["Wq_mean"], 90) for r in sens_rows if r["name"] == nm]
        ax.plot(xs, ys, color=colors[nm], marker=marks[nm], markersize=5, label=nm)
    ax.axhline(TARGET_WQ_MEAN, color=C_MUTED, linestyle="--", linewidth=1.2)
    ax.set_xticks([0.8, 1.0, 1.2, 1.4])
    ax.set_xlabel("Hệ số nhu cầu so với hiện tại")
    ax.set_ylabel("$W_q$ trung bình ngày (phút)")
    ax.set_title("Độ nhạy theo mức nhu cầu (mô phỏng 30 ngày/kịch bản)")
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(FIGS, "fig_sensitivity.png"))
    plt.close(fig)


def chart_priority(plt, s_a0, s_a2):
    fig, ax = plt.subplots(figsize=(5.4, 2.7))
    groups = [CLASS_NAME[1], CLASS_NAME[2], CLASS_NAME[3]]
    a0 = [s_a0[f"Wq_mean_P{p}"] for p in (1, 2, 3)]
    a2 = [s_a2[f"Wq_mean_P{p}"] for p in (1, 2, 3)]
    x = np.arange(len(groups))
    wd = 0.34
    ax.bar(x - wd / 2 - 0.01, a0, wd, color=C_BLUE, label="A0 – AS-IS (FCFS)")
    ax.bar(x + wd / 2 + 0.01, a2, wd, color=C_AQUA, label="A2 – TO-BE (ưu tiên)")
    for xi, v in zip(x - wd / 2 - 0.01, a0):
        ax.annotate(f"{v:.1f}", (xi, v), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=8, color=C_INK)
    for xi, v in zip(x + wd / 2 + 0.01, a2):
        ax.annotate(f"{v:.1f}", (xi, v), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=8, color=C_INK)
    ax.set_xticks(x, groups)
    ax.set_ylabel("$W_q$ trung bình (phút)")
    ax.set_title("Thời gian chờ theo mức ưu tiên")
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(FIGS, "fig_priority.png"))
    plt.close(fig)


# ------------------------------------------------------------------ MAIN ----
def main():
    log = []

    def say(msg=""):
        print(msg)
        log.append(msg)

    say("=" * 78)
    say("DU AN INT3501 - NHOM 8 | Phan tich hang doi tram tu van - phan loai")
    say(f"NHAN DU LIEU: {LABEL}")
    say("=" * 78)

    # 1. Du lieu
    reqs, util, path = generate_dataset()
    est_rows, svc = estimate_parameters(reqs)
    say(f"\n[1] Du lieu mo phong: {len(reqs)} yeu cau / {DAYS} ngay -> {path}")
    say(f"    E[S] = {svc['mean']:.2f} phut; SD = {svc['sd']:.2f}; CV = {svc['cv']:.2f}; "
        f"mu = {svc['mu_per_hour']:.2f} yc/gio/kenh")
    say(f"    Muc su dung dieu duong (AS-IS): {util['utilization']*100:.1f}%")

    write_csv(os.path.join(DATA, "lambda_by_hour.csv"),
              ["hour", "n_total", "lambda_hat", "lambda_assumed", "var_mean_ratio"],
              [[r["hour"], r["n_total"], round(r["lambda_hat"], 3),
                r["lambda_assumed"], round(r["var_mean_ratio"], 3)] for r in est_rows])
    write_tex_table(
        os.path.join(TABLES, "tab_lambda.tex"),
        ["Khung giờ", "Số lượt (20 ngày)", "$\\hat{\\lambda}$ (yc/gio)",
         "$\\lambda$ giả định", "Var/Mean"],
        [[r["hour"], r["n_total"], r["lambda_hat"], r["lambda_assumed"],
          r["var_mean_ratio"]] for r in est_rows])

    # 2. Kiem dinh cong thuc
    val_rows = validate_formulas()
    say("\n[2] Kiem dinh Erlang C bang mo phong (CV = 1, FCFS, 200 ngay/cau hinh)")
    for r in val_rows:
        say(f"    lambda={r['lambda']:>3} c={r['c']}  rho={r['rho']:.3f}  "
            f"Wq_lythuyet={r['Wq_analytic']:.2f}  Wq_mophong={r['Wq_sim']:.2f}  "
            f"lech={r['gap_pct']:.1f}%")
    write_tex_table(
        os.path.join(TABLES, "tab_validation.tex"),
        ["$\\lambda$ (yc/gio)", "$c$", "$\\rho$", "$W_q$ công thức (phút)",
         "$W_q$ mô phỏng (phút)", "Chênh lệch (\\%)"],
        [[r["lambda"], r["c"], r["rho"], r["Wq_analytic"], r["Wq_sim"],
          r["gap_pct"]] for r in val_rows])

    # 3. AS-IS theo gio
    rows_a0 = per_hour_table(SERVERS_ASIS, MEAN_SERVICE_ASIS)
    say("\n[3] Cau hinh AS-IS (c = 2 ca ngay, E[S] = 9 phut)")
    for r in rows_a0:
        say(f"    {r['hour']}  lambda={r['lambda']:>3}  rho={r['rho']:.2f}  "
            f"Wq={fmt(r['Wq'])}  P(Wq>15)={fmt(r['P_gt_15']*100 if isfinite(r['P_gt_15']) else r['P_gt_15'])}%  "
            f"{'DAT' if r['feasible'] else 'KHONG DAT'}")
    write_tex_table(
        os.path.join(TABLES, "tab_asis_hourly.tex"),
        ["Khung giờ", "$\\lambda$", "$c$", "$\\rho$", "$L_q$", "$W_q$ (phút)",
         "$W_q^{90}$ (phút)", "$P(W_q>15)$", "Mức cam kết"],
        [[r["hour"], r["lambda"], r["c"], r["rho"], r["Lq"], r["Wq"],
          r["Wq_p90"], r["P_gt_15"], r["feasible"]] for r in rows_a0])

    # 3b. Phuong an A1: chi tang nhan luc
    servers_a1 = [3 if HOURLY_LAMBDA[h] >= 10 else 2 for h in range(HOURS)]
    rows_a1 = per_hour_table(servers_a1, MEAN_SERVICE_ASIS)

    # 4. Toi uu hoa lich truc TO-BE
    opt_rows = optimize_staffing(MEAN_SERVICE_TOBE)
    servers_tobe = [r["c_star"] for r in opt_rows]
    rows_tobe = per_hour_table(servers_tobe, MEAN_SERVICE_TOBE)
    nh0, cost0 = staffing_cost(SERVERS_ASIS)
    nh1, cost1 = staffing_cost(servers_a1)
    nh2, cost2 = staffing_cost(servers_tobe)
    say("\n[4] Nghiem bai toan toi uu lich truc TO-BE (E[S] = 6 phut)")
    for r in opt_rows:
        say(f"    {r['hour']}  lambda={r['lambda']:>3}  c*={r['c_star']}  "
            f"rho={r['rho']:.2f}  Wq={r['Wq']:.2f}  P(Wq>15)={r['P_gt_15']*100:.2f}%")
    say(f"    Gio-dieu duong/ngay: AS-IS {nh0} | A1 {nh1} | TO-BE {nh2}")
    say(f"    Chi phi truc/ngay (VND): AS-IS {cost0:,} | A1 {cost1:,} | TO-BE {cost2:,}")
    write_tex_table(
        os.path.join(TABLES, "tab_optimization.tex"),
        ["Khung giờ", "$\\lambda$", "$c^*$", "$\\rho$", "$W_q$ (phút)",
         "$W_q^{90}$ (phút)", "$P(W_q>15)$", "Mức cam kết"],
        [[r["hour"], r["lambda"], r["c_star"], r["rho"], r["Wq"], r["Wq_p90"],
          r["P_gt_15"], r["feasible"]] for r in opt_rows])
    write_tex_table(
        os.path.join(TABLES, "tab_shift_plan.tex"),
        ["Khung giờ"] + [r["hour"] for r in opt_rows][:0] or ["Khung giờ"],
        [], 2)
    # bang lich truc dang ngang
    with open(os.path.join(TABLES, "tab_shift_plan.tex"), "w") as f:
        hours = [r["hour"] for r in opt_rows]
        f.write("\\begin{tabular}{l" + "c" * len(hours) + "}\n\\toprule\n")
        f.write("\\textbf{Khung giờ} & " + " & ".join(h.replace("-", "--") for h in hours) + " \\\\\n\\midrule\n")
        f.write("$\\lambda$ (yc/giờ) & " + " & ".join(str(l) for l in HOURLY_LAMBDA) + " \\\\\n")
        f.write("AS-IS $c$ & " + " & ".join(str(c) for c in SERVERS_ASIS) + " \\\\\n")
        f.write("A1 $c$ & " + " & ".join(str(c) for c in servers_a1) + " \\\\\n")
        f.write("TO-BE $c^*$ & " + " & ".join(str(c) for c in servers_tobe) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    # 5. So sanh ba phuong an bang mo phong (cung dieu kien nhu cau)
    s_a0, _ = scenario("A0 – AS-IS", SERVERS_ASIS, MEAN_SERVICE_ASIS, False)
    s_a1, _ = scenario("A1 – Tăng nhân lực", servers_a1, MEAN_SERVICE_ASIS, False)
    s_a2, _ = scenario("A2 – TO-BE", servers_tobe, MEAN_SERVICE_TOBE, True)
    for s, (nh, cost) in zip((s_a0, s_a1, s_a2), ((nh0, cost0), (nh1, cost1), (nh2, cost2))):
        s["nurse_hours_per_day"], s["cost_per_day"] = nh, cost
    say("\n[5] So sanh ba phuong an tren cung bo chi so (mo phong 20 ngay, CV = 1,25)")
    hdr = f"    {'Phuong an':<22}{'Wq':>7}{'Wq_p90':>9}{'P>15':>8}{'P1_Wq':>8}{'rho':>8}{'Gio-DD':>8}"
    say(hdr)
    for s in (s_a0, s_a1, s_a2):
        say(f"    {s['name']:<22}{s['Wq_mean']:>7.2f}{s['Wq_p90']:>9.2f}"
            f"{s['P_wait_gt_target']*100:>7.1f}%{s['Wq_mean_P1']:>8.2f}"
            f"{s['utilization']*100:>7.1f}%{s['nurse_hours_per_day']:>8}")
    comp_header = ["Chỉ số (đơn vị)", "A0 -- AS-IS", "A1 -- Tăng nhân lực", "A2 -- TO-BE"]
    comp_rows = [
        ["Số yêu cầu mô phỏng (lượt)", s_a0["n"], s_a1["n"], s_a2["n"]],
        ["$W_q$ trung bình (phút)", s_a0["Wq_mean"], s_a1["Wq_mean"], s_a2["Wq_mean"]],
        ["$W_q^{90}$ (phút)", s_a0["Wq_p90"], s_a1["Wq_p90"], s_a2["Wq_p90"]],
        ["$W$ trung bình (phút)", s_a0["W_mean"], s_a1["W_mean"], s_a2["W_mean"]],
        ["Tỷ lệ phải chờ (\\%)", s_a0["P_wait_gt_0"] * 100, s_a1["P_wait_gt_0"] * 100,
         s_a2["P_wait_gt_0"] * 100],
        ["$P(W_q>15)$ (\\%)", s_a0["P_wait_gt_target"] * 100,
         s_a1["P_wait_gt_target"] * 100, s_a2["P_wait_gt_target"] * 100],
        ["$W_q$ nhóm P1 (phút)", s_a0["Wq_mean_P1"], s_a1["Wq_mean_P1"], s_a2["Wq_mean_P1"]],
        ["$W_q^{90}$ nhóm P1 (phút)", s_a0["Wq_p90_P1"], s_a1["Wq_p90_P1"], s_a2["Wq_p90_P1"]],
        ["$W_q$ nhóm P3 (phút)", s_a0["Wq_mean_P3"], s_a1["Wq_mean_P3"], s_a2["Wq_mean_P3"]],
        ["Mức sử dụng điều dưỡng (\\%)", s_a0["utilization"] * 100,
         s_a1["utilization"] * 100, s_a2["utilization"] * 100],
        ["Giờ--điều dưỡng/ngày (giờ)", s_a0["nurse_hours_per_day"],
         s_a1["nurse_hours_per_day"], s_a2["nurse_hours_per_day"]],
        ["Chi phí trực/ngày (nghìn VND)", s_a0["cost_per_day"] / 1000,
         s_a1["cost_per_day"] / 1000, s_a2["cost_per_day"] / 1000],
    ]
    write_tex_table(os.path.join(TABLES, "tab_comparison.tex"), comp_header,
                    comp_rows, nd=2,
                    align="p{0.33\\linewidth}rrr")
    write_csv(os.path.join(DATA, "comparison.csv"), comp_header,
              [[c if isinstance(c, str) else round(float(c), 3) for c in row]
               for row in comp_rows])

    # 6. Do nhay va rui ro
    sens_rows = sensitivity([
        ("A0 – AS-IS", SERVERS_ASIS, MEAN_SERVICE_ASIS, False),
        ("A1 – Tăng nhân lực", servers_a1, MEAN_SERVICE_ASIS, False),
        ("A2 – TO-BE", servers_tobe, MEAN_SERVICE_TOBE, True),
    ])
    say("\n[6] Do nhay theo nhu cau")
    for r in sens_rows:
        say(f"    x{r['scale']:.1f}  {r['name']:<22} Wq={r['Wq_mean']:>7.2f}  "
            f"Wq_p90={r['Wq_p90']:>7.2f}  P>15={r['P_gt_15']*100:>5.1f}%  "
            f"rho_peak={r['rho_peak']:.2f}")
    write_tex_table(
        os.path.join(TABLES, "tab_sensitivity.tex"),
        ["Hệ số nhu cầu", "Phương án", "$W_q$ (phút)", "$W_q^{90}$ (phút)",
         "$P(W_q>15)$ (\\%)", "$\\rho$ giờ cao điểm"],
        [[f"$\\times${r['scale']:.1f}", r["name"], r["Wq_mean"], r["Wq_p90"],
          r["P_gt_15"] * 100, r["rho_peak"]] for r in sens_rows],
        align="llrrrr")

    reduced, s_abs = robustness_absence(servers_tobe)
    ms_low, s_low = partial_ai_benefit(servers_tobe)
    say(f"\n[7] Rui ro 1 - thieu 1 dieu duong {reduced}: Wq={s_abs['Wq_mean']:.2f} phut, "
        f"P(Wq>15)={s_abs['P_wait_gt_target']*100:.1f}%")
    say(f"    Rui ro 2 - AI chi giam 15% thoi gian xu ly (E[S]={ms_low:.2f} phut): "
        f"Wq={s_low['Wq_mean']:.2f} phut, P(Wq>15)={s_low['P_wait_gt_target']*100:.1f}%")
    write_tex_table(
        os.path.join(TABLES, "tab_risk.tex"),
        ["Tình huống rủi ro", "$W_q$ (phút)", "$W_q^{90}$ (phút)",
         "$P(W_q>15)$ (\\%)", "$W_q$ nhóm P1 (phút)"],
        [["TO-BE theo thiết kế", s_a2["Wq_mean"], s_a2["Wq_p90"],
          s_a2["P_wait_gt_target"] * 100, s_a2["Wq_mean_P1"]],
         ["Thiếu 1 điều dưỡng ở mọi khung giờ", s_abs["Wq_mean"], s_abs["Wq_p90"],
          s_abs["P_wait_gt_target"] * 100, s_abs["Wq_mean_P1"]],
         [f"AI chỉ giảm 15\\% thời gian xử lý", s_low["Wq_mean"], s_low["Wq_p90"],
          s_low["P_wait_gt_target"] * 100, s_low["Wq_mean_P1"]]],
        align="p{0.40\\linewidth}rrrr")

    # 7. Hinh ve
    plt = setup_mpl()
    chart_arrivals(plt, est_rows)
    chart_wq_by_hour(plt, rows_a0, rows_a1, rows_tobe)
    chart_wq_vs_c(plt)
    chart_sensitivity(plt, sens_rows)
    chart_priority(plt, s_a0, s_a2)
    say(f"\n[8] Da xuat 5 hinh vao {FIGS}")

    # 8. Bang tham so (de dua vao phu luc)
    write_tex_table(
        os.path.join(TABLES, "tab_assumptions.tex"),
        ["Mã", "Tham số", "Giá trị sử dụng", "Căn cứ / cách kiểm tra"],
        [["G1", "Cường độ đến theo giờ $\\lambda_t$",
          "6--12 yc/giờ; 100 yc/ngày",
          "Đặt theo quy mô phòng khám ngoại trú vừa; có thể thay bằng log hệ thống"],
         ["G2", "Cơ cấu mức ưu tiên", "P1 12\\%, P2 58\\%, P3 30\\%",
          "Giả định nhóm; cần đối chiếu bảng phân loại của cơ sở"],
         ["G3", "Thời gian xử lý AS-IS $E[S]$", f"{MEAN_SERVICE_ASIS:.0f} phút, CV = {CV_SERVICE}",
          "Giả định nhóm; kiểm tra bằng bấm giờ mẫu thực tế"],
         ["G4", "Thời gian xử lý TO-BE $E[S]$", f"{MEAN_SERVICE_TOBE:.0f} phút",
          "Giả định giảm 33\\% do có bản tóm tắt; đã kiểm tra tình huống chỉ giảm 15\\%"],
         ["G5", "Lịch trực hiện tại", "2 điều dưỡng, 07:00--19:00",
          "Giả định nhóm theo cấu hình tham chiếu"],
         ["G6", "Chi phí trực", f"{COST_PER_SERVER_HOUR:,} VND/giờ/điều dưỡng".replace(",", " "),
          "Giả định quy ước; chỉ dùng để so sánh tương đối giữa các phương án"],
         ["G7", "Mức cam kết dịch vụ",
          "$W_q \\leq 10$ phut; $P(W_q>15) \\leq 5\\%$; P1 $\\leq 5$ phut",
          "Nhóm tự đặt làm ràng buộc bài toán tối ưu"]],
        align="p{0.05\\linewidth}p{0.22\\linewidth}p{0.26\\linewidth}p{0.34\\linewidth}")

    with open(os.path.join(DATA, "run_log.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    say("\nHoan tat. Bang LaTeX trong tables/, du lieu trong data/.")


if __name__ == "__main__":
    main()
