import numpy as np
import pytest
from nomad.units import ureg

from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cell import (
    normalize_reference_electrode,
    normalize_three_electrode_cell,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cv import (
    generate_cv_plotly_figures,
    auto_decompose_cycles,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.ecsa import (
    extract_capacitive_current,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.result import (
    normalize_measurement_signals,
)
from nomad_ait_echt_oasis.normalizers.utils import (
    build_scatter_trace,
    get_quantity_array,
    get_quantity_scalar,
)
from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
    CVCycle,
    CVResult,
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
