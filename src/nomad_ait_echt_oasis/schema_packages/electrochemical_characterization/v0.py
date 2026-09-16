from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import (
    ArchiveSection,
    Category,
    EntryData,
    EntryDataCategory,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    ActivityStep,
    CompositeSystem,
    CompositeSystemReference,
    Measurement,
    MeasurementResult,
    SectionReference,
)
from nomad.datamodel.metainfo.plot import (
    PlotSection,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad_material_processing.solution.general import (
    Solution,
)
from nomad_measurements.mapping.schema import (
    MappingMeasurement,
    MappingResult,
)

from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cell import (
    normalize_reference_electrode,
    normalize_three_electrode_cell,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.cv import (
    normalize_cyclic_voltammetry,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.ecsa import (
    normalize_ecsa_measurement,
    normalize_ecsa_result,
)
from nomad_ait_echt_oasis.normalizers.electrochemical_characterization.mapping import (
    normalize_electrochemical_mapping,
)
from nomad_ait_echt_oasis.schema_packages.infrastructure import (
    LIMSInstrument,
    LIMSInstrumentReference,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

try:
    from nomad_measurements.general import (
        NOMADMeasurementsCategory,
    )
except ImportError:
    NOMADMeasurementsCategory = EntryDataCategory

m_package = SchemaPackage(
    name='AIT ECHT Electrochemical Characterization',
    aliases=['nomad_ait_echt_oasis.schema_packages.electrochemical_characterization'],
    description="""
    Schemas for the characterization of electrochemical systems.
    This package is based on NOMAD's Measurements and Material Processing plugins.
    The class structures are aligned with EMMO, including domain ontologies.

    Ontology Namespaces:
        emmo:  https://w3id.org/emmo#
        echem: https://w3id.org/emmo/domain/electrochemistry#
        chameo: https://w3id.org/emmo/domain/characterisation-methodology/chameo#
    """,
)

# --- Named Constants for Validation and Calculations ---
MIN_POINTS_FOR_CYCLE_SPLIT = 10
MIN_CYCLE_LENGTH = 4

# --- Constants for abbreviating long unit strings ---
CD_UNIT = 'milliampere / centimeter ** 2'
C_UNIT = 'milliampere'


# --- General sections ---
class MeasurementReference(SectionReference):
    """
    A section used for referencing a Measurement.
    """

    reference = Quantity(
        type=Measurement,
        description='A reference to a Measurement entry.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='Measurement reference',
        ),
    )


class MappingStep(ActivityStep):
    """
    A single measurement step at a defined stage/sample coordinate within a mapping run.
    """

    m_def = Section(
        description="""
        A single measurement step at a defined stage/sample coordinate 
        within a mapping run.
        """,
    )

    x_absolute = Quantity(
        type=np.float64,
        unit='m',
        description='Absolute x position of the measurement stage.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
    )

    y_absolute = Quantity(
        type=np.float64,
        unit='m',
        description='Absolute y position of the measurement stage.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
    )

    x_relative = Quantity(
        type=np.float64,
        unit='m',
        description='Relative x position on the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
    )

    y_relative = Quantity(
        type=np.float64,
        unit='m',
        description='Relative y position on the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
    )

    measurement_ref = SubSection(
        section_def=MeasurementReference,
        description="""
        Reference to the stand-alone measurement entry.
        """,
    )


# --- Categories ---
class ElectrochemicalMeasurementCategory(EntryDataCategory):
    """
    Category for electrochemical characterization measurements.
    """

    m_def = Category(
        label='Electrochemical Testing',
        categories=[EntryDataCategory, NOMADMeasurementsCategory],
    )


# --- Instruments ---
class Potentiostat(LIMSInstrument):
    """
    An electronic device that controls the potential difference between
    the working electrode and the reference electrode.

    Ontology:
        echem:Potentiostat
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_a9fc3f77_e48e_4bce_b118_044d608722f6)
    """

    m_def = Section(
        description="""
        A potentiostat instrument for controlling potential differences
        in electrochemical systems.
        """,
    )

    upper_voltage_limit = Quantity(
        type=float,
        unit='volt',
        description="""
        The maximum voltage that the potentiostat can apply across the counter
        and working electrodes.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='volt',
            label='Upper voltage limit',
        ),
    )

    upper_current_limit = Quantity(
        type=float,
        unit='ampere',
        description="""
        The maximum current output capacity of the potentiostat.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit=C_UNIT,
            label='Upper current limit',
        ),
    )


class PotentiostatReference(LIMSInstrumentReference):
    """
    A section used for referencing a Potentiostat.
    """

    reference = Quantity(
        type=Potentiostat,
        description="""
        A reference to a `Potentiostat` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='Potentiostat reference',
        ),
    )


class Galvanostat(LIMSInstrument):
    """
    An electronic device that controls the electric current between
    the working electrode and the auxiliary electrode.

    Ontology:
        echem:Galvanostat
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_22725105_c941_4b14_a4a2_fcb627958607)
    """

    m_def = Section(
        description="""
        A galvanostat instrument for controlling electric current.
        """,
    )

    upper_voltage_limit = Quantity(
        type=float,
        unit='volt',
        description="""
        The maximum voltage that the galvanostat can apply across the elctrodes.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='volt',
            label='Upper voltage limit',
        ),
    )

    upper_current_limit = Quantity(
        type=float,
        unit='ampere',
        description="""
        The maximum current output capacity of the galvanostat.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit=C_UNIT,
            label='Upper current limit',
        ),
    )


class GalvanostatReference(LIMSInstrumentReference):
    """
    A section used for referencing a Galvanostat.
    """

    reference = Quantity(
        type=Galvanostat,
        description="""
        A reference to a `Galvanostat` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='Galvanostat reference',
        ),
    )


class FrequencyResponseAnalyser(LIMSInstrument):
    """
    An electronic device that generates AC excitation signals and measures
    the frequency-dependent impedance response of an electrochemical system.

    Ontology:
        echem:FrequencyResponseAnalyser
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_279ecc9f_bfbc_4108_ae40_3c1c0f735e60)
    """

    m_def = Section(
        description="""
        A frequency response analyser for impedance spectroscopy.
        """,
    )

    lower_frequency_limit = Quantity(
        type=float,
        unit='hertz',
        description="""
        Minimum frequency that can be measured.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='millihertz',
            label='Lower frequency limit',
        ),
    )

    upper_frequency_limit = Quantity(
        type=float,
        unit='hertz',
        description="""
        Maximum frequency that can be measured.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='megahertz',
            label='Upper frequency limit',
        ),
    )


class FrequencyResponseAnalyserReference(LIMSInstrumentReference):
    """
    A section used for referencing a FrequencyResponseAnalyser.
    """

    reference = Quantity(
        type=FrequencyResponseAnalyser,
        description="""
        A reference to a `FrequencyResponseAnalyser` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='FrequencyResponseAnalyser reference',
        ),
    )


# --- Electrochemical Cell Components ---
class Electrolyte(Solution):
    """
    An ion-transport liquid phase containing dissolved salts, acids,
    or bases in a solvent. Inherits from `Solution` in
    `nomad_material_processing.solution.general`, preserving full solute,
    solvent, molar concentration, and PubChem substance integration.

    Ontology:
        echem:ElectrolyteSolution
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_fa22874b_76a9_4043_8b8f_6086c88746de)
    """

    m_def = Section(
        description="""
        An electrolyte solution used in an electrochemical cell.
        """,
    )

    ionic_conductivity = Quantity(
        type=float,
        unit='siemens / meter',
        description="""
        The measured ionic conductivity of the electrolyte solution.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='millisiemens / centimeter',
            label='Ionic conductivity',
        ),
    )


class Electrode(ArchiveSection):
    """
    Electron conductor in an electrochemical cell in contact with the electrolyte and
    connected to the external circuit.

    Ontology:
        echem:Electrode
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_0f007072_a8dd_4798_b865_1bf9363be627)
    """

    m_def = Section(
        description="""
        An electrode used in an electrochemical cell.
        """,
    )

    active_material = SubSection(
        section_def=CompositeSystem,
        description="""
        The composition of the active material of the electrode.
        """,
    )

    surface_area = Quantity(
        type=float,
        unit='centimeter ** 2',
        description="""
        The measured active surface area of the electrode
        in contact with the electrolyte.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='centimeter ** 2',
            label='Active surface area',
        ),
    )

    geometric_surface_area = Quantity(
        type=float,
        unit='centimeter ** 2',
        description="""
        The geometric surface area of the electrode
        in contact with the electrolyte.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='centimeter ** 2',
            label='Geometric surface area',
        ),
    )


class WorkingElectrode(Electrode):
    """
    The electrode in an electrochemical system at which the reaction of
    interest occurs. References a `CompositeSystem` (the physical sample or
    coated substrate being tested), ensuring full alignment with NOMAD's
    sample architecture and ECHO ontology.

    Ontology:
        echem:WorkingElectrode
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_fb988878_ee54_4350_9ee9_228c00c3ad35)
    """

    m_def = Section(
        description="""
        The working electrode used in the electrochemical cell.
        """,
    )

    sample = SubSection(
        section_def=CompositeSystemReference,
        description="""
        A reference to the physical sample mounted
        or acting as the working electrode.
        """,
    )


class ReferenceElectrode(Electrode):
    """
    An electrode with a stable, well-known electric potential used as a reference point
    for potential measurements in an electrochemical cell.

    Ontology:
        echem:ReferenceElectrode
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_7729c34e_1ae9_403d_b933_1765885e7f29)
    """

    m_def = Section(
        description="""
        The reference electrode used in the electrochemical cell.
        """,
    )

    reference_type = Quantity(
        type=MEnum(
            'Reversible Hydrogen Electrode (RHE)',
            'Ag/AgCl (sat. KCl)',
            'Ag/AgCl (3M KCl)',
            'Ag/AgCl (1M KCl)',
            'Saturated Calomel Electrode (SCE)',
            'Mercury-Mercurous Sulfate (MSE, sat. K2SO4)',
            'Mercury-Mercuric Oxide (Hg/HgO, 1M KOH)',
            'Other',
        ),
        default='Reversible Hydrogen Electrode (RHE)',
        description="""
        The specific type or chemistry of the reference electrode.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Reference electrode type',
        ),
    )

    standard_potential_vs_rhe = Quantity(
        type=float,
        unit='volt',
        description="""
        The standard reduction potential of this reference electrode relative
        to the Reversible Hydrogen Electrode (RHE).
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='volt',
            label='E° vs. RHE',
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        normalize_reference_electrode(self, archive, logger)


class CounterElectrode(Electrode):
    """
    An auxiliary electrode used in a three-electrode electrochemical cell to complete
    the current path with the Working Electrode without limiting the reaction rate.

    Ontology:
        echem:CounterElectrode
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_871bc4a4_2d17_4b88_9b0f_7ab85f14afea)
    """

    m_def = Section(
        description="""
        The counter (auxiliary) electrode used in the electrochemical cell.
        """,
    )

    geometry = Quantity(
        type=MEnum('Mesh', 'Wire', 'Foil', 'Rod', 'Ring', 'Foam', 'Other'),
        default='Mesh',
        description="""
        The geometric shape of the counter electrode.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Counter electrode geometry',
        ),
    )


class ElectrochemicalCell(ArchiveSection):
    """
    A system containing at least two electrodes in contact with an electrolyte,
    providing the physical and chemical environment for electrochemical reactions.

    Ontology:
        echem:ElectrochemicalCell
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_6f2c88c9_5c04_4953_a298_032cc3ab9b77)
    """

    m_def = Section(
        description="""
        The electrochemical cell configuration and components.
        """,
    )

    electrodes = SubSection(
        section_def=Electrode,
        repeats=True,
        description="""
        The electrodes composing the electrochemical cell.
        """,
    )

    electrolyte = SubSection(
        section_def=Electrolyte,
        description="""
        The electrolyte solution establishing ionic contact between electrodes.
        """,
    )


class ThreeElectrodeCell(ElectrochemicalCell):
    """
    An electrochemical cell that utilizes three electrodes to control and measure the
    electrochemical response of a system.

    Ontology:
        echem:ThreeElectrodeElectrochemicalCell
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_b9bece97_a511_4cb9_88a2_b5bd5c5e5d74)
    """

    m_def = Section(
        description="""
        The configuration and components of a three-electrode electrochemical cell.
        """,
    )

    working_electrode = SubSection(
        section_def=WorkingElectrode,
        description="""
        The working electrode where electrochemical reactions of interest occur.
        """,
    )

    reference_electrode = SubSection(
        section_def=ReferenceElectrode,
        description="""
        The reference electrode establishing the potential scale.
        """,
    )

    counter_electrode = SubSection(
        section_def=CounterElectrode,
        description="""
        The counter electrode completing the electrochemical circuit.
        """,
    )

    surface_area = Quantity(
        type=float,
        unit='centimeter ** 2',
        description="""
        Active geometric surface area of the working electrode.
        """,
    )

    reference_potential_vs_rhe = Quantity(
        type=float,
        unit='volt',
        description="""
        Standard potential of the reference electrode vs. RHE.
        """,
    )

    ph_value = Quantity(
        type=float,
        description="""
        Electrolyte pH value.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Normalize reference electrode and synchronize flattened cell properties."""
        super().normalize(archive, logger)
        normalize_three_electrode_cell(self, archive, logger)


# --- Electrochemical Measurement & Results ---
class MeasurementParameter(ArchiveSection):
    """
    Base section describing the input parameters of a generic measurement.

    Ontology:
        chameo:MeasurementParameter
        (https://w3id.org/emmo/domain/characterisation-methodology/chameo#MeasurementParameter)
    """

    m_def = Section(
        description="""
        Base parameters for a generic measurement.
        """,
    )


class ElectrochemicalMeasurementParameter(MeasurementParameter):
    """
    Base section describing the input parameters of an electrochemical measurement.
    """

    m_def = Section(
        description="""
        Base parameters for electrochemical measurements.
        """,
    )


class ElectrochemicalMeasurement(Measurement):
    """
    Base activity section for all electrochemical characterization measurements.
    Synchronizes the sample represented by the `WorkingElectrode` with
    NOMAD's `Measurement.samples`.

    Ontology:
        chameo:ElectrochemicalTesting
        (https://w3id.org/emmo/domain/characterisation-methodology/chameo#ElectrochemicalTesting)
    """

    m_def = Section(
        categories=[ElectrochemicalMeasurementCategory],
        description="""
        Base measurement for electrochemical characterization.
        """,
    )

    cell = SubSection(
        section_def=ThreeElectrodeCell,
        description="""
        The electrochemical cell configuration used in the measurement.
        """,
    )

    parameters = SubSection(
        section_def=ElectrochemicalMeasurementParameter,
        description="""
        Parameters of the electrochemical measurement.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizer for base ElectrochemicalMeasurement.
        - Synchronizes the sample between `cell.working_electrode.sample`
          and `Measurement.samples`.
        - Fills standard reduction potentials for reference electrodes
          if not explicitly set.
        """
        super().normalize(archive, logger)

        # Synchronize sample between cell.working_electrode and Measurement.samples
        if self.cell and self.cell.working_electrode:
            we = self.cell.working_electrode
            if we.sample is not None and not self.samples:
                self.samples = [we.sample]
            elif self.samples and we.sample is None:
                we.sample = self.samples[0]


class ElectrochemicalMeasurementResult(MeasurementResult):
    """
    Base class for electrochemical characterization measurement results.
    Inherits from NOMAD's `MeasurementResult` and can be understood as
    subclass of emmo:MeasurementResult.
    """

    m_def = Section(
        description="""
        Base measurement result for electrochemical characterization.
        """,
    )

    time = Quantity(
        type=np.float64,
        shape=['*'],
        unit='second',
        description="""
        Elapsed measurement time series.
        """,
    )

    potential = Quantity(
        type=np.float64,
        shape=['*'],
        unit='volt',
        description="""
        Applied or measured electric potential series.
        """,
    )

    potential_vs_rhe = Quantity(
        type=np.float64,
        shape=['*'],
        unit='volt',
        description="""
        Potential array converted vs. Reversible Hydrogen Electrode (RHE).
        """,
    )

    current = Quantity(
        type=np.float64,
        shape=['*'],
        unit='ampere',
        description="""
        Applied or measured electric current series.
        """,
    )

    current_density = Quantity(
        type=np.float64,
        shape=['*'],
        unit=CD_UNIT,
        description="""
        Electric current series normalized by the (geometric) active surface area.
        """,
    )


class ElectrochemicalMeasurementReference(MeasurementReference):
    """
    A section used for referencing an ElectrochemicalMeasurement.
    """

    reference = Quantity(
        type=ElectrochemicalMeasurement,
        description='A reference to an ElectrochemicalMeasurement entry.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='ElectrochemicalMeasurement reference',
        ),
    )


# --- Voltammetry & Cyclic Voltammetry (CV) ---
class VoltammetryParameter(ElectrochemicalMeasurementParameter):
    """
    Control parameters for voltammetric excitation signals.
    """

    m_def = Section(
        description="""
        Parameters governing the applied potential programme in voltammetry.
        """,
    )

    initial_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Starting electric potential of the sweep.
        """,
    )

    final_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Ending electric potential of the sweep.
        """,
    )

    scan_rate = Quantity(
        type=float,
        unit='volt / second',
        description="""
        Rate of potential change with time.
        """,
    )

    step_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Discrete potential step increment between successive data sampling points.
        """,
    )


class CVParameter(VoltammetryParameter):
    """
    Control parameters for cyclic voltammetry measurements
    with triangular potential waveforms (echem:TriangularPotentialWaveform).
    """

    m_def = Section(
        description="""
        Control and termination parameters for cyclic voltammetry.
        """,
    )

    lower_switching_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Lower vertex potential where scan direction reverses.
        """,
    )

    upper_switching_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Upper vertex potential where scan direction reverses.
        """,
    )

    initial_scan_direction = Quantity(
        type=MEnum('positive', 'negative'),
        default='positive',
        description="""
        Direction of the initial potential sweep
        (positive = anodic, negative = cathodic).
        """,
    )

    number_of_cycles = Quantity(
        type=int,
        default=1,
        description="""
        Total number of programmed cyclic sweeps (echem:TotalNumberOfCycles).
        """,
    )


class CVCycle(ElectrochemicalMeasurementResult):
    """
    Data for an individual cycle of a cyclic voltammogram.
    """

    m_def = Section(
        description="""
        Data and properties for an individual cycle of a cyclic voltammetry sweep.
        """,
    )

    cycle_index = Quantity(
        type=int,
        description="""
        Index of this cycle (1-based).
        """,
    )


class CVResult(ElectrochemicalMeasurementResult, PlotSection):
    """
    Results of a cyclic voltammetry measurement, containing individual segmented cycles
    and interactive plots.

    Ontology:
        echem:CurrentPotentialPlot
        (https://w3id.org/emmo/domain/electrochemistry#electrochemistry_b9a72491_8a50_4cac_a131_1e95d72b57ee)
    """

    m_def = Section(
        description="""
        Result section for cyclic voltammetry measurements.
        """,
        a_eln={
            'overview': True,
        },
    )

    cycles = SubSection(
        section_def=CVCycle,
        repeats=True,
        description="""
        Individual segmented cycles of the cyclic voltammetry experiment.
        """,
    )

    cycle_index = Quantity(
        type=int,
        shape=['*'],
        description="""
        Array of cycle indices for each individual data point.
        """,
    )

    scan_rate = Quantity(
        type=float,
        unit='volt / second',
        description='Scan rate of the cyclic voltammetric sweep.',
    )


class Voltammetry(ElectrochemicalMeasurement, EntryData):
    """
    Voltammetric measurement where the potential of the working electrode is varied
    while recording the resulting current.

    Ontology:
        chameo:Voltammetry
        (https://w3id.org/emmo/domain/characterisation-methodology/chameo#Voltammetry)
    """

    m_def = Section(
        description='General voltammetric measurement section.',
    )

    potentiostat = SubSection(
        section_def=PotentiostatReference,
        description="""
        The potentiostat used to conduct the voltammetry experiment.
        """,
    )

    parameters = SubSection(
        section_def=VoltammetryParameter,
        description="""
        Parameters of the voltammetric sweep.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizer for base Voltammetry measurement.
        - Synchronizes the Measurement.instruments list with
        the potentiostat.
        """
        super().normalize(archive, logger)

        # Synchronize the potentiostat with the Measurement.instruments list
        if self.potentiostat:
            if self.instruments is None:
                self.instruments = [self.potentiostat]
            elif self.potentiostat not in self.instruments:
                self.instruments.append(self.potentiostat)


class CyclicVoltammetry(Voltammetry):
    """
    Cyclic Voltammetry (CV) measurement.
    Sweeps the potential of the working electrode triangularly between vertex potentials
    while measuring the resulting current response over one or multiple cycles.

    Ontology:
        chameo:CyclicVoltammetry
        (https://w3id.org/emmo/domain/characterisation-methodology/chameo#CyclicVoltammetry)
    """

    m_def = Section(
        categories=[ElectrochemicalMeasurementCategory],
        description="""
        Cyclic voltammetry measurement entry schema.
        """,
    )

    parameters = SubSection(
        section_def=CVParameter,
        description="""
        Control and termination parameters for the cyclic sweep.
        """,
    )

    results = SubSection(
        section_def=CVResult,
        repeats=True,
        description="""
        Extracted cyclic voltammetry data and results.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizer for CyclicVoltammetry:
        Synchronizes cell defaults via super().normalize() and invokes
        the decoupled CV normalizer for all results.
        """
        super().normalize(archive, logger)
        normalize_cyclic_voltammetry(self, archive, logger)


class ECSAParameter(ElectrochemicalMeasurementParameter):
    """
    Control parameters for ECSA measurements across multiple scan rates.
    """

    m_def = Section(
        description="""
        Control parameters for ECSA measurements across multiple scan rates.
        """,
    )

    runs = SubSection(
        section_def=CVParameter,
        repeats=True,
        description="""
        Parameters for the individual cyclic voltammetry sweeps.
        """,
    )


class ECSAResult(ElectrochemicalMeasurementResult, PlotSection):
    """
    Result section for ECSA measurements containing individual cyclic voltammetry
    sweeps across different scan rates, capacitive charging currents,
    and extracted double-layer capacitance metrics.
    """

    m_def = Section(
        description="""
        Result section for ECSA multi-scan rate sweeps and capacitance.
        """,
        a_eln={
            'overview': True,
        },
    )

    runs = SubSection(
        section_def=CVResult,
        repeats=True,
        description="""
        Individual cyclic voltammetry sweeps at different scan rates.
        """,
    )

    scan_rates = Quantity(
        type=np.float64,
        shape=['*'],
        unit='volt / second',
        description="""
        Scan rates of the individual CV sweeps.
        """,
    )

    charging_currents = Quantity(
        type=np.float64,
        shape=['*'],
        unit='ampere',
        description="""
        Capacitive charging currents evaluated at center potential.
        """,
    )

    double_layer_capacitance = Quantity(
        type=float,
        unit='farad',
        description="""
        Double layer capacitance (Cdl) from charging current slope.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Evaluate Cdl from CV runs and generate Plotly figures
        via decoupled normalizer.
        """
        super().normalize(archive, logger)
        normalize_ecsa_result(self)


class ECSAMeasurement(ElectrochemicalMeasurement, EntryData):
    """
    Electrochemically Active Surface Area (ECSA) measurement entry.
    Sweeps cyclic voltammograms across multiple scan rates within a capacitive
    double-layer potential window to determine double-layer capacitance (Cdl)
    and electrochemical surface area (ECSA).
    """

    m_def = Section(
        categories=[ElectrochemicalMeasurementCategory],
        description="""
        ECSA measurement entry schema.
        """,
    )

    parameters = SubSection(
        section_def=ECSAParameter,
        description="""
        Parameters governing the individual ECSA CV sweeps.
        """,
    )

    results = SubSection(
        section_def=ECSAResult,
        repeats=True,
        description="""
        Results of the ECSA measurement.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Normalizer for ECSA measurement entry delegating to decoupled normalizer."""
        super().normalize(archive, logger)
        normalize_ecsa_measurement(self, archive, logger)


class ElectrochemicalMappingStep(MappingStep):
    """
    A single electrochemical measurement step
    at a defined stage/sample coordinate within a mapping run.
    """

    m_def = Section(
        description="""
        A single electrochemical measurement step 
        at a defined stage/sample coordinate within a mapping run.
        """,
    )

    measurement_ref = SubSection(
        section_def=ElectrochemicalMeasurementReference,
        description="""
        Reference to the stand-alone electrochemical measurement entry.
        """,
    )


class ElectrochemicalMappingResult(MappingResult):
    """
    Synthesized electrochemical characterization result
    at a single mapped spatial point.
    """

    m_def = Section(
        description="""
        Synthesized electrochemical characterization result 
        at a single mapped spatial point.
        """,
    )


class ElectrochemicalMapping(MappingMeasurement, EntryData):
    """
    Electrochemical characterization mapping
    across multiple sample surface positions.
    """

    m_def = Section(
        categories=[ElectrochemicalMeasurementCategory],
        description="""
        Electrochemical mapping across multiple sample surface positions.
        """,
    )

    steps = SubSection(
        section_def=ElectrochemicalMappingStep,
        repeats=True,
        description="""
        Ordered list of measurement steps at mapped spatial coordinates.
        """,
    )

    results = SubSection(
        section_def=ElectrochemicalMappingResult,
        repeats=True,
        description="""
        List of electrochemical results at mapped spatial positions.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Normalizer for ElectrochemicalMapping."""
        normalize_electrochemical_mapping(self, archive, logger)
        super().normalize(archive, logger)


m_package.__init_metainfo__()
