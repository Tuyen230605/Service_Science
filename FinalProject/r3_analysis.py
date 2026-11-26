"""Role 3 (Muc 7-9): ghep lich ca, danh gia lai A0/A1/A2 theo lich ca, xuat hinh/bang r3_*.

Chay tu thu muc goc repo:
    python -m FinalProject.analysis.r3_analysis

File nay chi DOC tham so va ham mo phong trong run_analysis.py / simulate.py (Role 2),
khong sua file nao cua Role 2. Moi so lieu la ket qua mo phong voi tham so gia dinh.

Dau ra:
    figures/r3_staffing.pdf, r3_shifts.pdf, r3_demand.pdf, r3_disruption.pdf, r3_service.pdf
    tables/r3_comparison.tex
    analysis/data/r3_shift_plan.csv, r3_results.csv, r3_run_log.txt
"""
from __future__ import annotations

import csv
import os

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

import FinalProject.analysis.queueing as q
import FinalProject.analysis.run_analysis as ra
from FinalProject.analysis.simulate import run, summarize

H = ra.HOURS                    # 16 khung mot gio, 06:00-22:00
FT, PT = 8, 4                   # ca 8 tieng va ca ngan 4 tieng
BREAK_OFFSETS = (2, 3, 4, 5)    # nghi 30 phut, khong roi vao gio dau/cuoi ca (BLLD 2019, Dieu 109)
BREAK_SHARE = 0.5               # trong gio nghi, nguoi do chi tinh nua kenh
PT_MAX = 4                      # G: toi da 4 ca ngan moi ngay
PEAK_HOURS = (2, 11, 12)        # 08-09, 17-18, 18-19: ba gio dong nhat
AFTERNOON = range(8, 16)        # 14:00-22:00, dung cho kich ban thieu mot nguoi ca chieu
DAYS_SENS = 30

NAMES = ("A0", "A1", "A2")
COLORS = {"A0": ra.C_BLUE, "A1": ra.C_ORANGE, "A2": ra.C_AQUA}
MARKERS = {"A0": "o", "A1": "s", "A2": "^"}


def vn(x, nd=1):
    """So kieu Viet Nam: 0.25 -> '0,3' (nd=1)."""
    return f"{x:.{nd}f}".replace(".", ",")


# ------------------------------------------------------------ GHEP LICH CA ---
def shift_plan(req, pt_max=PT_MAX, ft_starts=None):
    """Quy hoach nguyen: chon so nguoi cho tung kieu ca (gio bat dau, gio nghi).

    min  tong gio tra luong (8 cho ca dai, 4 cho ca ngan)
    s.t. so kenh co mat o gio t >= req[t]; nguoi dang nghi 30 phut tinh 0,5 kenh;
         so ca ngan <= pt_max; ca dai nghi o gio thu 3-6 cua ca.
    Hai muc tieu phu rat nho: it ca hon, va de phan du roi vao ba gio dong nhat.
    """
    var = []
    starts = range(0, H - FT + 1) if ft_starts is None else ft_starts
    for s in starts:
        for b in BREAK_OFFSETS:
            var.append((FT, s, b))
    if pt_max:
        for s in range(0, H - PT + 1):
            var.append((PT, s, None))
    A = np.zeros((H, len(var)))
    for j, (L, s, b) in enumerate(var):
        A[s:s + L, j] = 1.0
        if b is not None:
            A[s + b, j] -= BREAK_SHARE
    cost = np.array([L + 0.01 for (L, _, _) in var]) - 0.001 * A[list(PEAK_HOURS), :].sum(axis=0)
    cons = [LinearConstraint(A, lb=np.asarray(req, float), ub=np.inf)]
    if pt_max:
        row = np.array([[1.0 if L == PT else 0.0 for (L, _, _) in var]])
        cons.append(LinearConstraint(row, lb=0, ub=pt_max))
    res = milp(c=cost, constraints=cons, integrality=np.ones(len(var)), bounds=Bounds(0, np.inf))
    if not res.success:
        raise RuntimeError("Khong ghep duoc lich ca: " + res.message)
    x = np.round(res.x).astype(int)
    cover = A @ x
    shifts = [{"len": L, "start": s, "brk": b} for (L, s, b), n in zip(var, x) for _ in range(n)]
    shifts.sort(key=lambda d: (d["start"], -d["len"]))
    return {"shifts": shifts, "cover": cover, "paid": int(sum(d["len"] for d in shifts)),
            "n_ft": sum(d["len"] == FT for d in shifts), "n_pt": sum(d["len"] == PT for d in shifts),
            "servers": [int(np.floor(v + 1e-9)) for v in cover]}


def requirement(mean_service):
    rows = ra.optimize_staffing(mean_service)
    return [r["c_star"] for r in rows], sum(not r["feasible"] for r in rows)


# --------------------------------------------------------------- MO PHONG ---
def simulate(servers, service, days, seed, lam_scale=1.0, cv=ra.CV_SERVICE, balk=ra.BALK_QUEUE):
    lam = [l * lam_scale for l in ra.HOURLY_LAMBDA]
    reqs, util = run(ra.sim_config(servers, service, lam=lam, days=days, seed=seed, cv=cv, balk=balk))
    s = summarize(reqs, ra.TARGET_T)
    pk = summarize([r for r in reqs if ra.PEAK[0] * 60 <= r.t_arrival < ra.PEAK[1] * 60], ra.TARGET_T)
    s.update({"peak_Wq": pk["Wq_mean"], "peak_P": pk["P_wait_gt_target"],
              "peak_balk": pk["balk_rate"], "utilization": util["utilization"]})
    return s, reqs


# ----------------------------------------------------------------- HINH VE ---
def _pct_axis(ax):
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: vn(v, 0) if abs(v - round(v)) < 1e-9 else vn(v, 1)))


def _factor_ticks(ax, xs):
    ax.set_xticks(xs, [f"×{vn(x, 1)}" for x in xs])


def chart_staffing(plt, req1, req2, path):
    fig, ax = plt.subplots(figsize=(6.4, 2.15))
    x = np.arange(H)
    ax2 = ax.twinx()
    ax2.bar(x, ra.HOURLY_LAMBDA, 0.72, color="#d9d8d0", zorder=0, label="Lượt xe đến (trục phải)")
    ax2.set_ylabel("Lượt xe/giờ", color=ra.C_MUTED)
    ax2.set_ylim(0, 260)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    for nm, req in (("A0", ra.SERVERS_ASIS), ("A1", req1), ("A2", req2)):
        ax.step(x, req, where="mid", color=COLORS[nm], linewidth=2.0,
                label={"A0": "A0: 6 kênh cố định", "A1": "A1: số kênh theo BT1",
                       "A2": "A2: số kênh theo BT1, $E[S]$ giảm 20%"}[nm])
    ax.set_ylim(0, 9)
    ax.set_ylabel("Số kênh")
    ax.set_xticks(x, [f"{ra.OPEN_HOUR + h:02d}" for h in range(H)])
    ax.set_xlabel("Giờ bắt đầu khung")
    ax.grid(axis="x", visible=False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", ncol=2, fontsize=7.5, bbox_to_anchor=(0.5, 1.22))
    fig.savefig(path)
    plt.close(fig)


def chart_shifts(plt, plan_a1, hours_table, path):
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(6.6, 2.45), gridspec_kw={"width_ratios": [1.45, 1]})
    for i, sh in enumerate(plan_a1["shifts"]):
        y = len(plan_a1["shifts"]) - i
        s0 = ra.OPEN_HOUR + sh["start"]
        col = ra.C_ORANGE
        ax.barh(y, sh["len"], left=s0, height=0.62, color=col,
                alpha=1.0 if sh["len"] == FT else 0.45, edgecolor="white", linewidth=0.5)
        if sh["brk"] is not None:
            ax.barh(y, 0.5, left=s0 + sh["brk"] + 0.25, height=0.62, color="white")
    ax.set_xlim(ra.OPEN_HOUR, ra.OPEN_HOUR + H)
    ax.set_xticks(range(ra.OPEN_HOUR, ra.OPEN_HOUR + H + 1, 2))
    ax.set_yticks([])
    ax.set_xlabel("Giờ trong ngày")
    ax.set_title("(a) Lịch ca của A1: đậm là ca 8 tiếng, nhạt là ca 4 tiếng,\nkhoảng trắng là 30 phút nghỉ", fontsize=8)
    for h in PEAK_HOURS:
        ax.axvspan(ra.OPEN_HOUR + h, ra.OPEN_HOUR + h + 1, color="#f3efe4", zorder=0)
    ax.grid(axis="y", visible=False)

    methods = ["Cần theo BT1", "Hai ca cố định", "Ghép ca tối ưu"]
    wd = 0.26
    xs = np.arange(len(methods))
    for k, nm in enumerate(NAMES):
        vals = [hours_table[nm][m] for m in range(len(methods))]
        pos = xs + (k - 1) * (wd + 0.02)
        bx.bar(pos, vals, wd, color=COLORS[nm], label=nm)
        for p, v in zip(pos, vals):
            bx.annotate(f"{v}", (p, v), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=6.5)
    bx.set_xticks(xs, methods, fontsize=7.5)
    bx.set_ylim(0, 158)
    bx.set_ylabel("Giờ trả lương/ngày")
    bx.set_title("(b) Giờ trả lương theo cách xếp ca", fontsize=8)
    bx.legend(fontsize=7, loc="upper left", ncol=3)
    bx.grid(axis="x", visible=False)
    fig.tight_layout(w_pad=1.2)
    fig.savefig(path)
    plt.close(fig)


def chart_lines(plt, xs, series, ylabels, thresholds, path, xlab):
    fig, axes = plt.subplots(1, len(series), figsize=(6.4, 2.05))
    for ax, ser, ylab, thr in zip(axes, series, ylabels, thresholds):
        for nm in NAMES:
            ax.plot(xs, ser[nm], color=COLORS[nm], marker=MARKERS[nm], markersize=4.5, label=nm)
        if thr is not None:
            ax.axhline(thr, color=ra.C_MUTED, linestyle="--", linewidth=1.1)
            ax.annotate(f"ngưỡng {vn(thr, 0)}%", (xs[0], thr), xytext=(0, 3), textcoords="offset points",
                        fontsize=7, color=ra.C_MUTED)
        _factor_ticks(ax, xs)
        _pct_axis(ax)
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        ax.grid(axis="x", visible=False)
    axes[0].legend(fontsize=7.5, loc="upper left")
    fig.tight_layout(w_pad=1.5)
    fig.savefig(path)
    plt.close(fig)


def chart_disruption(plt, base, cut, path):
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.05))
    xs = np.arange(len(NAMES))
    wd = 0.36
    for ax, key, ylab, thr in zip(axes, ("peak_P", "peak_balk"),
                                  ("Xe chờ quá 5 phút, 17–19 (%)", "Khách bỏ đi, 17–19 (%)"), (5, 1)):
        v0 = [100 * base[n][key] for n in NAMES]
        v1 = [100 * cut[n][key] for n in NAMES]
        ax.bar(xs - wd / 2 - 0.01, v0, wd, color=[COLORS[n] for n in NAMES], alpha=0.45, label="Đủ người")
        ax.bar(xs + wd / 2 + 0.01, v1, wd, color=[COLORS[n] for n in NAMES], label="Thiếu 1 người ca chiều")
        for p, v in list(zip(xs - wd / 2 - 0.01, v0)) + list(zip(xs + wd / 2 + 0.01, v1)):
            ax.annotate(vn(v), (p, v), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=6.5)
        ax.axhline(thr, color=ra.C_MUTED, linestyle="--", linewidth=1.1)
        ax.set_xticks(xs, NAMES)
        ax.set_ylabel(ylab)
        ax.set_ylim(0, max(v1 + v0) * 1.18 + 0.5)
        _pct_axis(ax)
        ax.grid(axis="x", visible=False)
    from matplotlib.patches import Patch
    axes[0].legend([Patch(color="#777", alpha=0.45), Patch(color="#777")],
                   ["Đủ người", "Thiếu 1 người ca chiều"], fontsize=7, loc="upper right")
    fig.tight_layout(w_pad=1.5)
    fig.savefig(path)
    plt.close(fig)


def chart_service(plt, xs, peakP, replan, path):
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(6.4, 2.1))
    for nm in NAMES:
        ax.plot(xs, peakP[nm], color=COLORS[nm], marker=MARKERS[nm], markersize=4.5, label=nm)
    ax.axhline(5, color=ra.C_MUTED, linestyle="--", linewidth=1.1)
    ax.annotate("ngưỡng 5%", (xs[0], 5), xytext=(0, 3), textcoords="offset points", fontsize=7, color=ra.C_MUTED)
    _factor_ticks(ax, xs)
    _pct_axis(ax)
    ax.set_xlabel("$E[S]$ thực so với giả định")
    ax.set_ylabel("Xe chờ quá 5 phút, 17–19 (%)")
    ax.set_title("(a) Giữ nguyên lịch ca", fontsize=8)
    ax.legend(fontsize=7.5, loc="upper left")
    ax.grid(axis="x", visible=False)
    for nm in ("A1", "A2"):
        ys = [r[f"paid_{nm}"] for r in replan]
        bx.plot(xs, ys, color=COLORS[nm], marker=MARKERS[nm], markersize=4.5, label=nm)
        for x, r in zip(xs, replan):
            if r[f"bad_{nm}"]:
                bx.annotate(f"{r[f'bad_{nm}']} giờ không đạt", (x, r[f"paid_{nm}"]), xytext=(0, 6),
                            textcoords="offset points", ha="center", fontsize=6.5, color=COLORS[nm])
    bx.axhline(96, color=COLORS["A0"], linestyle=":", linewidth=1.2)
    bx.annotate("A0 hiện nay: 96 giờ", (xs[-1], 96), xytext=(0, -10), textcoords="offset points",
                ha="right", fontsize=7, color=COLORS["A0"])
    _factor_ticks(bx, xs)
    bx.set_xlabel("$E[S]$ thực so với giả định")
    bx.set_ylabel("Giờ trả lương/ngày")
    bx.set_title("(b) Lập lại lịch theo $E[S]$ thực", fontsize=8)
    bx.set_ylim(60, 145)
    bx.legend(fontsize=7.5, loc="lower right")
    bx.grid(axis="x", visible=False)
    fig.tight_layout(w_pad=1.5)
    fig.savefig(path)
    plt.close(fig)


# -------------------------------------------------------------------- BANG ---
def write_comparison(path, comp, paid, tech):
    def money(n):
        return (paid[n] * ra.COST_PER_SERVER_HOUR + tech[n]) / 1e6
    rows = [
        ("Giờ trả lương/ngày (giờ)", "--", [f"{paid[n]}" for n in NAMES]),
        ("Chi phí nhân lực và công nghệ (triệu đồng/ngày)", "--", [vn(money(n)) for n in NAMES]),
        ("Thời gian chờ trung bình, cả ngày (phút)", "$\\le 2$", [vn(comp[n]["Wq_mean"]) for n in NAMES]),
        ("Xe chờ quá 5 phút, giờ 17--19 (\\%)", "$\\le 5$", [vn(100 * comp[n]["peak_P"]) for n in NAMES]),
        ("Khách bỏ đi, giờ 17--19 (\\%)", "$\\le 1$", [vn(100 * comp[n]["peak_balk"]) for n in NAMES]),
        ("Xe phải chờ, cả ngày (\\%)", "--", [vn(100 * comp[n]["P_wait_gt_0"]) for n in NAMES]),
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("% Sinh tu analysis/r3_analysis.py; khong sua tay.\n")
        f.write("\\begin{tabular}{@{}lcccc@{}}\n\\toprule\n")
        f.write("Chỉ số & Ngưỡng & A0 & A1 & A2 \\\\\n\\midrule\n")
        for lab, thr, vals in rows:
            f.write(f"{lab} & {thr} & " + " & ".join(v.replace(",", "{,}") for v in vals) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")


def write_sens_other(path, other):
    rows = [("Cơ sở: CV 0,8; ngưỡng 20 xe", ("CV", 0.8)), ("CV của $S$ = 0,5", ("CV", 0.5)),
            ("CV của $S$ = 1,2", ("CV", 1.2)), ("Ngưỡng bỏ đi = 10 xe", ("nguong", 10)),
            ("Ngưỡng bỏ đi = 30 xe", ("nguong", 30))]
    with open(path, "w", encoding="utf-8") as f:
        f.write("% Sinh tu analysis/r3_analysis.py; khong sua tay.\n")
        f.write("\\begin{tabular}{@{}lcccc@{}}\n\\toprule\n")
        f.write(" & \\multicolumn{2}{c}{A0} & \\multicolumn{2}{c}{A1} \\\\\n")
        f.write("\\cmidrule(lr){2-3}\\cmidrule(l){4-5}\n")
        f.write("Giả định & Chờ quá 5 phút (\\%) & Bỏ đi (\\%) & Chờ quá 5 phút (\\%) & Bỏ đi (\\%) \\\\\n\\midrule\n")
        for lab, key in rows:
            vals = []
            for nm in ("A0", "A1"):
                s = other[(key[0], key[1], nm)]
                vals += [vn(100 * s["peak_P"]), vn(100 * s["peak_balk"])]
            f.write(lab + " & " + " & ".join(v.replace(",", "{,}") for v in vals) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")


# -------------------------------------------------------------------- MAIN ---
def main():
    log = []

    def say(msg=""):
        print(msg)
        log.append(msg)

    svc = {"A0": ra.SERVICE_ASIS, "A1": ra.SERVICE_ASIS, "A2": ra.SERVICE_TOBE}
    req1, _ = requirement(ra.MEAN_SERVICE_ASIS)
    req2, _ = requirement(ra.MEAN_SERVICE_TOBE)
    say("[1] So kenh can theo gio (BT1)")
    say(f"    A1 {req1} = {sum(req1)} kenh-gio; A2 {req2} = {sum(req2)} kenh-gio")

    # --- ghep ca: toi uu va quy tac thu cong (hai ca co dinh 06-14, 14-22, chi ca 8 tieng)
    plans, manual = {}, {}
    for nm, req in (("A0", ra.SERVERS_ASIS), ("A1", req1), ("A2", req2)):
        plans[nm] = shift_plan(req)
        manual[nm] = shift_plan(req, pt_max=0, ft_starts=[0, 8])
    say("\n[2] Ghep ca (ca 8 tieng co 30 phut nghi tinh luong; toi da %d ca 4 tieng)" % PT_MAX)
    for nm in NAMES:
        p, m = plans[nm], manual[nm]
        say(f"    {nm}: toi uu {p['paid']} gio ({p['n_ft']} ca 8h + {p['n_pt']} ca 4h); "
            f"hai ca co dinh {m['paid']} gio; kenh co mat {p['servers']}")
    hours_table = {"A0": [96, manual["A0"]["paid"], plans["A0"]["paid"]],
                   "A1": [sum(req1), manual["A1"]["paid"], plans["A1"]["paid"]],
                   "A2": [sum(req2), manual["A2"]["paid"], plans["A2"]["paid"]]}

    # Lich dung de danh gia: A0 giu cach lam hien nay (2 ca x 6 nguoi = 96 gio);
    # A1, A2 dung lich ca toi uu.
    servers = {"A0": ra.SERVERS_ASIS, "A1": plans["A1"]["servers"], "A2": plans["A2"]["servers"]}
    paid = {"A0": 96, "A1": plans["A1"]["paid"], "A2": plans["A2"]["paid"]}
    tech = {"A0": 0, "A1": 0, "A2": ra.TECH_COST_DAY}

    with open(os.path.join(ra.DATA, "r3_shift_plan.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["phuong_an", "loai_ca_gio", "bat_dau", "ket_thuc", "gio_nghi_30_phut"])
        for nm in ("A1", "A2"):
            for sh in plans[nm]["shifts"]:
                s0 = ra.OPEN_HOUR + sh["start"]
                brk = "" if sh["brk"] is None else f"{s0 + sh['brk']:02d}:15-{s0 + sh['brk']:02d}:45"
                w.writerow([nm, sh["len"], f"{s0:02d}:00", f"{s0 + sh['len']:02d}:00", brk])

    # --- so sanh chinh: 20 ngay, cung dong xe den
    comp, reqs = {}, {}
    for nm in NAMES:
        comp[nm], reqs[nm] = simulate(servers[nm], svc[nm], ra.DAYS, ra.SEED)
    say("\n[3] So sanh 20 ngay (cung seed)")
    for nm in NAMES:
        s = comp[nm]
        say(f"    {nm}: gio tra luong {paid[nm]}, Wq {s['Wq_mean']:.3f}, P>5 {100*s['P_wait_gt_target']:.2f}%, "
            f"bo di {100*s['balk_rate']:.2f}% | 17-19: Wq {s['peak_Wq']:.3f}, P>5 {100*s['peak_P']:.2f}%, "
            f"bo di {100*s['peak_balk']:.2f}% | phai cho {100*s['P_wait_gt_0']:.2f}%, su dung {100*s['utilization']:.1f}%")
    for nm in NAMES:
        say(f"    {nm}: chi phi {(paid[nm]*ra.COST_PER_SERVER_HOUR + tech[nm])/1e6:.3f} trieu dong/ngay")

    # --- insight tu du lieu A0: muc do don vao ba gio dong
    r0 = reqs["A0"]
    hours_of = [min(int(r.t_arrival // 60), H - 1) for r in r0]
    in_peak = np.array([h in PEAK_HOURS for h in hours_of])
    balked = np.array([r.balked for r in r0])
    wq = np.array([0.0 if r.balked else r.wq for r in r0])
    long_wait = (~balked) & (wq > ra.TARGET_T)
    car = np.array([r.priority == 1 for r in r0])
    svc_min = np.array([0.0 if r.balked else r.service for r in r0])
    say("\n[4] Quan sat tu du lieu mo phong A0")
    say(f"    Ba gio dong (08-09, 17-19): {100*in_peak.mean():.1f}% luot xe; "
        f"{100*long_wait[in_peak].sum()/max(long_wait.sum(),1):.1f}% so lan cho qua 5 phut; "
        f"{100*balked[in_peak].sum()/max(balked.sum(),1):.1f}% so luot bo di; "
        f"{100*wq[in_peak].sum()/wq.sum():.1f}% tong phut cho")
    say(f"    O to: {100*car.mean():.1f}% luot xe, {100*svc_min[car].sum()/svc_min.sum():.1f}% tong phut phuc vu")
    mu_a, mu_t = 60 / ra.MEAN_SERVICE_ASIS, 60 / ra.MEAN_SERVICE_TOBE
    lam_pk = max(ra.HOURLY_LAMBDA)
    say(f"    M/M/c gio 18-19: 6 kenh Wq {q.wq_min(lam_pk, mu_a, 6):.2f} phut (rho {q.utilization(lam_pk, mu_a, 6):.2f}); "
        f"7 kenh Wq {q.wq_min(lam_pk, mu_a, 7):.2f} phut (rho {q.utilization(lam_pk, mu_a, 7):.2f})")

    results = []
    for nm in NAMES:
        results.append(["so_sanh", nm, 1.0, paid[nm], comp[nm]["Wq_mean"], comp[nm]["P_wait_gt_target"],
                        comp[nm]["balk_rate"], comp[nm]["peak_P"], comp[nm]["peak_balk"]])

    # --- kich ban luong xe thay doi (giu nguyen lich ca)
    scales = [0.8, 1.0, 1.2, 1.4]
    dem = {nm: [] for nm in NAMES}
    say("\n[5] Luong xe thay doi (30 ngay/cau hinh, giu nguyen lich)")
    for sc in scales:
        for nm in NAMES:
            s, _ = simulate(servers[nm], svc[nm], DAYS_SENS, ra.SEED + 7, lam_scale=sc)
            dem[nm].append(s)
            results.append(["luong_xe", nm, sc, paid[nm], s["Wq_mean"], s["P_wait_gt_target"],
                            s["balk_rate"], s["peak_P"], s["peak_balk"]])
            say(f"    x{sc}: {nm} Wq {s['Wq_mean']:.2f}, 17-19 P>5 {100*s['peak_P']:.2f}%, "
                f"bo di {100*s['peak_balk']:.2f}%, ca ngay bo di {100*s['balk_rate']:.2f}%")

    # --- su co van hanh: thieu mot nguoi ca chieu (14-22)
    base, cut = {}, {}
    say("\n[6] Su co: thieu 1 nguoi ca chieu 14:00-22:00 (30 ngay)")
    for nm in NAMES:
        sv_cut = [c - 1 if h in AFTERNOON else c for h, c in enumerate(servers[nm])]
        base[nm], _ = simulate(servers[nm], svc[nm], DAYS_SENS, ra.SEED + 11)
        cut[nm], _ = simulate(sv_cut, svc[nm], DAYS_SENS, ra.SEED + 11)
        for lab, s in (("du_nguoi", base[nm]), ("thieu_1_nguoi_ca_chieu", cut[nm])):
            results.append([lab, nm, 1.0, paid[nm], s["Wq_mean"], s["P_wait_gt_target"],
                            s["balk_rate"], s["peak_P"], s["peak_balk"]])
        say(f"    {nm}: du nguoi 17-19 P>5 {100*base[nm]['peak_P']:.2f}%, bo di {100*base[nm]['peak_balk']:.2f}% | "
            f"thieu 1 nguoi P>5 {100*cut[nm]['peak_P']:.2f}%, bo di {100*cut[nm]['peak_balk']:.2f}%")
    a2_10 = {k: v * 0.9 for k, v in ra.SERVICE_ASIS.items()}
    s10, _ = simulate(servers["A2"], a2_10, DAYS_SENS, ra.SEED + 11)
    results.append(["A2_chi_giam_10pct", "A2", 1.0, paid["A2"], s10["Wq_mean"], s10["P_wait_gt_target"],
                    s10["balk_rate"], s10["peak_P"], s10["peak_balk"]])
    say(f"    A2 neu tra truoc chi giam 10% S: ca ngay P>5 {100*s10['P_wait_gt_target']:.2f}%, "
        f"bo di {100*s10['balk_rate']:.2f}% | 17-19 P>5 {100*s10['peak_P']:.2f}%, bo di {100*s10['peak_balk']:.2f}%")

    # --- do nhay theo E[S]: giu lich ca, va lap lai lich (BT1 + ghep ca)
    factors = list(ra.SERVICE_FACTORS)
    peakP = {nm: [] for nm in NAMES}
    replan = []
    say("\n[7] Do nhay theo E[S] that (30 ngay)")
    for f in factors:
        for nm in NAMES:
            s, _ = simulate(servers[nm], ra.scale_service(svc[nm], f), DAYS_SENS, ra.SEED + 17)
            peakP[nm].append(100 * s["peak_P"])
            results.append([f"E[S]x{f}", nm, f, paid[nm], s["Wq_mean"], s["P_wait_gt_target"],
                            s["balk_rate"], s["peak_P"], s["peak_balk"]])
        r1, bad1 = requirement(ra.mix_mean(ra.scale_service(ra.SERVICE_ASIS, f)))
        r2, bad2 = requirement(ra.mix_mean(ra.scale_service(ra.SERVICE_TOBE, f)))
        replan.append({"factor": f, "paid_A1": shift_plan(r1)["paid"], "bad_A1": bad1,
                       "paid_A2": shift_plan(r2)["paid"], "bad_A2": bad2})
        say(f"    x{f}: 17-19 P>5 A0 {peakP['A0'][-1]:.2f}% A1 {peakP['A1'][-1]:.2f}% A2 {peakP['A2'][-1]:.2f}% | "
            f"lap lai: A1 {replan[-1]['paid_A1']} gio ({bad1} gio khong dat), A2 {replan[-1]['paid_A2']} gio ({bad2})")

    # --- CV va nguong bo di (A0, A1 theo lich ca)
    say("\n[8] CV cua S va nguong bo di (A0, A1; 30 ngay)")
    other = {}
    for label, val, balk, cv in [("CV", c, ra.BALK_QUEUE, c) for c in (0.5, 0.8, 1.0, 1.2)] + \
                                [("nguong", b, b, ra.CV_SERVICE) for b in (10, 20, 30)]:
        line = []
        for nm in ("A0", "A1"):
            s, _ = simulate(servers[nm], svc[nm], DAYS_SENS, ra.SEED + 19, cv=cv, balk=balk)
            other[(label, val, nm)] = s
            line.append(f"{nm} P>5 {100*s['P_wait_gt_target']:.2f}% bo di {100*s['balk_rate']:.2f}% "
                        f"(17-19: {100*s['peak_P']:.2f}%, {100*s['peak_balk']:.2f}%)")
            results.append([f"{label}={val}", nm, 1.0, paid[nm], s["Wq_mean"], s["P_wait_gt_target"],
                            s["balk_rate"], s["peak_P"], s["peak_balk"]])
        say(f"    {label}={val}: " + " | ".join(line))

    with open(os.path.join(ra.DATA, "r3_results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kich_ban", "phuong_an", "he_so", "gio_tra_luong", "Wq_tb_phut", "P_cho_qua_5",
                    "bo_di", "P_cho_qua_5_gio_17_19", "bo_di_gio_17_19"])
        for row in results:
            w.writerow([f"{v:.5f}" if isinstance(v, float) else v for v in row])

    # --- xuat bang va hinh
    write_comparison(os.path.join(ra.TABLES, "r3_comparison.tex"), comp, paid, tech)
    plt = ra.setup_mpl()
    chart_staffing(plt, req1, req2, os.path.join(ra.FIGS, "r3_staffing.pdf"))
    chart_shifts(plt, plans["A1"], hours_table, os.path.join(ra.FIGS, "r3_shifts.pdf"))
    chart_lines(plt, scales,
                [{nm: [100 * s["peak_P"] for s in dem[nm]] for nm in NAMES},
                 {nm: [100 * s["peak_balk"] for s in dem[nm]] for nm in NAMES}],
                ["Xe chờ quá 5 phút, 17–19 (%)", "Khách bỏ đi, 17–19 (%)"], [5, 1],
                os.path.join(ra.FIGS, "r3_demand.pdf"), "Lượt xe so với hiện tại")
    chart_disruption(plt, base, cut, os.path.join(ra.FIGS, "r3_disruption.pdf"))
    chart_service(plt, factors, peakP, replan, os.path.join(ra.FIGS, "r3_service.pdf"))
    say("\n[9] Da xuat 5 hinh r3_*.pdf, bang tables/r3_comparison.tex, du lieu data/r3_*.csv")

    with open(os.path.join(ra.DATA, "r3_run_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
