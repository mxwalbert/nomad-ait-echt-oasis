from typing import TYPE_CHECKING, Any

from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

STANDARD_REFERENCE_POTENTIALS_VS_RHE: dict[str, float] = {
    'Reversible Hydrogen Electrode (RHE)': 0.0,
    'Ag/AgCl (sat. KCl)': 0.197,
    'Ag/AgCl (3M KCl)': 0.210,
    'Ag/AgCl (1M KCl)': 0.236,
    'Saturated Calomel Electrode (SCE)': 0.241,
    'Mercury-Mercurous Sulfate (MSE, sat. K2SO4)': 0.640,
    'Mercury-Mercuric Oxide (Hg/HgO, 1M KOH)': 0.098,
}


def normalize_reference_electrode(ref: Any) -> None:
    """Fill standard reduction potential vs RHE if known and not set."""
    if ref is None:
        return
    if (
        ref.standard_potential_vs_rhe is None
        and getattr(ref, 'reference_type', None) in STANDARD_REFERENCE_POTENTIALS_VS_RHE
    ):
        ref.standard_potential_vs_rhe = (
            STANDARD_REFERENCE_POTENTIALS_VS_RHE[ref.reference_type] * ureg.volt
        )


def _sync_reference_electrode(cell: Any, re: Any) -> None:
    """Synchronize reference electrode standard potential with cell field."""
    normalize_reference_electrode(re)
    if re.standard_potential_vs_rhe is not None:
        if getattr(cell, 'reference_potential_vs_rhe', None) is None:
            cell.reference_potential_vs_rhe = re.standard_potential_vs_rhe


def _sync_working_electrode(cell: Any, we: Any) -> None:
    """Synchronize working electrode surface area with cell field."""
    if we.surface_area is not None:
        if getattr(cell, 'surface_area', None) is None:
            cell.surface_area = we.surface_area


def _sync_electrolyte(cell: Any, elyte: Any) -> None:
    """Synchronize electrolyte pH with cell field."""
    if getattr(elyte, 'ph_value', None) is not None:
        if getattr(cell, 'ph_value', None) is None:
            cell.ph_value = float(elyte.ph_value)


def normalize_three_electrode_cell(
    cell: Any,
    archive: 'EntryArchive' = None,
    logger: 'BoundLogger' = None,
) -> None:
    """
    Normalize ThreeElectrodeCell:
    1. Normalizes reference electrode standard potential vs RHE.
    2. Synchronizes surface_area, reference_potential_vs_rhe, and ph_value
       between nested components and flat cell quantities.
    """
    if cell is None:
        return

    re = getattr(cell, 'reference_electrode', None)
    if re is not None:
        _sync_reference_electrode(cell, re)

    we = getattr(cell, 'working_electrode', None)
    if we is not None:
        _sync_working_electrode(cell, we)

    elyte = getattr(cell, 'electrolyte', None)
    if elyte is not None:
        _sync_electrolyte(cell, elyte)
