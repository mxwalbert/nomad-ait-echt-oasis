from typing import TYPE_CHECKING, Any

import numpy as np
import plotly.graph_objs as go
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad.units import ureg

from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cell import (
    normalize_three_electrode_cell,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.result import (
    C_UNIT,
    CD_UNIT,
    normalize_measurement_signals,
)
from nomad_ait_echt_oasis.normalizers.utils import (
    build_scatter_trace,
    get_quantity_array,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
        CVCycle,
        CVResult,
        CyclicVoltammetry,
    )

MIN_POINTS_FOR_CYCLE_SPLIT = 10
MIN_CYCLE_LENGTH = 5


def _get_y_data(target: Any, use_density: bool) -> np.ndarray | None:
    """Extract current or current density array based on use_density flag."""
    if use_density and getattr(target, 'current_density', None) is not None:
        return get_quantity_array(target.current_density, CD_UNIT)
    if getattr(target, 'current', None) is not None:
        return get_quantity_array(target.current, C_UNIT)


def generate_cv_plotly_figures(
    result: 'CVResult', use_density: bool = False
) -> list[PlotlyFigure]:
    """Generate interactive Plotly figures for CV voltammogram and time series."""
    figures = []
    if not result.cycles and (result.potential is None or result.current is None):
        return figures

    y_label = 'Current Density (mA/cm²)' if use_density else 'Current (mA)'

    # 1. Voltammogram (I-V or J-V)
    fig_cv = go.Figure()
    if result.cycles:
        for cyc in result.cycles:
            v = get_quantity_array(cyc.potential, 'volt')
            y = _get_y_data(cyc, use_density)
            if v is not None and y is not None:
                name = (
                    f'Cycle {cyc.cycle_index}'
                    if cyc.cycle_index is not None
                    else 'Voltammogram'
                )
                fig_cv.add_trace(build_scatter_trace(x=v, y=y, name=name))
    elif result.potential is not None and result.current is not None:
        v = get_quantity_array(result.potential, 'volt')
        y = _get_y_data(result, use_density)
        if v is not None and y is not None:
            fig_cv.add_trace(build_scatter_trace(x=v, y=y, name='Voltammogram'))

    fig_cv.update_layout(
        title='Cyclic Voltammogram',
        xaxis_title='Potential vs. Reference (V)',
        yaxis_title=y_label,
        hovermode='closest',
        template='plotly_white',
    )
    figures.append(
        PlotlyFigure(
            label='Cyclic Voltammogram',
            figure=fig_cv.to_plotly_json(),
        )
    )

    # 2. Time series (E(t) and I(t))
    fig_time = go.Figure()
    has_time = False

    if result.time is not None:
        t = get_quantity_array(result.time, 'second')
        v = get_quantity_array(result.potential, 'volt')
        y = _get_y_data(result, use_density)
        if t is not None and v is not None and y is not None:
            has_time = True
            fig_time.add_trace(
                build_scatter_trace(x=t, y=v, name='Potential (V)', yaxis='y1')
            )
            fig_time.add_trace(build_scatter_trace(x=t, y=y, name=y_label, yaxis='y2'))
    elif result.cycles:
        for cyc in result.cycles:
            t = get_quantity_array(cyc.time, 'second')
            v = get_quantity_array(cyc.potential, 'volt')
            y = _get_y_data(cyc, use_density)
            if t is not None and v is not None and y is not None:
                has_time = True
                suffix = (
                    f' (Cycle {cyc.cycle_index})'
                    if len(result.cycles) > 1 and cyc.cycle_index is not None
                    else ''
                )
                fig_time.add_trace(
                    build_scatter_trace(
                        x=t, y=v, name=f'Potential (V){suffix}', yaxis='y1'
                    )
                )
                fig_time.add_trace(
                    build_scatter_trace(x=t, y=y, name=f'{y_label}{suffix}', yaxis='y2')
                )

    if has_time:
        fig_time.update_layout(
            title='Chrono-Response (Potential & Current vs. Time)',
            xaxis_title='Time (s)',
            yaxis=dict(title='Potential (V)', side='left'),
            yaxis2=dict(title=y_label, side='right', overlaying='y'),
            template='plotly_white',
        )
        figures.append(
            PlotlyFigure(
                label='Potential & Current vs. Time',
                figure=fig_time.to_plotly_json(),
            )
        )

    return figures


def create_cv_cycle(  # noqa: PLR0913
    cycle_index: int,
    potential: np.ndarray,
    current: np.ndarray,
    time: np.ndarray | None = None,
    current_density: np.ndarray | None = None,
    potential_vs_rhe: np.ndarray | None = None,
    selector: slice | np.ndarray | None = None,
) -> 'CVCycle':
    """Construct a CVCycle section applying optional slice or boolean mask selection."""
    from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
        CVCycle,
    )

    sel = slice(None) if selector is None else selector
    cyc = CVCycle(
        cycle_index=cycle_index,
        potential=potential[sel] * ureg.volt,
        current=current[sel] * ureg.ampere,
    )
    if time is not None:
        cyc.time = time[sel] * ureg.second
    if current_density is not None:
        cyc.current_density = current_density[sel] * (
            ureg.milliampere / (ureg.centimeter**2)
        )
    if potential_vs_rhe is not None:
        cyc.potential_vs_rhe = potential_vs_rhe[sel] * ureg.volt
    return cyc


def auto_decompose_cycles(result: 'CVResult') -> None:
    """
    Auto-decompose contiguous data into CVCycle segments
    if cycles are not provided.
    """
    if result.cycles or result.potential is None or result.current is None:
        return

    v_arr = get_quantity_array(result.potential, 'volt')
    i_arr = get_quantity_array(result.current, 'ampere')
    if v_arr is None or i_arr is None:
        return

    t_arr = get_quantity_array(result.time, 'second')
    j_arr = get_quantity_array(result.current_density, CD_UNIT)
    v_rhe = get_quantity_array(result.potential_vs_rhe, 'volt')

    # Case 1: Pre-existing cycle_index array matching data length
    if result.cycle_index is not None and len(result.cycle_index) == len(v_arr):
        c_indices = np.asarray(result.cycle_index)
        for c_val in np.unique(c_indices):
            cyc = create_cv_cycle(
                cycle_index=int(c_val),
                potential=v_arr,
                current=i_arr,
                time=t_arr,
                current_density=j_arr,
                potential_vs_rhe=v_rhe,
                selector=(c_indices == c_val),
            )
            result.cycles.append(cyc)

    # Case 2: Detect cycle vertices from turning points
    elif len(v_arr) > MIN_POINTS_FOR_CYCLE_SPLIT:
        diffs = np.diff(v_arr)
        signs = np.sign(diffs)
        signs = np.where(signs == 0, 1, signs)
        turning_points = np.where(np.diff(signs) != 0)[0] + 1

        cycle_breaks = [0]
        for i in range(1, len(turning_points), 2):
            cycle_breaks.append(turning_points[i])
        if cycle_breaks[-1] != len(v_arr):
            cycle_breaks.append(len(v_arr))

        cycle_index_arr = np.zeros(len(v_arr), dtype=int)
        for c_idx in range(len(cycle_breaks) - 1):
            start_i = cycle_breaks[c_idx]
            end_i = cycle_breaks[c_idx + 1]
            if end_i - start_i < MIN_CYCLE_LENGTH:
                continue

            cycle_num = len(result.cycles) + 1
            cycle_index_arr[start_i:end_i] = cycle_num
            cyc = create_cv_cycle(
                cycle_index=cycle_num,
                potential=v_arr,
                current=i_arr,
                time=t_arr,
                current_density=j_arr,
                potential_vs_rhe=v_rhe,
                selector=slice(start_i, end_i),
            )
            result.cycles.append(cyc)

        if result.cycle_index is None and len(result.cycles) > 0:
            result.cycle_index = cycle_index_arr

    # Case 3: Fallback single cycle
    else:
        cyc = create_cv_cycle(
            cycle_index=1,
            potential=v_arr,
            current=i_arr,
            time=t_arr,
            current_density=j_arr,
            potential_vs_rhe=v_rhe,
        )
        result.cycles.append(cyc)
        if result.cycle_index is None:
            result.cycle_index = np.ones(len(v_arr), dtype=int)


def populate_continuous_data_from_cycles(result: 'CVResult') -> None:
    """
    Concatenate cycle arrays to populate continuous fields on CVResult
    if not present.
    """
    if result.potential is not None or not result.cycles:
        return

    valid_cycles = [
        cyc
        for cyc in result.cycles
        if cyc.potential is not None and cyc.current is not None
    ]
    if not valid_cycles:
        return

    all_v = [get_quantity_array(cyc.potential, 'volt') for cyc in valid_cycles]
    all_i = [get_quantity_array(cyc.current, 'ampere') for cyc in valid_cycles]
    all_idx = [
        np.full(len(v), cyc.cycle_index or 1, dtype=int)
        for cyc, v in zip(valid_cycles, all_v)
        if v is not None
    ]

    if all_v and all(v is not None for v in all_v):
        result.potential = np.concatenate(all_v) * ureg.volt
        result.current = np.concatenate(all_i) * ureg.ampere
        if result.cycle_index is None:
            result.cycle_index = np.concatenate(all_idx)

        if all(cyc.time is not None for cyc in valid_cycles):
            all_t = [get_quantity_array(cyc.time, 'second') for cyc in valid_cycles]
            if all(t is not None for t in all_t):
                result.time = np.concatenate(all_t) * ureg.second

        if all(cyc.current_density is not None for cyc in valid_cycles):
            all_j = [
                get_quantity_array(cyc.current_density, CD_UNIT) for cyc in valid_cycles
            ]
            if all(j is not None for j in all_j):
                result.current_density = np.concatenate(all_j) * (
                    ureg.milliampere / (ureg.centimeter**2)
                )

        if all(cyc.potential_vs_rhe is not None for cyc in valid_cycles):
            all_rhe = [
                get_quantity_array(cyc.potential_vs_rhe, 'volt') for cyc in valid_cycles
            ]
            if all(r is not None for r in all_rhe):
                result.potential_vs_rhe = np.concatenate(all_rhe) * ureg.volt


def calculate_cv_scan_rate(  # noqa: PLR2004
    potential: Any, time: Any
) -> float | None:
    """
    Calculate the cyclic voltammetry scan rate (in V/s) from potential and time
    by evaluating the total voltage range traversed (accounting for back-and-forth
    sweeps) divided by the total time.
    Returns None if it is not possible to calculate.
    """
    MIN_PNT = 2
    v_arr = get_quantity_array(potential, 'volt')
    t_arr = get_quantity_array(time, 'second')

    if v_arr is None or t_arr is None:
        return None

    if len(v_arr) < MIN_PNT or len(t_arr) < MIN_PNT or len(v_arr) != len(t_arr):
        return None

    finite_mask = np.isfinite(v_arr) & np.isfinite(t_arr)
    if np.sum(finite_mask) < MIN_PNT:
        return None

    v_arr = v_arr[finite_mask]
    t_arr = t_arr[finite_mask]

    dt = np.diff(t_arr)
    positive_dt = dt[dt > 0]
    if len(positive_dt) == 0:
        return None

    total_time = float(np.sum(positive_dt))
    total_voltage = float(np.sum(np.abs(np.diff(v_arr))))

    if total_time <= 0 or total_voltage <= 0:
        return None

    return total_voltage / total_time


def normalize_cv_result(
    result: 'CVResult',
    cell: Any = None,
    surface_area_val: float | None = None,
    ref_potential_rhe: float | None = None,
    ph_val: float | None = None,
) -> None:
    """
    Normalize a single CVResult: continuous current density, RHE conversion,
    cycle decomposition, continuous array population, scan rate calculation,
    and Plotly figures for CVResult and CVCycle.
    """
    has_area = (surface_area_val is not None) or (
        cell is not None and getattr(cell, 'surface_area', None) is not None
    )

    # 1. Normalize continuous signals on CVResult
    normalize_measurement_signals(
        result,
        cell=cell,
        surface_area=surface_area_val,
        ref_potential_vs_rhe=ref_potential_rhe,
        ph_value=ph_val,
    )

    # 2. Auto-decompose continuous data into CVCycle segments if not provided
    auto_decompose_cycles(result)

    # 3. Normalize individual cycles in CVCycle
    if result.cycles:
        for cyc in result.cycles:
            normalize_measurement_signals(
                cyc,
                cell=cell,
                surface_area=surface_area_val,
                ref_potential_vs_rhe=ref_potential_rhe,
                ph_value=ph_val,
            )

    # 4. Populate continuous arrays on CVResult from cycles if not present
    populate_continuous_data_from_cycles(result)

    # 5. Calculate scan rate from data if possible; leave empty if not possible
    calc_sr = calculate_cv_scan_rate(result.potential, result.time)
    if calc_sr is not None:
        result.scan_rate = calc_sr * (ureg.volt / ureg.second)

    # 6. Generate Plotly figures for CVResult
    result.figures = generate_cv_plotly_figures(result, use_density=has_area)


def normalize_cyclic_voltammetry(
    cv: 'CyclicVoltammetry',
    archive: 'EntryArchive' = None,
    logger: 'BoundLogger' = None,
) -> None:
    """Extract cell parameters and normalize all CV results."""
    if getattr(cv, 'cell', None) is not None:
        normalize_three_electrode_cell(cv.cell, archive, logger)

    for result in getattr(cv, 'results', None) or []:
        normalize_cv_result(result, cell=cv.cell)
