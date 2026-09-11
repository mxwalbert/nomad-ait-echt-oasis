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
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
        ECSAMeasurement,
        ECSAResult,
    )

MIN_POINTS_FOR_CAPACITANCE = 2


def extract_capacitive_current(
    v_arr: np.ndarray,
    i_arr: np.ndarray,
    min_points: int = MIN_POINTS_FOR_CAPACITANCE,
) -> float | None:
    """
    Extract midpoint capacitive charging current from forward and reverse sweeps.
    Returns None if data points are insufficient.
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


def evaluate_capacitance(target: 'ECSAResult') -> None:
    """
    Estimate capacitive charging currents, fit double layer capacitance,
    and compute ECSA.
    """
    runs = getattr(target, 'runs', None) or getattr(target, 'results', [])
    v_rates = []
    i_caps = []

    for run in runs:
        sr_val = get_quantity_scalar(getattr(run, 'scan_rate', None), 'volt / second')
        v_arr = get_quantity_array(getattr(run, 'potential', None), 'volt')
        i_arr = get_quantity_array(getattr(run, 'current', None), 'ampere')

        if sr_val is None or v_arr is None or i_arr is None:
            continue

        i_cap = extract_capacitive_current(v_arr, i_arr)
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

        # Calculate electrochemical surface area if specific capacitance is provided
        if (
            target.double_layer_capacitance is not None
            and getattr(target, 'specific_capacitance', None) is not None
            and target.specific_capacitance.magnitude > 0
        ):
            target.electrochemical_surface_area = (
                target.double_layer_capacitance / target.specific_capacitance
            ).to('centimeter ** 2')


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


def normalize_ecsa_result(
    result: 'ECSAResult',
    cell: Any = None,
    surface_area_val: float | None = None,
    ref_potential_rhe: float | None = None,
    ph_val: float | None = None,
) -> None:
    """Normalize each CV run in an ECSAResult, fit capacitance, and build figures."""
    runs = getattr(result, 'runs', None) or getattr(result, 'results', [])
    for run in runs:
        normalize_cv_result(
            run,
            cell=cell,
            surface_area_val=surface_area_val,
            ref_potential_rhe=ref_potential_rhe,
            ph_val=ph_val,
        )

    if runs:
        evaluate_capacitance(result)
        result.figures = generate_ecsa_plotly_figures(result)


def normalize_ecsa_measurement(
    ecsa: 'ECSAMeasurement',
    archive: 'EntryArchive' = None,
    logger: 'BoundLogger' = None,
) -> None:
    """
    Extract cell parameters and normalize all CV results
    in an ECSAMeasurement entry.
    """
    if getattr(ecsa, 'cell', None) is not None:
        normalize_three_electrode_cell(ecsa.cell, archive, logger)

    for res in getattr(ecsa, 'results', None) or []:
        normalize_ecsa_result(res, cell=ecsa.cell)
