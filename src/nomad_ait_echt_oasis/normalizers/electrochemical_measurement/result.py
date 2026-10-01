from typing import Any

from nomad.units import ureg

from nomad_ait_echt_oasis.normalizers.utils import (
    get_quantity_array,
    get_quantity_scalar,
)

CD_UNIT = 'milliampere / centimeter ** 2'
C_UNIT = 'milliampere'


def normalize_measurement_signals(
    result: Any,
    cell: Any = None,
    surface_area: float | None = None,
    ref_potential_vs_rhe: float | None = None,
    ph_value: float | None = None,
) -> None:
    """
    Compute current_density and potential_vs_rhe on any section inheriting
    from ElectrochemicalMeasurementResult (e.g. CVResult, CVCycle).
    Parameters can be passed explicitly or retrieved from a cell section.
    """
    if result is None:
        return

    # Extract cell parameters if cell is provided
    if cell is not None:
        if surface_area is None:
            surface_area = get_quantity_scalar(
                getattr(cell, 'surface_area', None), 'centimeter ** 2'
            )
        if ref_potential_vs_rhe is None:
            ref_potential_vs_rhe = get_quantity_scalar(
                getattr(cell, 'reference_potential_vs_rhe', None), 'volt'
            )
        if ph_value is None and getattr(cell, 'ph_value', None) is not None:
            ph_value = float(cell.ph_value)

    # 1. Current density J = (I / A) * 1000 mA/cm²
    if (
        surface_area is not None
        and surface_area > 0
        and getattr(result, 'current', None) is not None
        and getattr(result, 'current_density', None) is None
    ):
        i_arr = get_quantity_array(result.current, 'ampere')
        if i_arr is not None:
            result.current_density = ((i_arr / surface_area) * 1000.0) * (
                ureg.milliampere / (ureg.centimeter**2)
            )

    # 2. Potential vs RHE: E_RHE = E + E_ref + 0.05916 * pH
    if (
        ref_potential_vs_rhe is not None
        and ph_value is not None
        and getattr(result, 'potential', None) is not None
        and getattr(result, 'potential_vs_rhe', None) is None
    ):
        v_arr = get_quantity_array(result.potential, 'volt')
        if v_arr is not None:
            result.potential_vs_rhe = (
                v_arr + ref_potential_vs_rhe + (0.05916 * ph_value)
            ) * ureg.volt
