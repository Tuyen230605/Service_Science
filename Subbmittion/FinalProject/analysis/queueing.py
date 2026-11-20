"""Cong thuc hang doi M/M/s (Erlang C) dung cho bao cao INT3501.

Don vi thong nhat: lambda (yeu cau/gio), mu (yeu cau/gio/kenh), thoi gian tra ve
theo PHUT khi ham co hau to `_min`.

Nhom tu kiem tra cac cong thuc nay bang hai cach:
  (1) doi chieu voi vi du trong bai giang L4 (M/M/1, M/M/s);
  (2) so sanh voi mo phong su kien roi rac trong `simulate.py` khi thoi gian
      phuc vu la phan phoi mu (xem bang kiem dinh trong bao cao).
"""

from math import exp, factorial, log


def offered_load(lam: float, mu: float) -> float:
    """a = lambda/mu (so kenh toi thieu ve mat ly thuyet)."""
    return lam / mu


def utilization(lam: float, mu: float, c: int) -> float:
    """rho = lambda / (c*mu): muc su dung trung binh cua moi kenh."""
    return lam / (c * mu)


def p_zero(lam: float, mu: float, c: int) -> float:
    a = offered_load(lam, mu)
    rho = utilization(lam, mu, c)
    if rho >= 1:
        return float("nan")
    s = sum(a ** n / factorial(n) for n in range(c))
    s += a ** c / (factorial(c) * (1 - rho))
    return 1.0 / s


def prob_wait(lam: float, mu: float, c: int) -> float:
    """C(c, a): xac suat mot yeu cau den phai cho (cong thuc Erlang C)."""
    a = offered_load(lam, mu)
    rho = utilization(lam, mu, c)
    if rho >= 1:
        return 1.0
    return a ** c / (factorial(c) * (1 - rho)) * p_zero(lam, mu, c)


def lq(lam: float, mu: float, c: int) -> float:
    """So yeu cau trung binh dang cho."""
    rho = utilization(lam, mu, c)
    if rho >= 1:
        return float("inf")
    return prob_wait(lam, mu, c) * rho / (1 - rho)


def wq_min(lam: float, mu: float, c: int) -> float:
    """Thoi gian cho trung binh truoc khi duoc phuc vu (phut)."""
    rho = utilization(lam, mu, c)
    if rho >= 1:
        return float("inf")
    return lq(lam, mu, c) / lam * 60.0


def w_min(lam: float, mu: float, c: int) -> float:
    """Thoi gian trung binh trong he thong W = Wq + E[S] (phut)."""
    return wq_min(lam, mu, c) + 60.0 / mu


def l_system(lam: float, mu: float, c: int) -> float:
    """L = lambda * W (dinh ly Little)."""
    return lam * (w_min(lam, mu, c) / 60.0)


def prob_wait_gt(lam: float, mu: float, c: int, t_min: float) -> float:
    """P(Wq > t) voi t tinh bang phut; = C(c,a) * exp(-(c*mu - lambda) t)."""
    rho = utilization(lam, mu, c)
    if rho >= 1:
        return 1.0
    t_h = t_min / 60.0
    return prob_wait(lam, mu, c) * exp(-(c * mu - lam) * t_h)


def wq_percentile_min(lam: float, mu: float, c: int, p: float = 0.90) -> float:
    """Phan vi p cua thoi gian cho (phut). P(Wq > t) = 1 - p."""
    rho = utilization(lam, mu, c)
    if rho >= 1:
        return float("inf")
    tail = 1 - p
    pw = prob_wait(lam, mu, c)
    if pw <= tail:  # phan vi nam trong phan khong phai cho
        return 0.0
    return log(pw / tail) / (c * mu - lam) * 60.0


def metrics(lam: float, mu: float, c: int, t_target_min: float = 15.0) -> dict:
    """Bo chi so day du cho mot cau hinh (lambda, mu, c)."""
    rho = utilization(lam, mu, c)
    if rho >= 1:
        return {
            "lambda": lam, "mu": mu, "c": c, "rho": rho,
            "stable": False, "Pw": 1.0,
            "Lq": float("inf"), "L": float("inf"),
            "Wq": float("inf"), "W": float("inf"),
            "Wq_p90": float("inf"), "P_gt_target": 1.0,
        }
    return {
        "lambda": lam, "mu": mu, "c": c, "rho": rho, "stable": True,
        "Pw": prob_wait(lam, mu, c),
        "Lq": lq(lam, mu, c),
        "L": l_system(lam, mu, c),
        "Wq": wq_min(lam, mu, c),
        "W": w_min(lam, mu, c),
        "Wq_p90": wq_percentile_min(lam, mu, c, 0.90),
        "P_gt_target": prob_wait_gt(lam, mu, c, t_target_min),
    }
