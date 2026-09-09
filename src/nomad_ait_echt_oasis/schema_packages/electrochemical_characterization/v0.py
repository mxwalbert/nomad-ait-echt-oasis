from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objs as go
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
    CompositeSystem,
    CompositeSystemReference,
    Measurement,
    MeasurementResult,
)
from nomad.datamodel.metainfo.plot import (
    PlotlyFigure,
    PlotSection,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad.units import ureg
from nomad_material_processing.solution.general import (
    Solution,
)
from scipy.signal import find_peaks

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
MIN_POINTS_FOR_PEAK_DETECTION = 5
MIN_POINTS_FOR_CYCLE_SPLIT = 10
MIN_CYCLE_LENGTH = 4

STANDARD_REFERENCE_POTENTIALS_VS_SHE = {
    'Ag/AgCl (sat. KCl)': 0.197,
    'Ag/AgCl (3M KCl)': 0.210,
    'Ag/AgCl (1M KCl)': 0.236,
    'Standard Hydrogen Electrode (SHE)': 0.0,
    'Reversible Hydrogen Electrode (RHE)': 0.0,
    'Saturated Calomel Electrode (SCE)': 0.241,
    'Mercury-Mercurous Sulfate (MSE, sat. K2SO4)': 0.640,
    'Mercury-Mercuric Oxide (Hg/HgO, 1M KOH)': 0.098,
}

# --- Constants for abbreviating long unit strings ---
CD_UNIT = 'milliampere / centimeter ** 2'
C_UNIT = 'milliampere'


# --- Categories ---
class ElectrochemicalTestingCategory(EntryDataCategory):
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
            'Ag/AgCl (sat. KCl)',
            'Ag/AgCl (3M KCl)',
            'Ag/AgCl (1M KCl)',
            'Standard Hydrogen Electrode (SHE)',
            'Reversible Hydrogen Electrode (RHE)',
            'Saturated Calomel Electrode (SCE)',
            'Mercury-Mercurous Sulfate (MSE, sat. K2SO4)',
            'Mercury-Mercuric Oxide (Hg/HgO, 1M KOH)',
            'Ag/Ag+ (non-aqueous)',
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

    standard_potential_vs_she = Quantity(
        type=float,
        unit='volt',
        description="""
        The standard reduction potential of this reference electrode relative
        to the Standard Hydrogen Electrode (SHE).
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='volt',
            label='E° vs. SHE',
        ),
    )


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


class ElectrochemicalTesting(Measurement):
    """
    Base activity section for all electrochemical characterization measurements.
    Synchronizes the sample represented by the `WorkingElectrode` with
    NOMAD's `Measurement.samples`.

    Ontology:
        chameo:ElectrochemicalTesting
        (https://w3id.org/emmo/domain/characterisation-methodology/chameo#ElectrochemicalTesting)
    """

    m_def = Section(
        categories=[ElectrochemicalTestingCategory],
        description="""
        Base measurement for electrochemical characterization.
        """,
    )

    cell = SubSection(
        section_def=ThreeElectrodeCell,
        description="""
        The electrochemical cell used in the measurement.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizer for BaseElectrochemicalMeasurement.
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

        # Fill standard potential for reference electrode if known and not set
        if self.cell and self.cell.reference_electrode:
            ref = self.cell.reference_electrode
            if (
                ref.standard_potential_vs_she is None
                and ref.reference_type in STANDARD_REFERENCE_POTENTIALS_VS_SHE
            ):
                ref.standard_potential_vs_she = (
                    STANDARD_REFERENCE_POTENTIALS_VS_SHE[ref.reference_type] * ureg.volt
                )


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

    potential_vs_she = Quantity(
        type=np.float64,
        shape=['*'],
        unit='volt',
        description="""
        Potential array converted vs. Standard Hydrogen Electrode (SHE).
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
        Electric current series normalized by the (geometric) active surface area
        of the working electrode.
        """,
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
        description='Starting electric potential of the sweep.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='volt',
            label='Initial Potential',
        ),
    )

    final_potential = Quantity(
        type=float,
        unit='volt',
        description='Ending electric potential of the sweep.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='volt',
            label='Final Potential',
        ),
    )

    scan_rate = Quantity(
        type=float,
        unit='volt / second',
        description='Rate of potential change with time.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='millivolt / second',
            label='Scan Rate',
        ),
    )

    step_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Discrete potential step increment between successive data sampling points.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='millivolt',
            label='Step Potential',
        ),
    )


class CVParameter(VoltammetryParameter):
    """
    Control parameters for cyclic voltammetry measurements
    with triangular potential waveforms (echem:TriangularPotentialWaveform).
    """

    m_def = Section(
        description='Control and termination parameters for cyclic voltammetry.',
    )

    lower_switching_potential = Quantity(
        type=float,
        unit='volt',
        description='Lower vertex potential where scan direction reverses.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='volt',
            label='Lower Switching Potential',
        ),
    )

    upper_switching_potential = Quantity(
        type=float,
        unit='volt',
        description='Upper vertex potential where scan direction reverses.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='volt',
            label='Upper Switching Potential',
        ),
    )

    initial_scan_direction = Quantity(
        type=MEnum('positive', 'negative'),
        default='positive',
        description="""
        Direction of the initial potential sweep
        (positive = anodic, negative = cathodic).
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Initial Scan Direction',
        ),
    )

    number_of_cycles = Quantity(
        type=int,
        default=1,
        description="""
        Total number of programmed cyclic sweeps (echem:TotalNumberOfCycles).
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Number of Cycles',
        ),
    )


class CVCycle(ElectrochemicalMeasurementResult):
    """
    Data and extracted electrochemical metrics for an individual cycle
    of a cyclic voltammogram.
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

    anodic_peak_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Electric potential at the anodic peak maximum (Epa).
        """,
    )

    cathodic_peak_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Electric potential at the cathodic peak minimum (Epc).
        """,
    )

    anodic_peak_current = Quantity(
        type=float,
        unit='ampere',
        description="""
        Maximum current at the anodic peak (Ipa).
        """,
    )

    cathodic_peak_current = Quantity(
        type=float,
        unit='ampere',
        description="""
        Current at the cathodic peak (Ipc).
        """,
    )

    anodic_peak_current_density = Quantity(
        type=float,
        unit=CD_UNIT,
        description="""
        Maximum current density at the anodic peak (Jpa).
        """,
    )

    cathodic_peak_current_density = Quantity(
        type=float,
        unit=CD_UNIT,
        description="""
        Current density at the cathodic peak (Jpc).
        """,
    )

    peak_potential_separation = Quantity(
        type=float,
        unit='volt',
        description="""
        Separation between anodic and cathodic peak potentials (|Epa - Epc|).
        """,
    )

    half_wave_potential = Quantity(
        type=float,
        unit='volt',
        description="""
        Formal / half-wave potential (E1/2 = (Epa + Epc) / 2).
        """,
    )

    anodic_charge = Quantity(
        type=float,
        unit='coulomb',
        description="""
        Total integrated faradaic/capacitive anodic charge passed during this cycle.
        """,
    )

    cathodic_charge = Quantity(
        type=float,
        unit='coulomb',
        description="""
        Total integrated faradaic/capacitive cathodic charge passed during this cycle.
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
        description='Result section for cyclic voltammetry measurements.',
    )

    cycles = SubSection(
        section_def=CVCycle,
        repeats=True,
        description='Individual segmented cycles of the cyclic voltammetry experiment.',
    )

    cycle_index = Quantity(
        type=int,
        shape=['*'],
        description="""
        Array of cycle indices for each individual data point.
        """,
    )


class Voltammetry(ElectrochemicalTesting):
    """
    Voltammetric measurement where the potential of the working electrode is varied
    while recording the resulting current.
    """

    m_def = Section(
        description='General voltammetric measurement section.',
    )

    instrument = SubSection(
        section_def=PotentiostatReference,
        description="""
        The potentiostat used to conduct the voltammetry experiment
        (echem:hasTestEquipment).
        """,
    )

    parameters = SubSection(
        section_def=VoltammetryParameter,
        description='Parameters of the voltammetric sweep.',
    )


class CyclicVoltammetry(Voltammetry, EntryData):
    """
    Cyclic Voltammetry (CV) measurement.
    Sweeps the potential of the working electrode triangularly between vertex potentials
    while measuring the resulting current response over one or multiple cycles.
    """

    m_def = Section(
        categories=[ElectrochemicalTestingCategory],
        description='Cyclic voltammetry measurement entry schema.',
    )

    parameters = SubSection(
        section_def=CVParameter,
        description='Control and termination parameters for the cyclic sweep.',
    )

    results = SubSection(
        section_def=CVResult,
        repeats=True,
        description='Extracted cyclic voltammetry data and results.',
    )

    def _calculate_peaks_and_metrics(
        self,
        cycle: CVCycle,
        v_arr: np.ndarray,
        i_arr: np.ndarray,
        j_arr: np.ndarray | None,
        t_arr: np.ndarray | None,
    ) -> None:
        """Helper to find peaks and compute cycle metrics."""
        if (
            len(v_arr) < MIN_POINTS_FOR_PEAK_DETECTION
            or len(i_arr) < MIN_POINTS_FOR_PEAK_DETECTION
        ):
            return

        # Anodic peak (local maximum)
        pos_peaks, _ = find_peaks(i_arr)
        if len(pos_peaks) > 0:
            best_pos = pos_peaks[np.argmax(i_arr[pos_peaks])]
            cycle.anodic_peak_potential = float(v_arr[best_pos]) * ureg.volt
            cycle.anodic_peak_current = float(i_arr[best_pos]) * ureg.ampere
            if j_arr is not None:
                cycle.anodic_peak_current_density = float(j_arr[best_pos]) * (
                    ureg.milliampere / (ureg.centimeter**2)
                )

        # Cathodic peak (local minimum / most negative current)
        neg_peaks, _ = find_peaks(-i_arr)
        if len(neg_peaks) > 0:
            best_neg = neg_peaks[np.argmax(-i_arr[neg_peaks])]
            cycle.cathodic_peak_potential = float(v_arr[best_neg]) * ureg.volt
            cycle.cathodic_peak_current = float(i_arr[best_neg]) * ureg.ampere
            if j_arr is not None:
                cycle.cathodic_peak_current_density = float(j_arr[best_neg]) * (
                    ureg.milliampere / (ureg.centimeter**2)
                )

        # Peak separation and half-wave potential
        if (
            cycle.anodic_peak_potential is not None
            and cycle.cathodic_peak_potential is not None
        ):
            epa = cycle.anodic_peak_potential.to('volt').magnitude
            epc = cycle.cathodic_peak_potential.to('volt').magnitude
            cycle.peak_potential_separation = abs(epa - epc) * ureg.volt
            cycle.half_wave_potential = ((epa + epc) / 2.0) * ureg.volt

        # Integrated charge
        if t_arr is not None and len(t_arr) == len(i_arr):
            dt = np.gradient(t_arr)
            pos_mask = i_arr > 0
            neg_mask = i_arr < 0
            cycle.anodic_charge = (
                float(np.sum(i_arr[pos_mask] * dt[pos_mask])) * ureg.coulomb
            )
            cycle.cathodic_charge = (
                float(abs(np.sum(i_arr[neg_mask] * dt[neg_mask]))) * ureg.coulomb
            )

    def _generate_plotly_figures(
        self, result: CVResult, use_density: bool
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
                if cyc.potential is None or cyc.current is None:
                    continue
                cyc_v = np.asarray(cyc.potential.to('volt').magnitude)
                cyc_y = np.asarray(
                    cyc.current_density.to(CD_UNIT).magnitude
                    if use_density and cyc.current_density is not None
                    else cyc.current.to(C_UNIT).magnitude
                )
                cyc_name = (
                    f'Cycle {cyc.cycle_index}'
                    if cyc.cycle_index is not None
                    else 'Voltammogram'
                )
                fig_cv.add_trace(
                    go.Scatter(
                        x=cyc_v,
                        y=cyc_y,
                        mode='lines',
                        name=cyc_name,
                    )
                )
        elif result.potential is not None and result.current is not None:
            v_data = np.asarray(result.potential.to('volt').magnitude)
            y_data = np.asarray(
                result.current_density.to(CD_UNIT).magnitude
                if use_density and result.current_density is not None
                else result.current.to(C_UNIT).magnitude
            )
            fig_cv.add_trace(
                go.Scatter(
                    x=v_data,
                    y=y_data,
                    mode='lines',
                    name='Voltammogram',
                )
            )

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
        if (
            result.time is not None
            and result.potential is not None
            and result.current is not None
        ):
            has_time = True
            t_data = np.asarray(result.time.to('second').magnitude)
            v_data = np.asarray(result.potential.to('volt').magnitude)
            y_data = np.asarray(
                result.current_density.to(CD_UNIT).magnitude
                if use_density and result.current_density is not None
                else result.current.to(C_UNIT).magnitude
            )
            fig_time.add_trace(
                go.Scatter(
                    x=t_data,
                    y=v_data,
                    mode='lines',
                    name='Potential (V)',
                    yaxis='y1',
                )
            )
            fig_time.add_trace(
                go.Scatter(
                    x=t_data,
                    y=y_data,
                    mode='lines',
                    name=y_label,
                    yaxis='y2',
                )
            )
        elif result.cycles:
            for cyc in result.cycles:
                if (
                    cyc.time is not None
                    and cyc.potential is not None
                    and cyc.current is not None
                ):
                    has_time = True
                    cyc_t = np.asarray(cyc.time.to('second').magnitude)
                    cyc_v = np.asarray(cyc.potential.to('volt').magnitude)
                    cyc_y = np.asarray(
                        cyc.current_density.to(CD_UNIT).magnitude
                        if use_density and cyc.current_density is not None
                        else cyc.current.to(C_UNIT).magnitude
                    )
                    suffix = (
                        f' (Cycle {cyc.cycle_index})'
                        if len(result.cycles) > 1 and cyc.cycle_index is not None
                        else ''
                    )
                    fig_time.add_trace(
                        go.Scatter(
                            x=cyc_t,
                            y=cyc_v,
                            mode='lines',
                            name=f'Potential (V){suffix}',
                            yaxis='y1',
                        )
                    )
                    fig_time.add_trace(
                        go.Scatter(
                            x=cyc_t,
                            y=cyc_y,
                            mode='lines',
                            name=f'{y_label}{suffix}',
                            yaxis='y2',
                        )
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

    def _normalize_continuous_current_density(
        self, result: CVResult, surface_area: float | None
    ) -> None:
        """
        Compute current density series on CVResult if electrode
        surface area is known.
        """
        if (
            surface_area
            and surface_area > 0
            and result.current is not None
            and result.current_density is None
        ):
            current_arr = np.asarray(result.current.to('ampere').magnitude, dtype=float)
            result.current_density = ((current_arr / surface_area) * 1000.0) * (
                ureg.milliampere / (ureg.centimeter**2)
            )

    def _normalize_continuous_potential_vs_she(
        self,
        result: CVResult,
        ref_potential_she: float | None,
        ph_val: float | None,
    ) -> None:
        """
        Convert potential series to SHE/RHE on CVResult if reference
        potential and pH are known.
        """
        if (
            ref_potential_she is not None
            and ph_val is not None
            and result.potential is not None
            and result.potential_vs_she is None
        ):
            potential_arr = np.asarray(
                result.potential.to('volt').magnitude, dtype=float
            )
            result.potential_vs_she = (
                potential_arr + ref_potential_she + (0.05916 * ph_val)
            ) * ureg.volt

    def _auto_decompose_cycles(  # noqa: PLR0912, PLR0915
        self,
        result: CVResult,
    ) -> None:
        """
        Auto-decompose contiguous data into CVCycle segments if
        cycles are not provided.
        """
        if result.cycles or result.potential is None or result.current is None:
            return

        potential_arr = np.asarray(result.potential.to('volt').magnitude, dtype=float)
        current_arr = np.asarray(result.current.to('ampere').magnitude, dtype=float)
        time_arr = (
            np.asarray(result.time.to('second').magnitude, dtype=float)
            if result.time is not None
            else None
        )
        j_arr = (
            np.asarray(
                result.current_density.to(CD_UNIT).magnitude,
                dtype=float,
            )
            if result.current_density is not None
            else None
        )
        v_she = (
            np.asarray(result.potential_vs_she.to('volt').magnitude, dtype=float)
            if result.potential_vs_she is not None
            else None
        )

        if result.cycle_index is not None and len(result.cycle_index) == len(
            potential_arr
        ):
            c_indices = np.asarray(result.cycle_index)
            unique_cycles = np.unique(c_indices)
            for c_val in unique_cycles:
                mask = c_indices == c_val
                cyc = CVCycle(
                    cycle_index=int(c_val),
                    potential=potential_arr[mask] * ureg.volt,
                    current=current_arr[mask] * ureg.ampere,
                )
                if time_arr is not None:
                    cyc.time = time_arr[mask] * ureg.second
                if j_arr is not None:
                    cyc.current_density = j_arr[mask] * (
                        ureg.milliampere / (ureg.centimeter**2)
                    )
                if v_she is not None:
                    cyc.potential_vs_she = v_she[mask] * ureg.volt
                result.cycles.append(cyc)
        elif len(potential_arr) > MIN_POINTS_FOR_CYCLE_SPLIT:
            diffs = np.diff(potential_arr)
            signs = np.sign(diffs)
            signs = np.where(signs == 0, 1, signs)
            turning_points = np.where(np.diff(signs) != 0)[0] + 1

            cycle_breaks = [0]
            for i in range(1, len(turning_points), 2):
                cycle_breaks.append(turning_points[i])
            if cycle_breaks[-1] != len(potential_arr):
                cycle_breaks.append(len(potential_arr))

            cycle_index_arr = np.zeros(len(potential_arr), dtype=int)
            for c_idx in range(len(cycle_breaks) - 1):
                start_i = cycle_breaks[c_idx]
                end_i = cycle_breaks[c_idx + 1]
                if end_i - start_i < MIN_CYCLE_LENGTH:
                    continue

                cycle_num = len(result.cycles) + 1
                cycle_index_arr[start_i:end_i] = cycle_num

                cyc = CVCycle(
                    cycle_index=cycle_num,
                    potential=potential_arr[start_i:end_i] * ureg.volt,
                    current=current_arr[start_i:end_i] * ureg.ampere,
                )
                if time_arr is not None:
                    cyc.time = time_arr[start_i:end_i] * ureg.second
                if j_arr is not None:
                    cyc.current_density = j_arr[start_i:end_i] * (
                        ureg.milliampere / (ureg.centimeter**2)
                    )
                if v_she is not None:
                    cyc.potential_vs_she = v_she[start_i:end_i] * ureg.volt
                result.cycles.append(cyc)

            if result.cycle_index is None and len(result.cycles) > 0:
                result.cycle_index = cycle_index_arr
        else:
            cyc = CVCycle(
                cycle_index=1,
                potential=potential_arr * ureg.volt,
                current=current_arr * ureg.ampere,
            )
            if time_arr is not None:
                cyc.time = time_arr * ureg.second
            if j_arr is not None:
                cyc.current_density = j_arr * (ureg.milliampere / (ureg.centimeter**2))
            if v_she is not None:
                cyc.potential_vs_she = v_she * ureg.volt
            result.cycles.append(cyc)
            if result.cycle_index is None:
                result.cycle_index = np.ones(len(potential_arr), dtype=int)

    def _normalize_and_evaluate_cycles(
        self,
        result: CVResult,
        surface_area: float | None,
        ref_potential_she: float | None,
        ph_val: float | None,
    ) -> None:
        """
        Normalize individual cycles and extract redox peak parameters.
        """
        if not result.cycles:
            return

        for cyc in result.cycles:
            if cyc.current is None or cyc.potential is None:
                continue

            c_v = np.asarray(cyc.potential.to('volt').magnitude, dtype=float)
            c_i = np.asarray(cyc.current.to('ampere').magnitude, dtype=float)
            c_t = (
                np.asarray(cyc.time.to('second').magnitude, dtype=float)
                if cyc.time is not None
                else None
            )

            # Current density normalization on cycle
            if surface_area and surface_area > 0 and cyc.current_density is None:
                c_j = (c_i / surface_area) * 1000.0
                cyc.current_density = c_j * (ureg.milliampere / (ureg.centimeter**2))
            elif cyc.current_density is not None:
                c_j = np.asarray(
                    cyc.current_density.to(CD_UNIT).magnitude,
                    dtype=float,
                )
            else:
                c_j = None

            # Potential vs SHE conversion on cycle
            if (
                ref_potential_she is not None
                and ph_val is not None
                and cyc.potential_vs_she is None
            ):
                cyc.potential_vs_she = (
                    c_v + ref_potential_she + (0.05916 * ph_val)
                ) * ureg.volt

            # Calculate peaks and cycle metrics (ONLY in CVCycle)
            self._calculate_peaks_and_metrics(cyc, c_v, c_i, c_j, c_t)

    def _populate_continuous_data_from_cycles(self, result: CVResult) -> None:
        """
        Concatenate cycle arrays to populate continuous fields on
        CVResult if not present.
        """
        if result.potential is not None or not result.cycles:
            return

        all_v = []
        all_i = []
        all_t = []
        all_j = []
        all_she = []
        all_idx = []

        has_times = all(cyc.time is not None for cyc in result.cycles)
        has_j = all(cyc.current_density is not None for cyc in result.cycles)
        has_she = all(cyc.potential_vs_she is not None for cyc in result.cycles)

        for cyc in result.cycles:
            if cyc.potential is None or cyc.current is None:
                continue
            n_pts = len(cyc.potential)
            all_v.append(np.asarray(cyc.potential.to('volt').magnitude))
            all_i.append(np.asarray(cyc.current.to('ampere').magnitude))
            c_num = cyc.cycle_index if cyc.cycle_index is not None else 1
            all_idx.append(np.full(n_pts, c_num, dtype=int))
            if has_times and cyc.time is not None:
                all_t.append(np.asarray(cyc.time.to('second').magnitude))
            if has_j and cyc.current_density is not None:
                all_j.append(np.asarray(cyc.current_density.to(CD_UNIT).magnitude))
            if has_she and cyc.potential_vs_she is not None:
                all_she.append(np.asarray(cyc.potential_vs_she.to('volt').magnitude))

        if all_v:
            result.potential = np.concatenate(all_v) * ureg.volt
            result.current = np.concatenate(all_i) * ureg.ampere
            if result.cycle_index is None:
                result.cycle_index = np.concatenate(all_idx)
            if all_t:
                result.time = np.concatenate(all_t) * ureg.second
            if all_j:
                result.current_density = np.concatenate(all_j) * (
                    ureg.milliampere / (ureg.centimeter**2)
                )
            if all_she:
                result.potential_vs_she = np.concatenate(all_she) * ureg.volt

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizer for CyclicVoltammetry:
        1. Synchronizes samples and fills reference defaults via super().
        2. Computes current density if surface_area of working electrode is given.
        3. Computes potential vs. SHE if pH and reference standard are given.
        4. Auto-decomposes contiguous data into CVCycle segments if not set,
           populating result.cycles and result.cycle_index.
        5. Detects anodic/cathodic peaks and formal redox potentials for each cycle.
        6. Renders interactive Plotly voltammograms in PlotSection.
        """
        super().normalize(archive, logger)

        surface_area_val = None
        if (
            self.cell
            and self.cell.working_electrode
            and self.cell.working_electrode.surface_area
        ):
            surface_area_val = self.cell.working_electrode.surface_area.to(
                'centimeter ** 2'
            ).magnitude

        ref_potential_she = None
        if (
            self.cell
            and self.cell.reference_electrode
            and self.cell.reference_electrode.standard_potential_vs_she
        ):
            ref_potential_she = (
                self.cell.reference_electrode.standard_potential_vs_she.to(
                    'volt'
                ).magnitude
            )

        ph_val = None
        if (
            self.cell
            and self.cell.electrolyte
            and self.cell.electrolyte.ph_value is not None
        ):
            ph_val = float(self.cell.electrolyte.ph_value)

        for result in self.results:
            # 1. Continuous current density normalization on CVResult
            self._normalize_continuous_current_density(result, surface_area_val)

            # 2. Continuous SHE/RHE conversion on CVResult
            self._normalize_continuous_potential_vs_she(
                result, ref_potential_she, ph_val
            )

            # 3. Auto-decompose continuous data into CVCycle segments if not provided
            self._auto_decompose_cycles(result)

            # 4. Normalize individual cycles and calculate metrics in CVCycle
            self._normalize_and_evaluate_cycles(
                result, surface_area_val, ref_potential_she, ph_val
            )

            # 5. Populate continuous arrays on CVResult from cycles if not present
            self._populate_continuous_data_from_cycles(result)

            # 6. Generate Plotly figures
            result.figures = self._generate_plotly_figures(
                result, use_density=(surface_area_val is not None)
            )


m_package.__init_metainfo__()
