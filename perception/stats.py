"""Exact binomial bounds, shared by the detector evaluation and the trial report (Clopper-Pearson)."""

from scipy.stats import beta


def upper_bound(k: int, n: int, confidence: float = 0.95) -> float:
    """Exact one-sided upper bound on a rate seen k times in n."""
    return 1.0 if k >= n else float(beta.ppf(confidence, k + 1, n - k))


def interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    tail = (1 - confidence) / 2
    low = 0.0 if k == 0 else float(beta.ppf(tail, k, n - k + 1))
    high = 1.0 if k == n else float(beta.ppf(1 - tail, k + 1, n - k))
    return low, high
