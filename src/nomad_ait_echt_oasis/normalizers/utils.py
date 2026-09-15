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
        if unit and hasattr(qty, 'to'):
            val = qty.to(unit).magnitude
        else:
            val = getattr(qty, 'magnitude', qty)
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
        if unit and hasattr(qty, 'to'):
            val = qty.to(unit).magnitude
        else:
            val = getattr(qty, 'magnitude', qty)
        return float(val)
    except Exception:
        return None


def build_scatter_trace(  # noqa: PLR0913
    x: Any,
    y: Any,
    name: str,
    yaxis: str | None = None,
    mode: str = 'lines',
    line: dict[str, Any] | None = None,
    marker: dict[str, Any] | None = None,
) -> go.Scatter:
    """Helper to construct a Plotly Scatter trace cleanly."""
    trace_kwargs: dict[str, Any] = {
        'x': x.tolist() if isinstance(x, np.ndarray) else x,
        'y': y.tolist() if isinstance(y, np.ndarray) else y,
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


MIN_SLICE_LENGTH = 3


def parse_cycle_slice(slice_str: str | None) -> slice:
    """
    Parse a Python slice syntax string (e.g., '2:6') into a slice object.
    Returns slice(None) if slice_str is None, empty, or invalid.
    """
    if not slice_str or not isinstance(slice_str, str):
        return slice(None)
    parts = slice_str.strip().split(':')
    if len(parts) > MIN_SLICE_LENGTH:
        return slice(None)
    try:
        parsed = [int(p.strip()) if p.strip() else None for p in parts]
        return slice(*parsed)
    except ValueError:
        return slice(None)
