"""Mo phong su kien roi rac (DES) cho tram xu ly yeu cau tu van - phan loai.

Muc dich trong bao cao:
  (1) SINH DU LIEU MO PHONG co nhan ro rang (khong phai du lieu thuc te) de
      phuc vu buoc uoc luong tham so lambda, mu;
  (2) KIEM DINH cong thuc M/M/s: khi thoi gian phuc vu la phan phoi mu va
      ky luat FCFS, ket qua mo phong phai trung voi Erlang C trong sai so mo phong;
  (3) DANH GIA cac tinh huong ma cong thuc M/M/s KHONG mo ta duoc: thoi gian
      phuc vu bien thien khac phan phoi mu (CV != 1) va ky luat uu tien
      khong chen ngang (non-preemptive priority) theo 3 muc do uu tien.

Moi thoi gian ben trong module tinh bang PHUT, moc 0 = thoi diem mo cua so
tiep nhan trong ngay.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Request:
    rid: int
    day: int
    priority: int           # 1 = khan, 2 = thuong, 3 = thap
    t_arrival: float
    t_start: float = float("nan")
    t_end: float = float("nan")
    service: float = float("nan")

    @property
    def wq(self) -> float:
        return self.t_start - self.t_arrival

    @property
    def w(self) -> float:
        return self.t_end - self.t_arrival


@dataclass
class SimConfig:
    hourly_lambda: list[float]      # cuong do den theo tung gio lam viec (yc/gio)
    class_mix: dict[int, float]     # ty le cac muc uu tien
    mean_service_min: float         # E[S] (phut)
    cv_service: float = 1.0         # he so bien thien cua thoi gian phuc vu
    servers_by_hour: list[int] = field(default_factory=list)  # so kenh moi gio
    priority_rule: bool = False     # True: uu tien khong chen ngang
    days: int = 20
    seed: int = 20260117


def _service_sample(rng: np.random.Generator, mean: float, cv: float) -> float:
    if abs(cv - 1.0) < 1e-9:
        return float(rng.exponential(mean))
    sigma2 = np.log(1.0 + cv ** 2)
    mu_ln = np.log(mean) - sigma2 / 2.0
    return float(rng.lognormal(mu_ln, np.sqrt(sigma2)))


def _generate_arrivals(rng: np.random.Generator, cfg: SimConfig, day: int,
                       start_rid: int) -> list[Request]:
    """Dong den Poisson khong thuan nhat: moi gio co cuong do rieng."""
    reqs: list[Request] = []
    rid = start_rid
    classes = sorted(cfg.class_mix)
    probs = [cfg.class_mix[k] for k in classes]
    for h, lam in enumerate(cfg.hourly_lambda):
        n = rng.poisson(lam)
        times = np.sort(rng.uniform(h * 60.0, (h + 1) * 60.0, size=n))
        for t in times:
            pri = int(rng.choice(classes, p=probs))
            reqs.append(Request(rid=rid, day=day, priority=pri, t_arrival=float(t)))
            rid += 1
    reqs.sort(key=lambda r: r.t_arrival)
    return reqs


def _servers_at(cfg: SimConfig, t: float) -> int:
    """So kenh phuc vu hoat dong tai thoi diem t (phut)."""
    h = int(t // 60)
    h = min(max(h, 0), len(cfg.servers_by_hour) - 1)
    return cfg.servers_by_hour[h]


def run_day(cfg: SimConfig, rng: np.random.Generator, day: int,
            start_rid: int) -> tuple[list[Request], float]:
    """Mo phong mot ngay lam viec. Tra ve (danh sach yeu cau, tong gio kenh-ban).

    Quy uoc mo hinh:
      - So kenh thay doi theo gio (lich truc). Khi so kenh giam, kenh dang
        phuc vu van hoan tat yeu cau hien tai (khong bo do giua ca).
      - Yeu cau den sau gio dong cua so tiep nhan khong duoc sinh ra; yeu cau
        con lai trong hang doi duoc xu ly tiep (lam them gio).
    """
    reqs = _generate_arrivals(rng, cfg, day, start_rid)
    for r in reqs:
        r.service = _service_sample(rng, cfg.mean_service_min, cfg.cv_service)

    busy: list[float] = []              # heap cac thoi diem hoan tat
    waiting: list[tuple] = []           # heap theo (uu tien, thoi diem den)
    i, n = 0, len(reqs)
    busy_minutes = 0.0
    t = 0.0

    def push_wait(req: Request) -> None:
        key = (req.priority, req.t_arrival) if cfg.priority_rule else (0, req.t_arrival)
        heapq.heappush(waiting, (key, req.rid, req))

    def try_start(now: float) -> None:
        nonlocal busy_minutes
        while waiting and len(busy) < _servers_at(cfg, now):
            _, _, req = heapq.heappop(waiting)
            req.t_start = now
            req.t_end = now + req.service
            busy_minutes += req.service
            heapq.heappush(busy, req.t_end)

    while i < n or waiting or busy:
        t_arr = reqs[i].t_arrival if i < n else float("inf")
        t_dep = busy[0] if busy else float("inf")
        if t_arr <= t_dep:
            t = t_arr
            push_wait(reqs[i])
            i += 1
            try_start(t)
        else:
            t = heapq.heappop(busy)
            try_start(t)

    return reqs, busy_minutes


def run(cfg: SimConfig) -> tuple[list[Request], dict]:
    rng = np.random.default_rng(cfg.seed)
    all_reqs: list[Request] = []
    total_busy = 0.0
    rid = 1
    for d in range(1, cfg.days + 1):
        reqs, busy_min = run_day(cfg, rng, d, rid)
        all_reqs.extend(reqs)
        total_busy += busy_min
        rid += len(reqs)
    capacity_min = cfg.days * sum(cfg.servers_by_hour) * 60.0
    return all_reqs, {"busy_minutes": total_busy,
                      "capacity_minutes": capacity_min,
                      "utilization": total_busy / capacity_min}


def summarize(reqs: list[Request], target_min: float = 15.0) -> dict:
    wq = np.array([r.wq for r in reqs])
    w = np.array([r.w for r in reqs])
    out = {
        "n": len(reqs),
        "Wq_mean": float(wq.mean()),
        "Wq_p90": float(np.percentile(wq, 90)),
        "Wq_max": float(wq.max()),
        "W_mean": float(w.mean()),
        "P_wait_gt_0": float((wq > 1e-9).mean()),
        "P_wait_gt_target": float((wq > target_min).mean()),
    }
    for pri in sorted({r.priority for r in reqs}):
        sub = np.array([r.wq for r in reqs if r.priority == pri])
        out[f"Wq_mean_P{pri}"] = float(sub.mean())
        out[f"Wq_p90_P{pri}"] = float(np.percentile(sub, 90))
        out[f"P_gt_target_P{pri}"] = float((sub > target_min).mean())
    return out
