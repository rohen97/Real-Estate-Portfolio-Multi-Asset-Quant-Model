from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf


def nearest_psd(matrix, epsilon=1e-8):
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2)
    values = np.maximum(values, epsilon)
    result = vectors @ np.diag(values) @ vectors.T
    scale = np.sqrt(np.diag(result))
    return result / np.outer(scale, scale)


def exponentially_weighted_covariance(frame: pd.DataFrame, decay=0.97):
    values = frame.to_numpy(float)
    weights = decay ** np.arange(len(values) - 1, -1, -1)
    weights /= weights.sum()
    mean = (values * weights[:, None]).sum(0)
    centered = values - mean
    return (centered * weights[:, None]).T @ centered


def calibrate_covariance(records: list[dict], columns: list[str], decay=0.97):
    frame = pd.DataFrame(records)[columns].dropna()
    if len(frame) < 30:
        return {"status": "blocked", "observations": len(frame), "reason": "At least 30 complete time observations required"}
    raw = frame.cov().to_numpy()
    ewma = exponentially_weighted_covariance(frame, decay)
    standard_deviation = frame.std(ddof=1).replace(0, 1e-12).to_numpy(float)
    standardised = (frame - frame.mean()) / standard_deviation
    shrunk_standardised_covariance = LedoitWolf().fit(standardised).covariance_
    shrunk_scale = np.sqrt(np.diag(shrunk_standardised_covariance))
    correlation = nearest_psd(shrunk_standardised_covariance / np.outer(shrunk_scale, shrunk_scale))
    shrink = correlation * np.outer(standard_deviation, standard_deviation)
    return {
        "status": "calibrated",
        "columns": columns,
        "observations": len(frame),
        "means": frame.mean().to_numpy(float).tolist(),
        "sample_covariance": raw.tolist(),
        "ewma_covariance": ewma.tolist(),
        "ledoit_wolf_covariance": shrink.tolist(),
        "correlation": correlation.tolist(),
        "decay": decay,
        "method": "Scale-normalised Ledoit-Wolf correlation with exponentially weighted covariance diagnostic",
    }
