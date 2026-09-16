from typing import TYPE_CHECKING

import numpy as np
from nomad.units import ureg
from nomad_measurements.mapping.schema import SampleAlignment

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
        ElectrochemicalMapping,
    )


DIM_COORDINATES = 2


def normalize_electrochemical_mapping(  # noqa PLR0912, PLR0915
    mapping: 'ElectrochemicalMapping',
    archive: 'EntryArchive' = None,
    logger: 'BoundLogger' = None,
) -> None:
    """
    Normalizer for ElectrochemicalMapping entries.

    1. Checks for SampleAlignment (and affine_transformation) to compute relative
       coordinates (x_relative, y_relative) for each mapping step from absolute
       stage coordinates (x_absolute, y_absolute).
    2. Sets descriptive names on steps if not already populated.
    3. Transforms any mapping results if present.
    """
    if mapping is None:
        return

    # Check sample alignment and transformation
    transform = None
    sample_alignment = getattr(mapping, 'sample_alignment', None)
    if isinstance(sample_alignment, SampleAlignment):
        # Ensure sample_alignment is normalized if not done yet
        if getattr(sample_alignment, 'affine_transformation', None) is None:
            if hasattr(sample_alignment, 'normalize'):
                try:
                    sample_alignment.normalize(archive, logger)
                except Exception as exc:
                    if logger:
                        logger.warning(f'Failed to normalize sample_alignment: {exc}')
        if sample_alignment.affine_transformation is not None and hasattr(
            sample_alignment.affine_transformation, 'transform_vector'
        ):
            transform = sample_alignment.affine_transformation.transform_vector

    # 1. Process mapping steps
    steps = getattr(mapping, 'steps', None) or []
    for step in steps:
        # Calculate relative coordinates if transform is available
        if (
            transform is not None
            and isinstance(getattr(step, 'x_absolute', None), ureg.Quantity)
            and isinstance(getattr(step, 'y_absolute', None), ureg.Quantity)
        ):
            try:
                x_m = step.x_absolute.to('m').magnitude
                y_m = step.y_absolute.to('m').magnitude
                rel_coords = transform(np.array([x_m, y_m]))
                if rel_coords is not None and len(rel_coords) == DIM_COORDINATES:
                    step.x_relative = rel_coords[0]
                    step.y_relative = rel_coords[1]
            except Exception as exc:
                if logger:
                    logger.warning(
                        f'Failed to compute relative coordinates for step: {exc}'
                    )

        # Set step name if empty
        if not getattr(step, 'name', None):
            technique = 'Measurement'
            measurement = getattr(step.measurement_ref, 'reference', None)
            if measurement is not None:
                technique = type(measurement).__name__

            if isinstance(
                getattr(step, 'x_relative', None), ureg.Quantity
            ) and isinstance(getattr(step, 'y_relative', None), ureg.Quantity):
                x_mm = step.x_relative.to('mm').magnitude
                y_mm = step.y_relative.to('mm').magnitude
                step.name = (
                    f'{technique} at sample x = {x_mm:.1f} mm, y = {y_mm:.1f} mm'
                )
            elif isinstance(
                getattr(step, 'x_absolute', None), ureg.Quantity
            ) and isinstance(getattr(step, 'y_absolute', None), ureg.Quantity):
                x_mm = step.x_absolute.to('mm').magnitude
                y_mm = step.y_absolute.to('mm').magnitude
                step.name = f'{technique} at stage x = {x_mm:.1f} mm, y = {y_mm:.1f} mm'
            else:
                step.name = technique

    # 2. Process mapping results (if present)
    results = getattr(mapping, 'results', None) or []
    for result in results:
        if (
            transform is not None
            and isinstance(getattr(result, 'x_absolute', None), ureg.Quantity)
            and isinstance(getattr(result, 'y_absolute', None), ureg.Quantity)
            and getattr(result, 'x_relative', None) is None
        ):
            try:
                x_m = result.x_absolute.to('m').magnitude
                y_m = result.y_absolute.to('m').magnitude
                rel_coords = transform(np.array([x_m, y_m]))
                if rel_coords is not None and len(rel_coords) == DIM_COORDINATES:
                    result.x_relative = rel_coords[0]
                    result.y_relative = rel_coords[1]
            except Exception as exc:
                if logger:
                    logger.warning(
                        f'Failed to compute relative coordinates for result: {exc}'
                    )
