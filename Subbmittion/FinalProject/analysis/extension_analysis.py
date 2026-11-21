"""Phan mo rong: dinh vi roi rac (chon 2/5 diem mo cua hang), kich ban chien luoc
A/B/C, trai nghiem khach hang theo the he va hoc may du bao nhu cau.

Chay:  python3 extension_analysis.py      (sau run_analysis.py; KHONG ghi de dau ra cu)
Dau ra: data/ext_*.csv, data/ext_run_log.txt, tables/tab_ext_*.tex,
        ../figures/r2_location.png, r2_forecast.png, r3_scenarios.png

Nguon so lieu: dan so quan theo Tong dieu tra 2019 (citypopulation.de, dan theo
TCTK); 5,6 trieu xe may / 8,05 trieu dan; muc ban 110.000 m3 xang/thang va 453
cua hang (So Cong Thuong Ha Noi); gia xang E10 RON95-III ky 5/11/2026 (-2.075
d/L) va 12/11/2026 (-1.310 d/L); Tet Binh Ngo 17/02/2026; dot cang thang nguon
cung dau thang 3/2026. Cac tham so con lai la GIA DINH, ghi don vi ben canh.
"""

from __future__ import annotations

import csv
import datetime as dt
import itertools
import math
import os
from math import isfinite

import numpy as np

import queueing as q
import run_analysis as ra
from simulate import run, summarize

TABLES, DATA, FIGS = ra.TABLES, ra.DATA, ra.FIGS
SEED = 20260301
LOG: list[str] = []


def say(s=""):
    print(s)
    LOG.append(s)


def f2(x, nd=2):
    if isinstance(x, str):
        return x
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}".replace(",", "\\,")
    if not isfinite(x):
        return "--"
    return f"{x:,.{nd}f}".replace(",", "\\,")


def hh(*lines):
    """O tieu de nhieu dong, in dam."""
    body = "\\\\".join("\\textbf{" + x + "}" for x in lines)
    return "\\begin{tabular}[b]{@{}c@{}}" + body + "\\end{tabular}"


def write_table(name, header, rows, align, nd=2):
    with open(os.path.join(TABLES, name), "w") as f:
        f.write("\\begin{tabular}{" + align + "}\n\\toprule\n")
        f.write(" & ".join(header) + " \\\\\n\\midrule\n")
        for r in rows:
            if r == "MID":
                f.write("\\midrule\n")
                continue
            f.write(" & ".join(f2(v, nd) for v in r) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")


def write_csv(name, header, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows([r for r in rows if r != "MID"])


def plain(s):
    return s.replace("\\", "").replace("$", "")


# ============================================================================
# BAI TOAN 2 - DINH VI ROI RAC: CHON k = 2 TRONG 5 DIEM MO CUA HANG XANG MOI
# ============================================================================
# (ten quan cu, dan so 2019 (nguoi), toa do xap xi trung tam (vi do, kinh do))
ZONES = [("Cầu Giấy", 292_536, (21.0333, 105.7940)),
         ("Đống Đa", 371_606, (21.0170, 105.8260)),
         ("Thanh Xuân", 293_524, (20.9935, 105.8100)),
         ("Hà Đông", 397_854, (20.9640, 105.7700)),
         ("Nam Từ Liêm", 264_246, (21.0140, 105.7600)),
         ("Hai Bà Trưng", 303_586, (21.0060, 105.8570)),
         ("Hoàng Mai", 506_347, (20.9760, 105.8620)),
         ("Long Biên", 322_549, (21.0450, 105.8920))]
SITES = [("J1 Cầu Giấy", (21.0300, 105.7820), 120),   # (ten, toa do, f_j trieu d/thang:
         ("J2 Đống Đa", (21.0160, 105.8100), 150),    #  thue dat, khau hao, quan ly)
         ("J3 Hà Đông", (20.9800, 105.7900), 80),
         ("J4 Hoàng Mai", (20.9850, 105.8420), 95),
         ("J5 Long Biên", (21.0430, 105.8750), 75)]
MOTO_PER_CAPITA = 5.6e6 / 8.053663e6   # R: 5,6 trieu xe may / dan so 2019 ~ 0,70 xe/nguoi
VISITS_PER_VEHICLE_DAY = 0.2           # E: do xang 5 ngay/lan (2,5 L, ~0,5 L/ngay)
CAPTURE = 0.02                         # E: thi phan mot cua hang moi gianh duoc trong vung phu
CIRCUITY = 1.35                        # he so duong vong so voi duong chim bay
SPEED_KMH = 20.0                       # E: toc do xe may gio cao diem noi thanh
ACCESS_MIN = 2.0                       # phut vao/ra cua hang
K_OPEN = 2
R_COVER = 15.0                         # phut
SITE_SERVERS = ra.C_MAX                # 8 voi bom co nhan vien
LITRES_PER_VISIT_AVG = ra.LITRES_PER_STORE_DAY / ra.VISITS_DAY   # ~3,24 L/luot
# Chi phi nhan vien bien doi theo luot: gio-nguoi/luot = E[S]/60/muc su dung 0,7
STAFF_COST_PER_VISIT = ra.COST_PER_SERVER_HOUR * ra.MEAN_SERVICE_ASIS / 60 / 0.7
CONTRIB_PER_VISIT = LITRES_PER_VISIT_AVG * ra.MARGIN_PER_LITRE - STAFF_COST_PER_VISIT


def haversine_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    d = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(d))


TRAVEL = np.array([[haversine_km(z[2], s[1]) * CIRCUITY / SPEED_KMH * 60 + ACCESS_MIN
                    for s in SITES] for z in ZONES])
DEMAND = np.array([z[1] * MOTO_PER_CAPITA * VISITS_PER_VEHICLE_DAY * CAPTURE for z in ZONES])
FIXED = np.array([s[2] for s in SITES], dtype=float)


def site_capacity(c=SITE_SERVERS, es=ra.MEAN_SERVICE_ASIS):
    """Q_j (luot/ngay): lambda gio cao diem lon nhat thoa rho<=0.85, Wq<=2, P(Wq>5)<=5%,
    quy ra ca ngay bang ty trong gio cao diem (9%)."""
    mu = 60.0 / es
    best = 0
    for lam in range(1, 2000):
        m = q.metrics(lam, mu, c, ra.TARGET_T)
        if m["rho"] > 0.85 or not ra.feasible(m):
            break
        best = lam
    return best / max(ra.HOURLY_SHARE), best


def solve_location(demand, R, cap, k=K_OPEN):
    """Liet ke C(5,k) to hop; voi moi to hop liet ke day du phan bo don nguon.
    Muc tieu tu vung: max nhu cau phuc vu -> min thoi gian di lai -> min chi phi."""
    nI, nJ = TRAVEL.shape
    a = (TRAVEL <= R).astype(int)
    out = []
    for combo in itertools.combinations(range(nJ), k):
        covered = [i for i in range(nI) if any(a[i, j] for j in combo)]
        options = [[j for j in combo if a[i, j]] + [-1] for i in covered]
        best = None
        for assign in itertools.product(*options):
            load = {j: 0.0 for j in combo}
            served = wtime = 0.0
            for i, j in zip(covered, assign):
                if j >= 0:
                    load[j] += demand[i]
                    served += demand[i]
                    wtime += demand[i] * TRAVEL[i, j]
            if any(load[j] > cap + 1e-9 for j in combo):
                continue
            key = (round(served, 6), -wtime)
            if best is None or key > best[0]:
                best = (key, assign, dict(load), served, wtime)
        _, assign, load, served, wtime = best
        mu = 60.0 / ra.MEAN_SERVICE_ASIS
        peak = {j: load[j] * max(ra.HOURLY_SHARE) for j in combo}
        mets = {j: (q.metrics(peak[j], mu, SITE_SERVERS, ra.TARGET_T) if peak[j] > 0
                    else {"rho": 0.0, "Wq": 0.0}) for j in combo}
        margin = served * CONTRIB_PER_VISIT * 30 / 1e6  # tr.d/thang, lai gop tru luong NV
        fixed = FIXED[list(combo)].sum()
        out.append({
            "combo": combo, "name": " + ".join(SITES[j][0].split()[0] for j in combo),
            "cover_raw": demand[covered].sum(), "served": served,
            "served_pct": 100 * served / demand.sum(),
            "avg_time": wtime / served if served else float("nan"),
            "max_rho": max(mets[j]["rho"] for j in combo),
            "max_wq": max(mets[j]["Wq"] for j in combo),
            "fixed": fixed, "margin": margin, "profit": margin - fixed,
            "assign": {ZONES[i][0]: (SITES[j][0] if j >= 0 else "--")
                       for i, j in zip(covered, assign)},
            "load": {SITES[j][0]: round(load[j]) for j in combo}})
    out.sort(key=lambda r: (-round(r["served"], 6), r["avg_time"], r["fixed"]))
    return out


def location_block():
    cap, lam_peak = site_capacity()
    say(f"\n[L1] Dinh vi: chon {K_OPEN}/5 diem, R = {R_COVER:.0f} phut")
    say(f"     Nhu cau/vung = dan so x {MOTO_PER_CAPITA:.3f} xe/nguoi x "
        f"{VISITS_PER_VEHICLE_DAY} luot/xe/ngay x {CAPTURE:.0%} -> tong {DEMAND.sum():,.0f} luot/ngay")
    say(f"     Q_j = {cap:,.0f} luot/ngay (lambda cao diem {lam_peak} xe/gio, c = {SITE_SERVERS})")
    say(f"     Dong gop/luot = {LITRES_PER_VISIT_AVG:.2f} L x {ra.MARGIN_PER_LITRE} d - "
        f"{STAFF_COST_PER_VISIT:,.0f} d luong = {CONTRIB_PER_VISIT:,.0f} d")
    a = (TRAVEL <= R_COVER).astype(int)
    rows = []
    for i, z in enumerate(ZONES):
        rows.append([z[0], z[1], round(DEMAND[i])]
                    + [f"{TRAVEL[i, j]:.1f}" + ("$^{\\bullet}$" if a[i, j] else "")
                       for j in range(5)])
    rows.append(["Phủ được (lượt/ngày)", int(sum(z[1] for z in ZONES)), round(DEMAND.sum())]
                + [round((DEMAND * a[:, j]).sum()) for j in range(5)])
    write_table("tab_ext_cover_matrix.tex",
                [hh("Vùng nhu cầu $i$"), hh("Dân số", "2019 (người)"), hh("$h_i$", "(lượt/ngày)")]
                + [hh(s[0].split()[0], "(phút)") for s in SITES], rows, "lrrrrrrr")
    for i, z in enumerate(ZONES):
        say(f"     {z[0]:<13} h={DEMAND[i]:7.1f}  t=" + " ".join(f"{t:5.1f}" for t in TRAVEL[i]))

    res = solve_location(DEMAND, R_COVER, cap)
    for r in res:
        say(f"     {r['name']:<8} phu={r['cover_raw']:7.1f} phucvu={r['served']:7.1f} "
            f"({r['served_pct']:5.1f}%) t={r['avg_time']:5.2f} rho={r['max_rho']:.2f} "
            f"Wq={r['max_wq']:.2f} F={r['fixed']:.0f} LN={r['profit']:7.1f}tr {r['load']}")
    best = res[0]
    by_profit = max(res, key=lambda r: r["profit"])
    say(f"     => Chon {best['name']}; phan bo {best['assign']}; LN cao nhat: {by_profit['name']}")
    trows = [[r["name"], round(r["cover_raw"]), round(r["served"]), r["served_pct"],
              r["avg_time"], r["max_rho"], r["max_wq"], int(r["fixed"]), r["margin"],
              r["profit"]] for r in res]
    write_table("tab_ext_location.tex",
                [hh("Tổ hợp"), hh("Phủ trong $R$", "(lượt/ngày)"), hh("Phục vụ", "(lượt/ngày)"),
                 hh("Phục vụ", "(\\%)"), hh("$\\bar t$", "(phút)"), hh("$\\rho_{\\max}$"),
                 hh("$W_{q,\\max}$", "(phút)"), hh("$F$", "(tr.đ/tháng)"),
                 hh("Đóng góp", "(tr.đ/tháng)"), hh("Lợi nhuận", "(tr.đ/tháng)")],
                trows, "lrrrrrrrrr", nd=2)
    write_csv("ext_location.csv", ["combo", "covered", "served", "served_pct", "avg_time_min",
                                   "max_rho", "max_wq_min", "fixed_mVND", "margin_mVND",
                                   "profit_mVND"], trows)

    sens = []
    for label, R, scale, c in [("$R$ = 12 phút", 12, 1.0, SITE_SERVERS),
                               ("$R$ = 15 phút (cơ sở)", 15, 1.0, SITE_SERVERS),
                               ("$R$ = 20 phút", 20, 1.0, SITE_SERVERS),
                               ("KB-A: nhu cầu $\\times$0.8", 15, 0.8, SITE_SERVERS),
                               ("KB-B: nhu cầu $\\times$1.2", 15, 1.2, SITE_SERVERS),
                               ("Cửa hàng 6 vòi ($c=6$)", 15, 1.0, 6)]:
        capx, _ = site_capacity(c=c)
        rx = solve_location(DEMAND * scale, R, capx)
        b = rx[0]
        same = next(r for r in rx if r["combo"] == best["combo"])
        bp = max(rx, key=lambda r: r["profit"])
        sens.append([label, capx, b["name"], b["served_pct"], same["served_pct"],
                     bp["name"], bp["profit"], same["profit"]])
        say(f"     [do nhay] {plain(label):<26} Q={capx:7.1f} chon={b['name']:<8} "
            f"{b['served_pct']:5.1f}% (co so {same['served_pct']:5.1f}%) LNmax={bp['name']} "
            f"LN co so={same['profit']:.1f}")
    write_table("tab_ext_location_sens.tex",
                [hh("Tình huống"), hh("$Q_j$", "(lượt/ngày)"), hh("Tối ưu", "phục vụ"),
                 hh("Phục vụ", "(\\%)"), hh(best["name"], "phục vụ (\\%)"),
                 hh("Tối ưu", "lợi nhuận"), hh("Lợi nhuận", "tối ưu (tr.đ)"),
                 hh(best["name"], "lợi nhuận (tr.đ)")],
                sens, "lrlrrlrr", nd=1)
    return cap, res, best


# ============================================================================
# KHACH HANG: PHAN KHUC THEO THE HE VA MAT KHACH DO CHO
# ============================================================================
SEGMENTS = [  # (ten, ty trong, theta (phut kien nhan), c_g = xac suat chuyen han cua hang)
    ("Gen Z (18--29)", 0.30, 8.0, 0.08),
    ("Gen Y (30--44)", 0.35, 10.0, 0.06),
    ("Gen X (45--60)", 0.25, 12.0, 0.04),
    ("60+", 0.10, 15.0, 0.03),
]
PATIENCE_SHAPE = 2.0   # Weibull k: cho ngan gan nhu khong gay mat khach, cho dai tang nhanh
# CLV (dong) = lai gop 3 nam cua mot khach quen: xe may 73 luot/nam x 2,5 L; o to 52 luot/nam x 30 L
CLV = {1: round(52 * ra.LITRES_PER_VISIT[1] * ra.MARGIN_PER_LITRE * 3, -4),
       2: round(365 * VISITS_PER_VEHICLE_DAY * ra.LITRES_PER_VISIT[2] * ra.MARGIN_PER_LITRE * 3, -4)}
ONCALL_PREMIUM = 1.5              # he so luong gio nhan vien du phong


def cx_metrics(reqs, seed, clv_scale=1.0):
    """Khach da vao hang: p_g(w) = 1 - exp(-(w/theta_g)^2) la xac suat khong hai long den
    muc lan sau bo di; khach thay hang qua dai va bo di (balk): p = 1.
    Ton that moi luot = p x [lai gop luot do + c_g x CLV]."""
    rng = np.random.default_rng(seed)
    seg = rng.choice(len(SEGMENTS), size=len(reqs), p=[s[1] for s in SEGMENTS])
    balked = np.array([r.balked for r in reqs])
    wq = np.array([0.0 if r.balked else r.wq for r in reqs])
    cls = np.array([r.priority for r in reqs])
    theta = np.array([SEGMENTS[g][2] for g in seg])
    churn = np.array([SEGMENTS[g][3] for g in seg])
    p = np.where(balked, 1.0, 1 - np.exp(-(wq / theta) ** PATIENCE_SHAPE))  # balk: mat chac chan
    margin = np.where(cls == 1, ra.LITRES_PER_VISIT[1], ra.LITRES_PER_VISIT[2]) * ra.MARGIN_PER_LITRE
    clv = np.where(cls == 1, CLV[1], CLV[2]) * clv_scale
    out = {"loss_rate": float(p.mean()),
           "lost_margin": float((p * margin).sum()),
           "lost_clv": float((p * churn * clv).sum())}
    for g, s in enumerate(SEGMENTS):
        out[s[0]] = float(p[seg == g].mean())
    return out


# ============================================================================
# BAI TOAN 3 - KICH BAN A/B/C VA LUA CHON CHIEN LUOC
# ============================================================================
SCEN = [  # ten, he so nhu cau, he so thoi gian phuc vu
    ("KB-A Nhu cầu thấp", 0.80, 1.00),   # chuyen sang xe dien, vung phat thai thap
    ("KB-B Nhu cầu tăng", 1.20, 1.00),   # doi thu lan can dong cua, xe dang ky moi
    ("KB-C Gián đoạn", 1.35, 1.15),      # cang thang nguon cung: don khach + ban gioi han
]
SCEN_PROB = [0.30, 0.45, 0.25]
STRATS = ["A0", "CL-A", "CL-B tĩnh", "CL-B thích ứng"]
PLAN_A1 = [r["c_star"] for r in ra.optimize_staffing(ra.MEAN_SERVICE_ASIS)]
PLAN_A2 = [r["c_star"] for r in ra.optimize_staffing(ra.MEAN_SERVICE_TOBE)]


def strategy_plan(st, scale, s_mult):
    lam = [l * scale for l in ra.HOURLY_LAMBDA]
    svc_asis = {k: v * s_mult for k, v in ra.SERVICE_ASIS.items()}
    svc_tobe = {k: v * s_mult for k, v in ra.SERVICE_TOBE.items()}
    if st == "A0":
        return ra.SERVERS_ASIS, svc_asis, sum(ra.SERVERS_ASIS), 0, False
    if st == "CL-A":
        return PLAN_A1, svc_asis, sum(PLAN_A1), 0, False
    if st == "CL-B tĩnh":
        return PLAN_A2, svc_tobe, sum(PLAN_A2), 0, True
    plan = [r["c_star"] for r in ra.optimize_staffing(ra.mix_mean(svc_tobe), lam=lam)]
    reg = sum(min(c, b) for c, b in zip(plan, PLAN_A2))
    extra = sum(max(0, c - b) for c, b in zip(plan, PLAN_A2))
    return plan, svc_tobe, reg, extra, True


def scenario_block():
    say("\n[S1] Kich ban chien luoc (30 ngay/o, cung seed trong mot kich ban)")
    say(f"     Lich A1 = {PLAN_A1} ({sum(PLAN_A1)}); A2 = {PLAN_A2} ({sum(PLAN_A2)})")
    res = {}
    for si, (sname, scale, smult) in enumerate(SCEN):
        for st in STRATS:
            plan, svc, reg, extra, tool = strategy_plan(st, scale, smult)
            lam = [l * scale for l in ra.HOURLY_LAMBDA]
            reqs, util = run(ra.sim_config(plan, svc, lam=lam, days=30, seed=SEED + 100 * si))
            s = summarize(reqs, ra.TARGET_T)
            cx = cx_metrics(reqs, SEED + 7 + si)
            staff = (reg + ONCALL_PREMIUM * extra) * ra.COST_PER_SERVER_HOUR
            tech = ra.TECH_COST_DAY if tool else 0
            lost = (cx["lost_margin"] + cx["lost_clv"]) / 30
            res[(sname, st)] = {**s, **cx, "plan": plan, "hours": reg + extra, "extra": extra,
                                "staff": staff, "tech": tech, "lost": lost,
                                "lost_margin_day": cx["lost_margin"] / 30,
                                "lost_clv_day": cx["lost_clv"] / 30,
                                "total": staff + tech + lost}
            r = res[(sname, st)]
            say(f"     {sname:<18} {st:<15} Wq={s['Wq_mean']:6.2f} p90={s['Wq_p90']:6.2f} "
                f"P>5={s['P_wait_gt_target']*100:6.2f}% balk={s['balk_rate']*100:5.2f}% gio={reg + extra:>3} mat={cx['loss_rate']*100:5.2f}% "
                f"NL={staff/1e3:7.1f}k mat={lost/1e3:8.1f}k tong={r['total']/1e3:8.1f}k lich={plan}")
    rows = []
    for sname, _, _ in SCEN:
        for st in STRATS:
            r = res[(sname, st)]
            rows.append([sname.split()[0] if st == STRATS[0] else "", st, r["Wq_mean"],
                         r["P_wait_gt_target"] * 100, r["balk_rate"] * 100, r["hours"],
                         r["loss_rate"] * 100, (r["staff"] + r["tech"]) / 1e3,
                         r["lost"] / 1e3, r["total"] / 1e3])
        rows.append("MID")
    write_table("tab_ext_scenarios.tex",
                [hh("Kịch", "bản"), hh("Chiến lược"), hh("$W_q$", "(phút)"),
                 hh("$P(W_q{>}5)$", "(\\%)"), hh("Bỏ đi vì", "hàng dài (\\%)"),
                 hh("Giờ NV", "/ngày"), hh("Mất khách", "(\\%)"),
                 hh("Nhân lực +", "công nghệ", "(nghìn đ)"), hh("Giá trị mất", "(nghìn đ)"),
                 hh("Tổng", "(nghìn đ)")], rows[:-1], "llrrrrrrrr", nd=2)
    write_csv("ext_scenarios.csv", ["scenario", "strategy", "Wq", "P_gt5_pct", "balk_pct",
                                    "staff_hours", "loss_pct", "staff_tech_kVND",
                                    "lost_kVND", "total_kVND"], rows)

    say("\n[S2] Hoi tiec theo tong chi phi (nghin dong/ngay)")
    cand = ["CL-A", "CL-B tĩnh", "CL-B thích ứng"]
    best_s = {s[0]: min(res[(s[0], st)]["total"] for st in cand) for s in SCEN}
    reg_rows = []
    for st in cand:
        tot = [res[(s[0], st)]["total"] for s in SCEN]
        regret = [t - best_s[s[0]] for t, s in zip(tot, SCEN)]
        exp_c = sum(p * t for p, t in zip(SCEN_PROB, tot))
        ok = sum(res[(s[0], st)]["P_wait_gt_target"] <= ra.TARGET_TAIL
                 and res[(s[0], st)]["balk_rate"] <= 0.01 for s in SCEN)
        reg_rows.append([st] + [t / 1e3 for t in tot] + [exp_c / 1e3, max(regret) / 1e3, f"{ok}/3"])
        say(f"     {st:<15} " + " ".join(f"{t/1e3:9.1f}" for t in tot)
            + f"  E={exp_c/1e3:9.1f}  maxRegret={max(regret)/1e3:8.1f}  dat {ok}/3")
    write_table("tab_ext_regret.tex",
                [hh("Chiến lược")] + [hh(s[0].split()[0]) for s in SCEN]
                + [hh("Kỳ vọng"), hh("Hối tiếc", "tối đa"), hh("Đạt", "mục tiêu")],
                reg_rows, "lrrrrrc", nd=1)

    say("\n[S3] Do nhay theo he so CLV")
    clv_rows = []
    for k in (0.0, 0.5, 1.0, 2.0):
        exp = {}
        for st in cand:
            exp[st] = sum(p * (res[(s[0], st)]["staff"] + res[(s[0], st)]["tech"]
                               + res[(s[0], st)]["lost_margin_day"]
                               + k * res[(s[0], st)]["lost_clv_day"])
                          for p, s in zip(SCEN_PROB, SCEN))
        win = min(exp, key=exp.get)
        clv_rows.append([f"$\\times${k:.1f} ({CLV[2]*k/1e3:,.0f} / {CLV[1]*k/1e6:,.2f})".replace(",", ".")]
                        + [exp[st] / 1e3 for st in cand] + [win])
        say(f"     CLVx{k:.1f} " + "  ".join(f"{st}={exp[st]/1e3:.1f}" for st in cand) + f" -> {win}")
    write_table("tab_ext_clv.tex",
                [hh("Hệ số CLV", "(xe máy nghìn đ / ô tô tr.đ)")] + [hh(st) for st in cand]
                + [hh("Chi phí kỳ vọng", "thấp nhất")], clv_rows, "lrrrl", nd=1)

    say("\n[S4] Ty le khach bo di theo the he (KB-B, %)")
    seg_rows = []
    for nm, share, theta, churn in SEGMENTS:
        vals = [res[("KB-B Nhu cầu tăng", st)][nm] * 100 for st in STRATS]
        seg_rows.append([nm, f2(share * 100, 0), f2(theta, 0), f2(churn * 100, 0)] + vals)
        say(f"     {nm:<16} " + "  ".join(f"{st}={v:.2f}" for st, v in zip(STRATS, vals)))
    write_table("tab_ext_segments.tex",
                [hh("Phân khúc"), hh("Tỷ trọng", "(\\%)"), hh("$\\theta_g$", "(phút)"),
                 hh("$c_g$", "(\\%)")] + [hh(st, "(\\%)") for st in STRATS],
                seg_rows, "lrrrrrrr", nd=2)
    return res


# ============================================================================
# BAI TOAN 4 - HOC MAY: DU BAO LUOT XE NGAY TOI -> LICH NHAN VIEN
# Lich su luot xe la MO PHONG; lich su kien (Tet, cang thang nguon cung, dieu chinh gia
# thu Nam) theo thuc te. Thay bang du lieu POS/hoa don dien tu cua cua hang khi co.
# ============================================================================
START = dt.date(2024, 11, 25)   # thu Hai; 2 nam lich su
N_DAYS = 2 * 364
TETS = [dt.date(2025, 1, 29), dt.date(2026, 2, 17)]   # R: mung 1 Tet At Ty, Binh Ngo
TENSIONS = [(dt.date(2025, 7, 1), 7, 0.35),            # R (bao chi): cua hang dong cua/ban cam chung
            (dt.date(2026, 3, 4), 8, 0.60)]            # R: 7/3/2026 khach tang cao, 17 cua hang tam dung
TEST_START, TEST_DAYS = dt.date(2026, 1, 5), 84         # gom Tet 2026 va dot thang 3/2026
WEEKDAY = np.array([1.04, 1.00, 0.99, 1.02, 1.06, 0.97, 0.92])  # E: T2..CN
PRICE_SD = 900   # d/L: bien do dieu chinh tuan (vd. 5/11/2026: -2.075; 12/11/2026: -1.310)
PRE15 = 9        # so khung gio truoc 15h (06-15) trong ngay dieu chinh


def synth_history(seed=SEED + 500):
    """Lich su 2 nam (mo phong) voi lich su kien that: Tet, dot cang thang nguon cung,
    dieu chinh gia thu Nam luc 15h (gia tang -> do xang truoc 15h; gia giam -> doi sau 15h)."""
    rng = np.random.default_rng(seed)
    days = [START + dt.timedelta(d) for d in range(N_DAYS)]
    wd = np.array([d.weekday() for d in days])
    idx = np.arange(N_DAYS)
    season = 1 + 0.05 * np.sin(2 * np.pi * (idx - 60) / 364)
    tet = np.ones(N_DAYS)
    tet_flag = np.zeros(N_DAYS)
    for k, d in enumerate(days):
        for t in TETS:
            off = (d - t).days
            if -10 <= off <= -4:
                tet[k], tet_flag[k] = 1.20, 1      # do xang ve que, mua sam
            elif -3 <= off <= 5:
                tet[k], tet_flag[k] = 0.55, -1     # nghi Tet
    tension = np.zeros(N_DAYS)
    for t0, length, amp in TENSIONS:
        k0 = (t0 - START).days
        for k in range(length):
            tension[k0 + k] = amp * math.sin(math.pi * (k + 0.5) / length)
    dprice = np.array([float(np.clip(rng.normal(0, PRICE_SD), -2500, 2500)) if d.weekday() == 3
                       else 0.0 for d in days])
    noise = np.exp(rng.normal(0, 0.06, N_DAYS))
    mult = WEEKDAY[wd] * season * tet * (1 + tension) * noise
    lam = np.outer(mult, ra.HOURLY_LAMBDA).astype(float)
    pre = np.arange(ra.HOURS) < PRE15
    for k in range(N_DAYS):
        if dprice[k] != 0:
            x = dprice[k] / 1000
            lam[k, pre] *= max(0.3, 1 + 0.25 * x)      # tang gia: mua truoc 15h
            lam[k, ~pre] *= max(0.3, 1 - 0.15 * x)     # sau 15h: nguoc lai
            if k + 1 < N_DAYS:
                lam[k + 1] *= max(0.3, 1 - 0.06 * x)
    dprice_exp = np.where(dprice != 0, dprice + rng.normal(0, 300, N_DAYS), 0.0)
    signal = np.concatenate([[0.0], tension[:-1]]) + rng.normal(0, 0.05, N_DAYS)
    counts = rng.poisson(lam)
    return {"days": days, "wd": wd, "tet": tet_flag, "dprice": dprice,
            "dprice_exp": dprice_exp, "signal": signal, "lam": lam, "counts": counts,
            "tension": tension}


def design(H, idx):
    tot = H["counts"].sum(axis=1)
    rows = []
    nh = ra.HOURS
    for d in idx:
        hist = tot[max(0, d - 28):d]
        lag = math.log((tot[d - 1] + 1) / (hist.mean() + 1)) if d >= 1 else 0.0
        prev_dp = H["dprice_exp"][d - 1] if d >= 1 else 0.0
        for h in range(nh):
            x = np.zeros(nh + 6 + 9)
            x[h] = 1                                 # gio (16 bien gia)
            if H["wd"][d] > 0:
                x[nh + H["wd"][d] - 1] = 1           # thu (6 bien gia, T2 lam moc)
            b = nh + 6
            dp = H["dprice_exp"][d] / 1000           # muc dieu chinh du kien (nghin d/L)
            x[b] = math.sin(2 * np.pi * d / 364)
            x[b + 1] = math.cos(2 * np.pi * d / 364)
            x[b + 2] = 1.0 if H["tet"][d] > 0 else 0.0   # truoc Tet
            x[b + 3] = 1.0 if H["tet"][d] < 0 else 0.0   # nghi Tet
            x[b + 4] = dp if h < PRE15 else 0.0          # ngay dieu chinh, truoc 15h
            x[b + 5] = dp if h >= PRE15 else 0.0         # ngay dieu chinh, sau 15h
            x[b + 6] = prev_dp / 1000                    # ngay sau dieu chinh
            x[b + 7] = H["signal"][d]                    # tin hieu nguon cung (tre 1 ngay)
            x[b + 8] = lag
            rows.append(x)
    return np.array(rows)


def fit_poisson_glm(X, y, l2=1e-3, iters=60):
    """Hoi quy Poisson (log-link) uoc luong bang IRLS co phat L2 nho."""
    beta = np.zeros(X.shape[1])
    beta[:ra.HOURS] = np.log(y.reshape(-1, ra.HOURS).mean(axis=0) + 0.5)
    for _ in range(iters):
        eta = X @ beta
        mu = np.exp(eta)
        z = eta + (y - mu) / mu
        A = X.T @ (mu[:, None] * X) + l2 * np.eye(X.shape[1])
        new = np.linalg.solve(A, X.T @ (mu * z))
        done = np.max(np.abs(new - beta)) < 1e-9
        beta = new
        if done:
            break
    return beta


def ml_block():
    H = synth_history()
    t0 = (TEST_START - START).days
    train = np.arange(28, t0)
    test = np.arange(t0, t0 + TEST_DAYS)
    beta = fit_poisson_glm(design(H, train), H["counts"][train].ravel())
    assert np.isfinite(beta).all()
    lam_glm = np.exp(design(H, test) @ beta).reshape(len(test), ra.HOURS)
    lam_static = np.tile(ra.HOURLY_LAMBDA, (len(test), 1)).astype(float)
    lam_snaive = np.array([H["counts"][[d - 7, d - 14, d - 21, d - 28]].mean(axis=0) for d in test])
    lam_true = H["lam"][test]
    models = [("Kế hoạch tĩnh (hồ sơ cố định)", lam_static),
              ("TB 4 tuần cùng thứ (seasonal naive)", lam_snaive),
              ("Hồi quy Poisson GLM (học máy)", lam_glm)]
    d0, d1 = H["days"][test[0]], H["days"][test[-1]]
    say(f"\n[M1] Du bao ngay toi: train {H['days'][train[0]]}..{H['days'][train[-1]]}, test {d0}..{d1}")
    act = H["counts"][test].sum(axis=1)
    acc_rows = []
    pmask = (np.abs(H["dprice"][test]) >= 1000) | (H["tension"][test] > 0.05) | (H["tet"][test] != 0)
    for name, lam in models:
        pred = lam.sum(axis=1)
        mape = float(np.mean(np.abs(pred - act) / act) * 100)
        mape_p = float(np.mean(np.abs(pred[pmask] - act[pmask]) / act[pmask]) * 100)
        mae = float(np.mean(np.abs(lam - H["counts"][test])))
        acc_rows.append([name, mape, mape_p, mae])
        say(f"     {name:<38} MAPE={mape:5.2f}%  MAPE ngay su kien={mape_p:5.2f}%  "
            f"MAE gio={mae:.2f} xe/gio")
    b = ra.HOURS + 6
    say(f"     He so: truoc Tet={beta[b+2]:.3f}, Tet={beta[b+3]:.3f}, chinh gia truoc 15h={beta[b+4]:.3f}, "
        f"sau 15h={beta[b+5]:.3f}, ngay sau={beta[b+6]:.3f}, nguon cung={beta[b+7]:.3f}; "
        f"so ngay su kien trong test={int(pmask.sum())}")
    write_table("tab_ext_ml_acc.tex",
                [hh("Mô hình dự báo"), hh("MAPE tổng", "ngày (\\%)"),
                 hh("MAPE ngày", "sự kiện (\\%)"), hh("MAE theo giờ", "(xe/giờ)")],
                acc_rows, "lrrr")

    say("\n[M2] Lap lich theo du bao (so hoa, c <= 8) - mo phong 84 ngay test")
    policies = [("Lịch A2 tĩnh", None), ("Lịch A2 + đệm 20\\%", "buffer"),
                ("Theo TB 4 tuần", lam_snaive), ("Theo GLM (học máy)", lam_glm),
                ("Biết trước nhu cầu (oracle)", lam_true)]
    pol_rows = []
    for pname, lam in policies:
        w_all, w_p, hours, bad, balk_all, arr_all = [], [], 0, 0, 0, 0
        for k, d in enumerate(test):
            if lam is None:
                plan = PLAN_A2
            elif isinstance(lam, str):
                plan = [r["c_star"] for r in ra.optimize_staffing(
                    ra.MEAN_SERVICE_TOBE, lam=[l * 1.2 for l in ra.HOURLY_LAMBDA])]
            else:
                plan = [r["c_star"] for r in ra.optimize_staffing(ra.MEAN_SERVICE_TOBE,
                                                                   lam=list(lam[k]))]
            reqs, _ = run(ra.sim_config(plan, ra.SERVICE_TOBE, lam=list(lam_true[k]), days=1,
                                        seed=SEED + 900 + int(d)))
            w = np.array([r.wq for r in reqs if not r.balked])
            nb = sum(r.balked for r in reqs)
            balk_all += nb
            arr_all += len(reqs)
            w_all.extend(w)
            if pmask[k]:
                w_p.extend(w)
            hours += sum(plan)
            bad += ((w > ra.TARGET_T).mean() > ra.TARGET_TAIL) or nb / len(reqs) > 0.01
        w_all, w_p = np.array(w_all), np.array(w_p)
        nd = len(test)
        row = [pname, float(w_all.mean()), float((w_all > ra.TARGET_T).mean() * 100),
               float(w_p.mean()), float((w_p > ra.TARGET_T).mean() * 100),
               100 * balk_all / arr_all, 100 * bad / nd, hours / nd,
               hours / nd * ra.COST_PER_SERVER_HOUR / 1e3]
        pol_rows.append(row)
        say(f"     {plain(pname):<28} Wq={row[1]:.3f} P>5={row[2]:5.2f}% | ngay su kien: Wq={row[3]:.3f} "
            f"P>5={row[4]:5.2f}% | bo di={row[5]:.2f}% ngay vi pham={row[6]:5.1f}% gio={row[7]:5.2f} "
            f"chiphi={row[8]:.0f}k")
    write_table("tab_ext_ml_staff.tex",
                [hh("Cách lập lịch"), hh("$W_q$", "(phút)"), hh("$P(W_q{>}5)$", "(\\%)"),
                 hh("$W_q$ ngày", "sự kiện (phút)"), hh("$P(W_q{>}5)$ ngày", "sự kiện (\\%)"),
                 hh("Bỏ đi", "(\\%)"), hh("Ngày vi", "phạm (\\%)"), hh("Giờ NV", "/ngày"),
                 hh("Chi phí", "(nghìn đ/ngày)")],
                pol_rows, "lrrrrrrrr", nd=2)
    write_csv("ext_ml.csv", ["policy", "Wq", "P_gt5_pct", "Wq_event_days", "P_gt5_event_days_pct",
                             "balk_pct", "violation_days_pct", "staff_hours", "cost_kVND"], pol_rows)
    return H, test, act, models


# ============================================================================
# HINH VE
# ============================================================================
def charts(loc_res, scen, H, test, act, models):
    plt = ra.setup_mpl()
    fig, ax = plt.subplots(figsize=(6.2, 2.7))
    x = np.arange(len(loc_res))
    wd = 0.38
    ax.bar(x - wd / 2 - 0.01, [r["cover_raw"] for r in loc_res], wd, color=ra.C_BLUE,
           label=f"Nằm trong $R$ = {R_COVER:.0f} phút")
    ax.bar(x + wd / 2 + 0.01, [r["served"] for r in loc_res], wd, color=ra.C_AQUA,
           label="Phục vụ được khi có giới hạn năng lực")
    ax.axhline(DEMAND.sum(), color=ra.C_MUTED, linestyle="--", linewidth=1.1)
    ax.annotate(f"Tổng nhu cầu {DEMAND.sum():,.0f} lượt/ngày".replace(",", "."),
                (len(loc_res) - 0.5, DEMAND.sum() * 1.02), ha="right", fontsize=8, color=ra.C_MUTED)
    ax.set_xticks(x, [r["name"].replace(" + ", "+") for r in loc_res])
    ax.set_ylim(0, DEMAND.sum() * 1.15)
    ax.set_ylabel("Lượt xe/ngày")
    ax.set_title("Chọn 2 trong 5 điểm: nhu cầu được phủ và được phục vụ")
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.12))
    fig.savefig(os.path.join(FIGS, "r2_location.png"))
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(6.4, 2.6), sharey=True)
    cols = {"A0": ra.C_MUTED, "CL-A": ra.C_ORANGE, "CL-B tĩnh": ra.C_BLUE, "CL-B thích ứng": ra.C_AQUA}
    top = 60
    for ax, (sname, _, _) in zip(axes, SCEN):
        vals = [scen[(sname, st)]["P_wait_gt_target"] * 100 for st in STRATS]
        bars = ax.bar(range(len(STRATS)), [min(v, top) for v in vals],
                      color=[cols[s] for s in STRATS], width=0.7)
        for bb, v in zip(bars, vals):
            ax.annotate(f"{v:.1f}", (bb.get_x() + bb.get_width() / 2, min(v, top)),
                        textcoords="offset points", xytext=(0, 2), ha="center", fontsize=7)
        ax.axhline(5, color=ra.C_INK, linestyle="--", linewidth=1)
        ax.set_title(sname.replace(" Nhu cầu", ":").replace(" Gián", ": gián"), fontsize=9)
        ax.set_xticks([])
        ax.grid(axis="x", visible=False)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("$P(W_q>5)$ (%)")
    fig.legend([plt.Rectangle((0, 0), 1, 1, color=cols[s]) for s in STRATS], STRATS,
               loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.06))
    fig.savefig(os.path.join(FIGS, "r3_scenarios.png"))
    plt.close(fig)

    import matplotlib.dates as mdates
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    dates = [H["days"][d] for d in test]
    ax.plot(dates, act, color=ra.C_INK, linewidth=1.2, label="Thực tế (mô phỏng)")
    ax.plot(dates, models[0][1].sum(axis=1), color=ra.C_MUTED, linewidth=1.2, linestyle="--",
            label="Kế hoạch tĩnh")
    ax.plot(dates, models[1][1].sum(axis=1), color=ra.C_ORANGE, linewidth=1.5, label="TB 4 tuần cùng thứ")
    ax.plot(dates, models[2][1].sum(axis=1), color=ra.C_AQUA, linewidth=2, label="Poisson GLM")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.set_xlabel("Ngày (giai đoạn kiểm tra 05/01--29/03/2026)")
    ax.set_ylabel("Lượt xe/ngày")
    ax.set_title("Dự báo lượt xe ngày tới trên tập kiểm tra")
    ax.grid(axis="x", visible=False)
    ax.legend(fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    fig.savefig(os.path.join(FIGS, "r2_forecast.png"))
    plt.close(fig)


def main():
    np.seterr(all="ignore")  # canh bao matmul gia tu Accelerate (macOS); beta da kiem tra huu han
    say("=" * 78)
    say("PHAN MO RONG | DU LIEU MO PHONG, HIEU CHINH TU SO LIEU CONG BO")
    say("=" * 78)
    cap, loc_res, best = location_block()
    scen = scenario_block()
    H, test, act, models = ml_block()
    charts(loc_res, scen, H, test, act, models)
    with open(os.path.join(DATA, "ext_run_log.txt"), "w") as f:
        f.write("\n".join(LOG) + "\n")
    print("\nHoan tat phan mo rong.")


if __name__ == "__main__":
    main()
