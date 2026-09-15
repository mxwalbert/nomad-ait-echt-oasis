from typing import TYPE_CHECKING, Any

import numpy as np
import plotly.graph_objs as go
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad.units import ureg

from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cell import (
    normalize_three_electrode_cell,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cv import (
    C_UNIT,
    normalize_cv_result,
)
from nomad_ait_echt_oasis.normalizers.utils import (
    build_scatter_trace,
    get_quantity_array,
    get_quantity_scalar,
    parse_cycle_slice,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
        ECSAMeasurement,
        ECSAResult,
    )

MIN_POINTS_FOR_CAPACITANCE = 2
MIN_DATA_POINTS = 3


def extract_anodic_cathodic_arcs(
    v_arr: np.ndarray,
    i_arr: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Separate a cyclic voltammetry sweep into anodic and cathodic arcs
    bounded by the minimum and maximum potentials.
    Returns (v_anod, i_anod, v_cath, i_cath).
    """
    if len(v_arr) < MIN_DATA_POINTS or len(i_arr) < MIN_DATA_POINTS:
        return np.array([]), np.array([]), np.array([]), np.array([])

    grad = np.gradient(v_arr)
    tol = 1e-7

    anod_mask = grad > tol
    cath_mask = grad < -tol
    return v_arr[anod_mask], i_arr[anod_mask], v_arr[cath_mask], i_arr[cath_mask]


def filter_arc_window(
    v_arc: np.ndarray,
    i_arc: np.ndarray,
    v_mid: float,
    v_span: float,
    width_fraction: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Filter arc points to a potential window centered at v_mid with
    width = width_fraction * v_span.
    """
    if len(v_arc) == 0:
        return v_arc, i_arc

    w = (
        0.5
        if width_fraction is None or width_fraction <= 0
        else min(width_fraction, 1.0)
    )
    half_width = (w * v_span) / 2.0
    v_low = v_mid - half_width
    v_high = v_mid + half_width

    mask = (v_arc >= v_low) & (v_arc <= v_high)
    if np.count_nonzero(mask) >= MIN_POINTS_FOR_CAPACITANCE:
        return v_arc[mask], i_arc[mask]
    return v_arc, i_arc


def extract_capacitive_current(
    v_arr: np.ndarray,
    i_arr: np.ndarray,
    min_points: int = MIN_POINTS_FOR_CAPACITANCE,
) -> float | None:
    """
    Extract midpoint capacitive charging current from forward and reverse sweeps.
    Returns None if data points are insufficient. Kept for fallback and testing.
    """
    if len(v_arr) < min_points or len(i_arr) < min_points:
        return None

    v_min, v_max = float(np.min(v_arr)), float(np.max(v_arr))
    v_mid = (v_min + v_max) / 2.0

    diffs = np.diff(v_arr)
    diffs = np.append(diffs, diffs[-1])
    fwd_mask = diffs > 0
    rev_mask = diffs < 0

    i_fwd, v_fwd = i_arr[fwd_mask], v_arr[fwd_mask]
    i_rev, v_rev = i_arr[rev_mask], v_arr[rev_mask]

    if (
        len(v_fwd) > 1
        and len(v_rev) > 1
        and np.min(v_fwd) <= v_mid <= np.max(v_fwd)
        and np.min(v_rev) <= v_mid <= np.max(v_rev)
    ):
        sort_fwd = np.argsort(v_fwd)
        sort_rev = np.argsort(v_rev)
        i_anodic_mid = float(np.interp(v_mid, v_fwd[sort_fwd], i_fwd[sort_fwd]))
        i_cathodic_mid = float(np.interp(v_mid, v_rev[sort_rev], i_rev[sort_rev]))
        return abs(i_anodic_mid - i_cathodic_mid) / 2.0

    return float(np.max(i_arr) - np.min(i_arr)) / 2.0


def add_capacitance_fits_to_figure(  # noqa: PLR0913
    run: Any,
    poly_anod: np.ndarray,
    poly_cath: np.ndarray,
    v_fit_min: float,
    v_fit_max: float,
    surface_area: float | None = None,
) -> None:
    """
    Add anodic and cathodic linear fit lines to the run's cyclic voltammogram plot.
    """
    if not (getattr(run, 'figures', None) and v_fit_max > v_fit_min):
        return

    volt_fig = next(
        (f for f in run.figures if getattr(f, 'label', None) == 'Cyclic Voltammogram'),
        None,
    )
    if not (
        volt_fig and isinstance(volt_fig.figure, dict) and 'data' in volt_fig.figure
    ):
        return

    layout = volt_fig.figure.get('layout', {})
    y_title = str(layout.get('yaxis_title') or layout.get('yaxis', {}).get('title', ''))
    use_density = 'mA/cm²' in y_title or 'Current Density' in y_title
    y_scale = (
        (1000.0 / surface_area)
        if (use_density and surface_area and surface_area > 0)
        else 1000.0
    )

    v_line = np.linspace(v_fit_min, v_fit_max, 50)
    traces = [
        build_scatter_trace(
            x=v_line,
            y=np.polyval(poly_anod, v_line) * y_scale,
            name='Anodic Fit',
            line=dict(dash='dash', color='red', width=2),
        ),
        build_scatter_trace(
            x=v_line,
            y=np.polyval(poly_cath, v_line) * y_scale,
            name='Cathodic Fit',
            line=dict(dash='dash', color='blue', width=2),
        ),
    ]

    fig_dict = dict(volt_fig.figure)
    fig_data = fig_dict.get('data', [])
    clean_traces = [
        t
        for t in fig_data
        if isinstance(t, dict) and t.get('name') not in ('Anodic Fit', 'Cathodic Fit')
    ]
    for trace in traces:
        t_json = trace.to_plotly_json()
        if isinstance(t_json.get('x'), np.ndarray):
            t_json['x'] = t_json['x'].tolist()
        if isinstance(t_json.get('y'), np.ndarray):
            t_json['y'] = t_json['y'].tolist()
        clean_traces.append(t_json)

    fig_dict['data'] = clean_traces
    volt_fig.figure = fig_dict


def evaluate_run_capacitance(
    run: Any,
    cycle_selection: str | None = None,
    width_fraction: float = 0.5,
    surface_area: float | None = None,
) -> float | None:
    """
    Extract anodic and cathodic arcs across selected cycles, filter to the centered
    potential window, perform linear regressions, compute capacitive current distance,
    and update run's Plotly voltammogram with the fit lines.
    """
    cycles = getattr(run, 'cycles', None) or (
        [run] if getattr(run, 'potential', None) is not None else []
    )
    selected_cycles = cycles[parse_cycle_slice(cycle_selection)] if cycles else []
    if not selected_cycles:
        return None

    anod_data, cath_data, v_mids = [], [], []
    full_mins, full_maxs = [], []

    for cyc in selected_cycles:
        v_c = get_quantity_array(cyc.potential, 'volt')
        i_c = get_quantity_array(cyc.current, 'ampere')
        if v_c is None or i_c is None or len(v_c) < MIN_DATA_POINTS:
            continue

        v_min_cyc, v_max_cyc = float(np.min(v_c)), float(np.max(v_c))
        if v_max_cyc <= v_min_cyc:
            continue

        full_mins.append(v_min_cyc)
        full_maxs.append(v_max_cyc)

        v_mid = (v_min_cyc + v_max_cyc) / 2.0
        v_span = v_max_cyc - v_min_cyc
        v_mids.append(v_mid)

        v_a, i_a, v_c_arc, i_c_arc = extract_anodic_cathodic_arcs(v_c, i_c)
        v_a_f, i_a_f = filter_arc_window(v_a, i_a, v_mid, v_span, width_fraction)
        v_c_f, i_c_f = filter_arc_window(
            v_c_arc, i_c_arc, v_mid, v_span, width_fraction
        )

        if len(v_a_f) > 0:
            anod_data.append((v_a_f, i_a_f))
        if len(v_c_f) > 0:
            cath_data.append((v_c_f, i_c_f))

    if not anod_data or not cath_data:
        return None

    v_a = np.concatenate([d[0] for d in anod_data])
    i_a = np.concatenate([d[1] for d in anod_data])
    v_c = np.concatenate([d[0] for d in cath_data])
    i_c = np.concatenate([d[1] for d in cath_data])

    if len(v_a) < MIN_POINTS_FOR_CAPACITANCE or len(v_c) < MIN_POINTS_FOR_CAPACITANCE:
        return None

    poly_anod = np.polyfit(v_a, i_a, 1)
    poly_cath = np.polyfit(v_c, i_c, 1)

    v_mid_eval = (
        float(np.mean(v_mids)) if v_mids else float((np.mean(v_a) + np.mean(v_c)) / 2.0)
    )
    i_cap = (
        abs(
            float(np.polyval(poly_anod, v_mid_eval))
            - float(np.polyval(poly_cath, v_mid_eval))
        )
        / 2.0
    )

    add_capacitance_fits_to_figure(
        run,
        poly_anod,
        poly_cath,
        min(float(np.min(v_a)), float(np.min(v_c))),
        max(float(np.max(v_a)), float(np.max(v_c))),
        surface_area=surface_area,
    )

    return i_cap


def evaluate_capacitance(
    target: 'ECSAResult',
    surface_area_val: float | None = None,
    cycle_selection: str | None = None,
    width_fraction: float = 0.5,
) -> None:
    """
    Estimate capacitive charging currents, fit double layer capacitance,
    and compute ECSA.
    """
    runs = getattr(target, 'runs', None) or getattr(target, 'results', [])
    v_rates = []
    i_caps = []

    for run in runs:
        sr_val = get_quantity_scalar(getattr(run, 'scan_rate', None), 'volt / second')
        if sr_val is None:
            continue

        i_cap = evaluate_run_capacitance(
            run,
            cycle_selection=cycle_selection,
            width_fraction=width_fraction,
            surface_area=surface_area_val,
        )
        if i_cap is not None:
            v_rates.append(sr_val)
            i_caps.append(i_cap)

    if len(v_rates) >= MIN_POINTS_FOR_CAPACITANCE:
        sort_idx = np.argsort(v_rates)
        rates_sorted = np.array(v_rates)[sort_idx]
        caps_sorted = np.array(i_caps)[sort_idx]

        target.scan_rates = rates_sorted * (ureg.volt / ureg.second)
        target.charging_currents = caps_sorted * ureg.ampere

        slope, _ = np.polyfit(rates_sorted, caps_sorted, 1)
        if slope > 0:
            target.double_layer_capacitance = float(slope) * ureg.farad


def generate_ecsa_plotly_figures(target: 'ECSAResult') -> list[PlotlyFigure]:
    """Generate interactive Plotly figure for ECSA Cdl determination fit."""
    figures = []
    v_sr_mv = get_quantity_array(
        getattr(target, 'scan_rates', None), 'millivolt / second'
    )
    i_c_ma = get_quantity_array(getattr(target, 'charging_currents', None), C_UNIT)

    if v_sr_mv is not None and i_c_ma is not None:
        fig_cdl = go.Figure()
        fig_cdl.add_trace(
            build_scatter_trace(
                x=v_sr_mv,
                y=i_c_ma,
                mode='markers',
                name='Charging Current',
                marker=dict(size=8, color='blue'),
            )
        )
        cdl_val = get_quantity_scalar(
            getattr(target, 'double_layer_capacitance', None), 'farad'
        )
        if cdl_val is not None:
            fit_x = np.linspace(float(np.min(v_sr_mv)), float(np.max(v_sr_mv)), 50)
            fit_y = (cdl_val * (fit_x / 1000.0)) * 1000.0
            fig_cdl.add_trace(
                build_scatter_trace(
                    x=fit_x,
                    y=fit_y,
                    mode='lines',
                    name=f'Fit (Cdl = {cdl_val * 1e3:.2f} mF)',
                    line=dict(dash='dash', color='red'),
                )
            )
        fig_cdl.update_layout(
            title='Double-Layer Capacitance Fit (Cdl)',
            xaxis_title='Scan Rate (mV/s)',
            yaxis_title=f'Charging Current ({C_UNIT})',
            template='plotly_white',
        )
        figures.append(
            PlotlyFigure(
                label='Cdl Determination',
                figure=fig_cdl.to_plotly_json(),
            )
        )

    return figures


def normalize_ecsa_result(  # noqa: PLR0913
    result: 'ECSAResult',
    cell: Any = None,
    surface_area_val: float | None = None,
    ref_potential_rhe: float | None = None,
    ph_val: float | None = None,
    parameters: Any = None,
    cycle_selection: str | None = None,
    width_fraction: float = 0.5,
) -> None:
    """Normalize each CV run in an ECSAResult, fit capacitance, and build figures."""
    if surface_area_val is None and cell is not None:
        surface_area_val = get_quantity_scalar(
            getattr(cell, 'surface_area', None), 'centimeter ** 2'
        )

    runs = getattr(result, 'runs', None) or getattr(result, 'results', [])
    param_runs = getattr(parameters, 'runs', []) if parameters is not None else []
    for idx, run in enumerate(runs):
        run_param = param_runs[idx] if idx < len(param_runs) else None
        normalize_cv_result(
            run,
            cell=cell,
            surface_area_val=surface_area_val,
            ref_potential_rhe=ref_potential_rhe,
            ph_val=ph_val,
            parameters=run_param,
            cycle_selection=cycle_selection,
        )

    if runs:
        evaluate_capacitance(
            result,
            surface_area_val=surface_area_val,
            cycle_selection=cycle_selection,
            width_fraction=width_fraction,
        )
        result.figures = generate_ecsa_plotly_figures(result)


def normalize_ecsa_measurement(
    ecsa: 'ECSAMeasurement',
    archive: 'EntryArchive' = None,
    logger: 'BoundLogger' = None,
    cycle_selection: str | None = None,
    width_fraction: float = 0.5,
) -> None:
    """
    Extract cell parameters and normalize all CV results
    in an ECSAMeasurement entry.
    """
    if getattr(ecsa, 'cell', None) is not None:
        normalize_three_electrode_cell(ecsa.cell, archive, logger)

    params = getattr(ecsa, 'parameters', None)
    for res in getattr(ecsa, 'results', None) or []:
        normalize_ecsa_result(
            res,
            cell=ecsa.cell,
            parameters=params,
            cycle_selection=cycle_selection,
            width_fraction=width_fraction,
        )
