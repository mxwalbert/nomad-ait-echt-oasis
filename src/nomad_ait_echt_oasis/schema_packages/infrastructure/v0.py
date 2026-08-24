from collections.abc import Callable
from inspect import signature

import numpy as np
from nomad.datamodel.data import (
    Category,
    EntryData,
    EntryDataCategory,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections.v1 import (
    Entity,
    EntityReference,
    Instrument,
    InstrumentReference,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad.metainfo.data_type import (
    Datetime,
)
from scipy.optimize import curve_fit

m_package = SchemaPackage(
    name='AIT ECHT Infrastructure',
    aliases=['nomad_ait_echt_oasis.schema_packages.infrastructure'],
)


class LIMSDeviceCategory(EntryDataCategory):
    """
    Category for entry schemas related to devices
    for laboratory inventory management.
    """

    m_def = Category(
        label='LIMS Devices',
        categories=[EntryDataCategory],
    )


class LIMSDevice(Entity, EntryData):
    """
    A device that is registered in the laboratory inventory management.

    Inherited from `BaseSection`:
        name (str)
        datetime (Datetime)
        lab_id (str)
        description (str)

    Own properties:
        vendor (str)
        model (str)
        serial (str)
        activation_date (Datetime)
        device_type (str)
    """

    m_def = Section(
        categories=[LIMSDeviceCategory],
    )

    vendor = Quantity(
        type=str,
        description="""
        The manufacturer or seller of the device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Vendor Name',
        ),
    )
    model = Quantity(
        type=str,
        description="""
        The specific product name of the device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Model Name',
        ),
    )
    serial = Quantity(
        type=str,
        description="""
        The unique identification code of the device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Serial Number',
        ),
    )
    activation_date = Quantity(
        type=Datetime,
        description="""
        The day when the device was started to be used.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.DateTimeEditQuantity,
            label='Activation Date',
        ),
    )
    device_type = Quantity(
        type=str,
        description="""
        The type of device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Device Type',
        ),
    )

    def normalize(self, archive, logger) -> None:
        """
        Fills the device_type property if empty or
        if the entry is a subclass of LIMSDevice.
        """

        super().normalize(archive, logger)

        if self.device_type is None or type(self) is not LIMSDevice:
            self.device_type = self.__class__.__name__


class LIMSDeviceReference(EntityReference):
    """
    A section used for referencing a LIMSDevice.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (LIMSDevice)
    """

    reference = Quantity(
        type=LIMSDevice,
        description="""
        A reference to a `LIMSDevice` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='LIMSDevice reference',
        ),
    )


class LIMSCalibrationCategory(EntryDataCategory):
    """
    Category for entry schemas related to calibrations
    for laboratory inventory management.
    """

    m_def = Category(
        label='LIMS Calibrations',
        categories=[EntryDataCategory],
    )


class LIMSCalibration(Entity, EntryData):
    """
    A calibration that is registered in the laboratory inventory management.

    Inherited from `BaseSection`:
        name (str)
        datetime (Datetime)
        lab_id (str)
        description (str)

    Own properties:
        input_values (np.ndarray[float])
        output_values (np.ndarray[float])
        model_coefficients (np.ndarray[float])
        model_type (str)
    """

    m_def = Section(
        categories=[LIMSCalibrationCategory],
    )

    input_values = Quantity(
        type=float,
        shape=['*'],
        description="""
        The input values for the calibration.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Input values',
        ),
    )
    output_values = Quantity(
        type=float,
        shape=['*'],
        description="""
        The output values for the calibration.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Output values',
        ),
    )
    model_coefficients = Quantity(
        type=float,
        shape=['*'],
        description="""
        The coefficients for the calibration model.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Model coefficients',
        ),
    )
    model_type = Quantity(
        type=MEnum(
            'zero-intercept linear',
            'linear',
            'quadratic',
            'logarithmic',
            'exponential',
            'power law',
        ),
        shape=[],
        default='zero-intercept linear',
        description="""
        The model function of the calibration.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Model function',
        ),
    )

    def _raw_model(self) -> Callable[[np.ndarray, ...], np.ndarray]:
        """
        Returns the raw model function based on `model_type`.
        """

        return {
            'zero-intercept linear': lambda x, a: a * x,
            'linear': lambda x, a, b: a * x + b,
            'quadratic': lambda x, a, b, c: a * x**2 + b * x + c,
            'logarithmic': lambda x, a, b: a * np.log(x) + b,
            'exponential': lambda x, a, b: a * np.exp(b * x),
            'power law': lambda x, a, b: a * x**b,
        }[self.model_type]

    def _num_params(self) -> int:
        """
        Returns the number of parameters for the selected model function.
        """
        return len(signature(self._raw_model()).parameters) - 1

    def get_model(self, logger) -> Callable[[np.ndarray], np.ndarray]:
        """
        Returns a callable function that can be used to
        convert raw values into calibrated values.
        """

        if (
            self.model_coefficients is None
            or len(self.model_coefficients) != self._num_params()
        ):
            logger.warning(
                """
                Model coefficients are missing or invalid.
                Returning identity model.
                """
            )
            return lambda x: x

        return lambda x: self._raw_model()(x, *self.model_coefficients)

    def normalize(self, archive, logger) -> None:
        """
        Fills the model coefficients if empty
        and if input/output values are present.
        """

        super().normalize(archive, logger)

        if (
            self.input_values is None
            or self.output_values is None
            or self.model_coefficients is not None
        ):
            return

        x = np.asarray(self.input_values, dtype=float)
        y = np.asarray(self.output_values, dtype=float)

        if len(x) != len(y):
            logger.warning(
                """
                Input and output values must have the same length.
                Skipped coefficient calculation.
                """
            )
            return

        if len(x) < self._num_params():
            logger.warning(
                """
                Cannot determine coefficients from insufficient data.
                Consider a different model type or provide more data.
                Skipped coefficient calculation.
                """
            )
            return

        try:
            model = self._raw_model()

            # Domain checks for special models
            if self.model_type in ['zero-intercept linear', 'logarithmic', 'power law']:
                if np.any(x <= 0):
                    logger.warning(
                        """
                        Selected model type requires x > 0.
                        Skipped coefficient calculation.
                        """
                    )
                    return

            # Simple generic initial guess
            p0 = np.ones(self._num_params())

            coefficients, _ = curve_fit(
                model,
                x,
                y,
                p0=p0,
                maxfev=10000,
            )

            self.model_coefficients = coefficients

        except Exception as exc:
            logger.warning(f'Failed to fit calibration model: {exc}')


class LIMSCalibrationReference(EntityReference):
    """
    A section used for referencing a LIMSCalibration.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (LIMSCalibration)
    """

    reference = Quantity(
        type=LIMSCalibration,
        description="""
        A reference to a `LIMSCalibration` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='LIMSCalibration reference',
        ),
    )


class LIMSInstrument(Instrument, LIMSDevice):
    """
    An instrument that is registered in the laboratory inventory management.
    The instrument can be a standalone device or contain other devices.

    Inherited from `BaseSection`:
        name (str)
        datetime (Datetime)
        lab_id (str)
        description (str)

    Inherited from `LIMSDevice`:
        vendor (str)
        model (str)
        serial (str)
        activation_date (Datetime)
        device_type (str)

    Own properties:
        sub_devices (list[LIMSDeviceReference])
        calibrations (list[LIMSCalibrationReference])
    """

    sub_devices = SubSection(
        section_def=LIMSDeviceReference,
        repeats=True,
        description="""
        A list of references to `LIMSDevice` entries that are 
        part of this instrument.
        """,
    )
    calibrations = SubSection(
        section_def=LIMSCalibrationReference,
        repeats=True,
        description="""
        A list of references to `LIMSCalibration` entries that are 
        associated with this instrument.
        """,
    )


class LIMSInstrumentReference(InstrumentReference):
    """
    A section used for referencing a LIMSInstrument.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (LIMSInstrument)
    """

    reference = Quantity(
        type=LIMSInstrument,
        description="""
        A reference to a `LIMSInstrument` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='LIMSInstrument reference',
        ),
    )


class LIMSConsumableCategory(EntryDataCategory):
    """
    Category for entry schemas related to consumables
    for laboratory inventory management.
    """

    m_def = Category(
        label='LIMS Consumables',
        categories=[EntryDataCategory],
    )


class LIMSConsumable(Entity, EntryData):
    """
    A consumable that is registered in the laboratory inventory management.

    Inherited from `BaseSection`:
        name (str)
        datetime (Datetime)
        lab_id (str)
        description (str)

    Own properties:
        vendor (str)
        batch_number (str)
        stock_date (Datetime)
        item_type (str)
    """

    m_def = Section(
        categories=[LIMSConsumableCategory],
    )

    vendor = Quantity(
        type=str,
        description="""
        The manufacturer or seller of the consumable.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    batch_number = Quantity(
        type=str,
        description="""
        The unique identification code of the manufacturing lot.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    stock_date = Quantity(
        type=Datetime,
        description="""
        The day when the consumable was put into stock.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.DateTimeEditQuantity,
        ),
    )
    item_type = Quantity(
        type=str,
        description="""
        The type of consumable.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )

    def normalize(self, archive, logger) -> None:
        """
        Fills the item_type property if empty or
        if the entry is a subclass of LIMSConsumable.
        """

        super().normalize(archive, logger)

        if self.item_type is None or type(self) is not LIMSConsumable:
            self.item_type = self.__class__.__name__


class LIMSConsumableReference(EntityReference):
    """
    A section used for referencing a LIMSConsumable.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (LIMSConsumable)
    """

    reference = Quantity(
        type=LIMSConsumable,
        description="""
        A reference to a `LIMSConsumable` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='LIMSConsumable reference',
        ),
    )


m_package.__init_metainfo__()
