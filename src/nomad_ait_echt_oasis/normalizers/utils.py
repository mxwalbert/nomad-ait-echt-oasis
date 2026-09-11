from typing import Any

import numpy as np
import plotly.graph_objs as go


def get_quantity_array(
    qty: Any,
    unit: str | None = None,
    dtype: type = float,
) -> np.ndarray | None:
    """
    Safely extract a NumPy array from a NOMAD/Pint Quantity in target units.
    Returns None if qty is None or empty.
    """
    if qty is None:
        return None
    try:
        val = qty.to(unit).magnitude if unit else getattr(qty, 'magnitude', qty)
        arr = np.asarray(val, dtype=dtype)
        return arr if arr.size > 0 else None
    except Exception:
        return None


def get_quantity_scalar(
    qty: Any,
    unit: str | None = None,
) -> float | None:
    """
    Safely extract a scalar float from a NOMAD/Pint Quantity in target units.
    Returns None if qty is None.
    """
    if qty is None:
        return None
    try:
        val = qty.to(unit).magnitude if unit else getattr(qty, 'magnitude', qty)
        return float(val)
    except Exception:
        return None


def build_scatter_trace(  # noqa: PLR0913
    x: np.ndarray,
    y: np.ndarray,
    name: str,
    yaxis: str | None = None,
    mode: str = 'lines',
    line: dict[str, Any] | None = None,
    marker: dict[str, Any] | None = None,
) -> go.Scatter:
    """Helper to construct a Plotly Scatter trace cleanly."""
    trace_kwargs: dict[str, Any] = {
        'x': x,
        'y': y,
        'mode': mode,
        'name': name,
    }
    if yaxis is not None:
        trace_kwargs['yaxis'] = yaxis
    if line is not None:
        trace_kwargs['line'] = line
    if marker is not None:
        trace_kwargs['marker'] = marker
    return go.Scatter(**trace_kwargs)
