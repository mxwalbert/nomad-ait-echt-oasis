import numpy as np
import pytest

from nomad_ait_echt_oasis.schema_packages.infrastructure.v0 import (
    LIMSCalibration,
    LIMSCalibrationReference,
    LIMSConsumable,
    LIMSDevice,
    LIMSInstrument,
)


def test_lims_components(archive):
    lims_device = LIMSDevice(name='device')
    lims_instrument = LIMSInstrument(name='instrument')
    lims_consumable = LIMSConsumable(name='consumable')
    lims_apple = LIMSConsumable(name='apple', item_type='fruit')

    for li in [lims_device, lims_instrument, lims_consumable, lims_apple]:
        li.normalize(archive, None)

    assert lims_device.device_type == 'LIMSDevice'
    assert lims_instrument.device_type == 'LIMSInstrument'
    assert lims_consumable.item_type == 'LIMSConsumable'
    assert lims_apple.item_type == 'fruit'


def test_lims_calibration_fit_and_evaluation(archive):
    """Test curve fitting, coefficient resolution, and model evaluation for LIMSCalibration."""
    # Test linear model fitting (y = 2x + 1)
    calib = LIMSCalibration(
        name='Linear Calibration',
        model_type='linear',
        input_values=[1.0, 2.0, 3.0, 4.0],
        output_values=[3.0, 5.0, 7.0, 9.0],
    )
    calib.normalize(archive, None)

    assert calib.model_coefficients is not None
    assert len(calib.model_coefficients) == 2
    assert calib.model_coefficients[0] == pytest.approx(2.0, rel=1e-3)
    assert calib.model_coefficients[1] == pytest.approx(1.0, rel=1e-3)

    # Evaluate fitted model
    model_func = calib.get_model(logger=None)
    assert model_func(10.0) == pytest.approx(21.0, rel=1e-3)
    np.testing.assert_allclose(model_func(np.array([0.0, 5.0])), [1.0, 11.0], rtol=1e-3)

    # Test fallback to identity model when coefficients are missing/invalid
    unfit_calib = LIMSCalibration(name='Unfit Calibration', model_type='linear')

    class MockLogger:
        def __init__(self):
            self.warnings = []

        def warning(self, msg):
            self.warnings.append(msg)

    logger = MockLogger()
    identity_func = unfit_calib.get_model(logger=logger)
    assert len(logger.warnings) == 1
    assert identity_func(42.0) == 42.0

    # Test LIMSCalibrationReference
    ref = LIMSCalibrationReference(reference=calib, name='Linear Calibration Ref')
    assert ref.reference == calib


def test_lims_calibration_edge_cases(archive):
    """Test validation edge cases and warnings in LIMSCalibration normalization."""

    class MockLogger:
        def __init__(self):
            self.warnings = []

        def warning(self, msg):
            self.warnings.append(msg)

    # Case 1: Mismatched lengths of input and output values
    logger1 = MockLogger()
    calib_mismatch = LIMSCalibration(
        model_type='linear',
        input_values=[1.0, 2.0],
        output_values=[1.0],
    )
    calib_mismatch.normalize(archive, logger1)
    assert calib_mismatch.model_coefficients is None
    assert any('same length' in w for w in logger1.warnings)

    # Case 2: Insufficient data points for chosen model (quadratic requires 3 points)
    logger2 = MockLogger()
    calib_insufficient = LIMSCalibration(
        model_type='quadratic',
        input_values=[1.0, 2.0],
        output_values=[1.0, 4.0],
    )
    calib_insufficient.normalize(archive, logger2)
    assert calib_insufficient.model_coefficients is None
    assert any('insufficient data' in w for w in logger2.warnings)

    # Case 3: Domain restriction violation (x <= 0 for zero-intercept linear, logarithmic, power law)
    logger3 = MockLogger()
    calib_domain = LIMSCalibration(
        model_type='logarithmic',
        input_values=[-1.0, 2.0],
        output_values=[0.0, 1.0],
    )
    calib_domain.normalize(archive, logger3)
    assert calib_domain.model_coefficients is None
    assert any('requires x > 0' in w for w in logger3.warnings)

    # Case 4: Pre-existing coefficients are preserved without refitting
    calib_preset = LIMSCalibration(
        model_type='linear',
        input_values=[1.0, 2.0],
        output_values=[10.0, 20.0],
        model_coefficients=[5.0, 0.0],
    )
    calib_preset.normalize(archive, None)
    assert list(calib_preset.model_coefficients) == [5.0, 0.0]
