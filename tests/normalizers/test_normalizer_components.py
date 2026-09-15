import numpy as np
import pytest
from nomad.units import ureg

from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cell import (
    normalize_reference_electrode,
    normalize_three_electrode_cell,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cv import (
    auto_decompose_cycles,
    generate_cv_plotly_figures,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.ecsa import (
    evaluate_run_capacitance,
    extract_anodic_cathodic_arcs,
    extract_capacitive_current,
    filter_arc_window,
    normalize_ecsa_result,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.result import (
    normalize_measurement_signals,
)
from nomad_ait_echt_oasis.normalizers.utils import (
    build_scatter_trace,
    get_quantity_array,
    get_quantity_scalar,
    parse_cycle_slice,
)
from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
    CVCycle,
    CVParameter,
    CVResult,
    ECSAResult,
    Electrolyte,
    ReferenceElectrode,
    ThreeElectrodeCell,
    WorkingElectrode,
)


def test_utils_quantity_extractors():
    """Test get_quantity_array and get_quantity_scalar helpers."""
    assert get_quantity_array(None) is None
    assert get_quantity_scalar(None) is None

    qty_arr = np.array([1.0, 2.0, 3.0]) * ureg.volt
    extracted_arr = get_quantity_array(qty_arr, 'millivolt')
    assert extracted_arr is not None
    assert np.allclose(extracted_arr, [1000.0, 2000.0, 3000.0])

    qty_scalar = 0.5 * (ureg.centimeter**2)
    extracted_scalar = get_quantity_scalar(qty_scalar, 'centimeter ** 2')
    assert extracted_scalar == pytest.approx(0.5)

    # Empty array handling
    empty_arr = np.array([]) * ureg.second
    assert get_quantity_array(empty_arr) is None


def test_utils_build_scatter_trace():
    """Test build_scatter_trace helper."""
    x = np.array([0.0, 1.0])
    y = np.array([2.0, 3.0])
    trace = build_scatter_trace(x, y, name='Test Trace', yaxis='y2')
    assert trace.name == 'Test Trace'
    assert trace.yaxis == 'y2'
    assert np.array_equal(trace.x, x)
    assert np.array_equal(trace.y, y)


def test_cell_normalizer():
    """Test ThreeElectrodeCell normalization and property flattening."""
    
    # Smoke tests
    normalize_reference_electrode(None)
    normalize_three_electrode_cell(None)

    # Basic test
    re = ReferenceElectrode(reference_type='Ag/AgCl (sat. KCl)')
    normalize_reference_electrode(re)
    assert re.standard_potential_vs_rhe is not None
    assert re.standard_potential_vs_rhe.to('volt').magnitude == pytest.approx(0.197)

    we = WorkingElectrode(surface_area=0.25 * (ureg.centimeter**2))
    elyte = Electrolyte(ph_value=1.5)
    cell = ThreeElectrodeCell(
        working_electrode=we,
        reference_electrode=re,
        electrolyte=elyte,
    )

    normalize_three_electrode_cell(cell)

    # Verify properties flattened to cell level
    assert cell.surface_area is not None
    assert cell.surface_area.to('centimeter ** 2').magnitude == pytest.approx(0.25)
    assert cell.reference_potential_vs_rhe is not None
    assert cell.reference_potential_vs_rhe.to('volt').magnitude == pytest.approx(0.197)
    assert cell.ph_value == pytest.approx(1.5)


def test_cv_normalizer():
    """Test missing normalization edge cases of CV normalizer."""

    potential = np.array([0.0, 0.5, 1.0]) * ureg.volt
    current = np.array([0.001, 0.002, 0.003]) * ureg.ampere
    time = np.array([0.0, 1.0, 2.0]) * ureg.second

    # Test plotting empty CVResult
    generate_cv_plotly_figures(CVResult())

    # Test plotting result without cycles and without time
    res_no_cyc = CVResult(
        potential=potential,
        current=current
    )
    generate_cv_plotly_figures(res_no_cyc)

    # Test plotting result with cycle
    cyc = CVCycle(
        cycle_index=0,
        potential=potential,
        current=current,
        time=time
    )
    generate_cv_plotly_figures(CVResult(cycles=[cyc]))

    # Test decomposition of empty CVResult
    res_empty = CVResult(
        potential=np.array([]) * ureg.volt,
        current=np.array([]) * ureg.ampere
    )
    auto_decompose_cycles(res_empty)

    # Test decomposition of indexed data
    res_indexed = CVResult(
        cycle_index=np.array([1, 1, 1]),
        potential=potential,
        current=current
    )
    auto_decompose_cycles(res_indexed)

    # Test decomposition of too short data
    auto_decompose_cycles(res_no_cyc)

    # Test multi-cycle splitting: 10 full cycles (0.0 -> 1.0 -> -1.0 -> 0.0)
    # A single cycle consists of 40 points: 0.0 -> 1.0 (10 pts), 1.0 -> -1.0 (20 pts), -1.0 -> 0.0 (10 pts)
    one_cycle = np.concatenate([
        np.linspace(0.0, 1.0, 10, endpoint=False),
        np.linspace(1.0, -1.0, 20, endpoint=False),
        np.linspace(-1.0, 0.0, 10, endpoint=False),
    ])
    ten_cycles_v = np.tile(one_cycle, 10)
    ten_cycles_v = np.append(ten_cycles_v, 0.0)  # final point
    ten_cycles_i = np.ones_like(ten_cycles_v) * 0.001

    # Case A: Auto-detected v_start and v_end
    res_multi_auto = CVResult(
        potential=ten_cycles_v * ureg.volt,
        current=ten_cycles_i * ureg.ampere,
    )
    auto_decompose_cycles(res_multi_auto)
    assert len(res_multi_auto.cycles) == 10, f'Expected 10 cycles, got {len(res_multi_auto.cycles)}'
    for idx, cyc in enumerate(res_multi_auto.cycles, start=1):
        assert cyc.cycle_index == idx

    # Case B: Explicit CVParameter specifying initial_potential and final_potential
    res_multi_param = CVResult(
        potential=ten_cycles_v * ureg.volt,
        current=ten_cycles_i * ureg.ampere,
    )
    params = CVParameter(
        initial_potential=0.0 * ureg.volt,
        final_potential=0.0 * ureg.volt,
    )
    auto_decompose_cycles(res_multi_param, parameters=params)
    assert len(res_multi_param.cycles) == 10, f'Expected 10 cycles, got {len(res_multi_param.cycles)}'

    # Case C: Extremum cycle boundary (-1.0 -> 1.0 -> -1.0)
    one_cycle_ext = np.concatenate([
        np.linspace(-1.0, 1.0, 20, endpoint=False),
        np.linspace(1.0, -1.0, 20, endpoint=False),
    ])
    three_cycles_v = np.tile(one_cycle_ext, 3)
    three_cycles_v = np.append(three_cycles_v, -1.0)
    three_cycles_i = np.ones_like(three_cycles_v) * 0.001

    res_ext = CVResult(
        potential=three_cycles_v * ureg.volt,
        current=three_cycles_i * ureg.ampere,
    )
    auto_decompose_cycles(res_ext)
    assert len(res_ext.cycles) == 3, f'Expected 3 cycles, got {len(res_ext.cycles)}'


def test_result_signal_normalizer():
    """Test normalize_measurement_signals on CVResult and CVCycle."""
    cell = ThreeElectrodeCell(
        surface_area=0.5 * (ureg.centimeter**2),
        reference_potential_vs_rhe=0.200 * ureg.volt,
        ph_value=1.0,
    )

    v_raw = np.array([0.0, 0.5, 1.0])
    i_raw = np.array([0.001, 0.002, 0.003])

    res = CVResult(
        potential=v_raw * ureg.volt,
        current=i_raw * ureg.ampere,
    )

    normalize_measurement_signals(res, cell=cell)

    # Current density: J = I / Area * 1000 = (0.001 / 0.5) * 1000 = 2.0 mA/cm²
    assert res.current_density is not None
    j_vals = res.current_density.to('milliampere / centimeter ** 2').magnitude
    assert np.allclose(j_vals, [2.0, 4.0, 6.0])

    # Potential vs RHE: E_RHE = E + 0.200 + 0.05916 * 1.0 = E + 0.25916 V
    assert res.potential_vs_rhe is not None
    v_rhe_vals = res.potential_vs_rhe.to('volt').magnitude
    assert np.allclose(v_rhe_vals, v_raw + 0.200 + 0.05916 * 1.0)


def test_extract_capacitive_current():
    """Test pure numerical capacitive current extraction."""
    # Symmetrical capacitive loop: 0.1 to 0.3 V
    v_fwd = np.linspace(0.1, 0.3, 20)
    v_rev = np.linspace(0.3, 0.1, 20)
    v_arr = np.concatenate([v_fwd, v_rev])

    # 1 mA forward, -1 mA reverse -> midpoint charging current = |1 - (-1)| / 2 = 1 mA
    i_fwd = np.full(20, 0.001)
    i_rev = np.full(20, -0.001)
    i_arr = np.concatenate([i_fwd, i_rev])

    i_cap = extract_capacitive_current(v_arr, i_arr)
    assert i_cap is not None
    assert i_cap == pytest.approx(0.001, rel=1e-3)


def test_parse_cycle_slice():
    """Test Python slice string parsing helper."""
    assert parse_cycle_slice(None) == slice(None)
    assert parse_cycle_slice('') == slice(None)
    assert parse_cycle_slice('invalid') == slice(None)
    assert parse_cycle_slice('2:6') == slice(2, 6)
    assert parse_cycle_slice('1:') == slice(1, None)
    assert parse_cycle_slice(':-1') == slice(None, -1)
    assert parse_cycle_slice('0:10:2') == slice(0, 10, 2)


def test_extract_anodic_cathodic_arcs():
    """Test separating CV cycle into anodic and cathodic arcs."""
    # Symmetrical triangular cycle: 0.0 -> 1.0 -> 0.0
    v_arr = np.array([0.0, 0.5, 1.0, 1.0, 0.5, 0.0])
    i_arr = np.array([0.001, 0.001, 0.0, 0.0, -0.001, -0.001])

    v_anod, i_anod, v_cath, i_cath = extract_anodic_cathodic_arcs(v_arr, i_arr)
    assert len(v_anod) > 0
    assert len(v_cath) > 0
    # Anodic arc should have potential increasing from min to max
    assert v_anod[0] == 0.0
    assert v_anod[-1] == 1.0
    # Cathodic arc should have potential decreasing from max to min
    assert v_cath[0] == 1.0
    assert v_cath[-1] == 0.0


def test_filter_arc_window():
    """Test filtering arc data to centered potential window."""
    v_arc = np.linspace(0.0, 1.0, 11)  # 0.0, 0.1, ..., 1.0
    i_arc = np.full(11, 0.001)

    v_mid = 0.5
    v_span = 1.0

    # 50% width -> [0.25, 0.75]
    v_filt, i_filt = filter_arc_window(v_arc, i_arc, v_mid, v_span, width_fraction=0.5)
    assert np.all(v_filt >= 0.25)
    assert np.all(v_filt <= 0.75)
    assert len(v_filt) == 5  # 0.3, 0.4, 0.5, 0.6, 0.7


def test_evaluate_run_capacitance_and_overlay():
    """Test arc regression capacitance evaluation and Plotly figure overlay."""
    v_fwd = np.linspace(0.1, 0.5, 20)
    v_rev = np.linspace(0.5, 0.1, 20)
    v_arr = np.concatenate([v_fwd, v_rev])

    # Anodic: 2 mA (+ 0.1*v slope), Cathodic: -2 mA (+ 0.1*v slope)
    # At v_mid = 0.3V, delta_i = 4 mA, i_cap = 2 mA = 0.002 A
    i_fwd = 0.002 + 0.001 * v_fwd
    i_rev = -0.002 + 0.001 * v_rev
    i_arr = np.concatenate([i_fwd, i_rev])

    cyc1 = CVCycle(cycle_index=1, potential=v_arr * ureg.volt, current=i_arr * ureg.ampere)
    cyc2 = CVCycle(cycle_index=2, potential=v_arr * ureg.volt, current=i_arr * ureg.ampere)

    run = CVResult(cycles=[cyc1, cyc2], scan_rate=0.05 * (ureg.volt / ureg.second))
    run.figures = generate_cv_plotly_figures(run)

    i_cap = evaluate_run_capacitance(run, cycle_selection='-1:', width_fraction=0.5)
    assert i_cap is not None
    assert i_cap == pytest.approx(0.002, rel=1e-2)

    # Verify that Anodic Fit and Cathodic Fit lines were added to run.figures
    volt_fig = next(f for f in run.figures if f.label == 'Cyclic Voltammogram')
    trace_names = [t.get('name') for t in volt_fig.figure.get('data', [])]
    assert 'Anodic Fit' in trace_names
    assert 'Cathodic Fit' in trace_names

    # Verify that all trace data is serialized to Python lists (not np.ndarray) for msgpack
    for trace in volt_fig.figure.get('data', []):
        assert isinstance(trace.get('x'), list)
        assert isinstance(trace.get('y'), list)
        assert not isinstance(trace.get('x'), np.ndarray)
        assert not isinstance(trace.get('y'), np.ndarray)


def test_ecsa_result_arc_regression():
    """Test full ECSA normalization with arc regression and Cdl fit."""
    v_fwd = np.linspace(0.1, 0.5, 20)
    v_rev = np.linspace(0.5, 0.1, 20)
    v_arr = np.concatenate([v_fwd, v_rev])

    # Run 1: scan_rate = 0.02 V/s, delta_i = 2 mA -> i_cap = 1 mA = 0.001 A
    run1 = CVResult(
        cycles=[
            CVCycle(
                cycle_index=1,
                potential=v_arr * ureg.volt,
                current=np.concatenate([np.full(20, 0.001), np.full(20, -0.001)]) * ureg.ampere,
            )
        ],
        scan_rate=0.02 * (ureg.volt / ureg.second),
    )

    # Run 2: scan_rate = 0.05 V/s, delta_i = 5 mA -> i_cap = 2.5 mA = 0.0025 A
    run2 = CVResult(
        cycles=[
            CVCycle(
                cycle_index=1,
                potential=v_arr * ureg.volt,
                current=np.concatenate([np.full(20, 0.0025), np.full(20, -0.0025)]) * ureg.ampere,
            )
        ],
        scan_rate=0.05 * (ureg.volt / ureg.second),
    )

    ecsa_res = ECSAResult(runs=[run1, run2])

    normalize_ecsa_result(ecsa_res)

    assert ecsa_res.double_layer_capacitance is not None
    # Slope = (0.0025 - 0.001) / (0.05 - 0.02) = 0.0015 / 0.03 = 0.05 F = 50 mF
    cdl = ecsa_res.double_layer_capacitance.to('farad').magnitude
    assert cdl == pytest.approx(0.05, rel=1e-2)
