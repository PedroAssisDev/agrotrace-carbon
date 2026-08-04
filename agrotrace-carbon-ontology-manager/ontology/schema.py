"""TBox definition for AgroMRV-O Lite (OWL 2, self-contained)."""

from __future__ import annotations

from owlready2 import (
    DataProperty,
    ObjectProperty,
    Thing,
    get_ontology,
)


def define_schema(base_iri: str = "http://example.org/agromrv-lite#") -> object:
    """Create and return the AgroMRV-O Lite ontology with schema definitions."""
    onto = get_ontology(base_iri)

    with onto:
        # ------------------------------------------------------------------ #
        # Context Module
        # ------------------------------------------------------------------ #
        class Context(Thing):
            pass

        class OrganizationalContext(Context):
            pass

        class TemporalContext(Context):
            pass

        # ------------------------------------------------------------------ #
        # Farm Entity Module
        # ------------------------------------------------------------------ #
        class FarmEntity(Thing):
            pass

        class Property(FarmEntity):
            pass

        class Animal(FarmEntity):
            pass

        class Location(FarmEntity):
            pass

        class EmissionCycle(FarmEntity):
            """Reporting cycle linking property, period, granularity and status."""
            pass

        # ------------------------------------------------------------------ #
        # Record Module
        # ------------------------------------------------------------------ #
        class DataRecord(Thing):
            pass

        class AnnualPropertyInventoryRecord(DataRecord):
            pass

        class MonthlyPropertyRecord(DataRecord):
            pass

        class DailyAnimalProductionRecord(DataRecord):
            pass

        class DailyAnimalNutritionRecord(DataRecord):
            pass

        # ------------------------------------------------------------------ #
        # Observation Module
        # ------------------------------------------------------------------ #
        class Observation(Thing):
            pass

        class QuantitativeObservation(Observation):
            pass

        class QualitativeObservation(Observation):
            pass

        class FeedInputObservation(QuantitativeObservation):
            pass

        class HerdCountObservation(QuantitativeObservation):
            pass

        class AnimalWeightObservation(QuantitativeObservation):
            pass

        class MilkProductionObservation(QuantitativeObservation):
            pass

        class MilkCompositionObservation(QuantitativeObservation):
            pass

        class MilkSalesObservation(QuantitativeObservation):
            pass

        class EnergyUseObservation(QuantitativeObservation):
            pass

        class FuelUseObservation(QuantitativeObservation):
            pass

        class FertilizerUseObservation(QuantitativeObservation):
            pass

        class LandUseObservation(QuantitativeObservation):
            pass

        class SoilTypeObservation(QualitativeObservation):
            pass

        class NutritionObservation(QuantitativeObservation):
            pass

        class EconomicObservation(QuantitativeObservation):
            pass

        class EmissionObservation(QuantitativeObservation):
            pass

        class DestinationObservation(QualitativeObservation):
            pass

        class ResponsiblePersonObservation(QualitativeObservation):
            pass

        class AdministrativeObservation(QualitativeObservation):
            pass

        # ------------------------------------------------------------------ #
        # Canonical Variable Module
        # ------------------------------------------------------------------ #
        class CanonicalVariable(Thing):
            pass

        class FeedVariable(CanonicalVariable):
            pass

        class HerdVariable(CanonicalVariable):
            pass

        class WeightVariable(CanonicalVariable):
            pass

        class MilkVariable(CanonicalVariable):
            pass

        class MilkCompositionVariable(CanonicalVariable):
            pass

        class EnergyVariable(CanonicalVariable):
            pass

        class FuelVariable(CanonicalVariable):
            pass

        class FertilizerVariable(CanonicalVariable):
            pass

        class LandVariable(CanonicalVariable):
            pass

        class SoilVariable(CanonicalVariable):
            pass

        class NutritionVariable(CanonicalVariable):
            pass

        class EmissionVariable(CanonicalVariable):
            pass

        class EconomicVariable(CanonicalVariable):
            pass

        class AdministrativeVariable(CanonicalVariable):
            pass

        # ------------------------------------------------------------------ #
        # Unit Module
        # ------------------------------------------------------------------ #
        class Unit(Thing):
            pass

        # ------------------------------------------------------------------ #
        # Calculation Module
        # ------------------------------------------------------------------ #
        class CalculationEntity(Thing):
            pass

        class CalculationMethod(CalculationEntity):
            pass

        class EmissionCalculationMethod(CalculationMethod):
            pass

        class ConversionCalculationMethod(CalculationMethod):
            pass

        class ConfigurationMethod(CalculationMethod):
            pass

        class EntericFermentationCH4CalculationMethod(EmissionCalculationMethod):
            pass

        class ManureManagementCH4CalculationMethod(EmissionCalculationMethod):
            pass

        class FertilizerN2OCalculationMethod(EmissionCalculationMethod):
            pass

        class EnergyCO2CalculationMethod(EmissionCalculationMethod):
            pass

        class TotalGHGCO2eCalculationMethod(EmissionCalculationMethod):
            pass

        class MonthlyToAnnualSumMethod(ConversionCalculationMethod):
            pass

        class MonthlyToAnnualProrationMethod(ConversionCalculationMethod):
            pass

        class DefaultConfigurationProvider(ConfigurationMethod):
            pass

        class CalculationExecution(CalculationEntity):
            pass

        class EmissionCalculationExecution(CalculationExecution):
            pass

        class ConversionCalculationExecution(CalculationExecution):
            pass

        class BatchCalculationExecution(CalculationExecution):
            pass

        class LegacyCompatibilityExecution(CalculationExecution):
            pass

        class CalculationInput(Thing):
            pass

        class ObservationInput(CalculationInput):
            pass

        class ParameterInput(CalculationInput):
            pass

        class EmissionFactorInput(CalculationInput):
            pass

        class GWPInput(CalculationInput):
            pass

        class ConvertedInput(CalculationInput):
            pass

        class CalculationParameter(Thing):
            pass

        class EmissionFactor(CalculationParameter):
            pass

        class GWPParameterSet(CalculationParameter):
            pass

        class CalculationResult(Thing):
            pass

        class EmissionResult(CalculationResult):
            pass

        class CH4EmissionResult(EmissionResult):
            pass

        class N2OEmissionResult(EmissionResult):
            pass

        class CO2EmissionResult(EmissionResult):
            pass

        class CO2EquivalentResult(EmissionResult):
            pass

        class ProductivityResult(CalculationResult):
            pass

        class DMIResult(CalculationResult):
            pass

        class AggregatedResult(CalculationResult):
            pass

        # ------------------------------------------------------------------ #
        # Greenhouse Gas & Emission Source
        # ------------------------------------------------------------------ #
        class GreenhouseGas(Thing):
            pass

        class CarbonDioxide(GreenhouseGas):
            pass

        class Methane(GreenhouseGas):
            pass

        class NitrousOxide(GreenhouseGas):
            pass

        class EmissionSource(Thing):
            pass

        class EntericFermentation(EmissionSource):
            pass

        class ManureManagement(EmissionSource):
            pass

        class FertilizerApplication(EmissionSource):
            pass

        class EnergyUse(EmissionSource):
            pass

        class TotalGHG(EmissionSource):
            pass

        # ------------------------------------------------------------------ #
        # Software Module
        # ------------------------------------------------------------------ #
        class SoftwareComponent(Thing):
            pass

        class SoftwareFunction(SoftwareComponent):
            pass

        class BatchCalculationRunner(SoftwareComponent):
            pass

        class LegacyCompatibilityAdapter(SoftwareComponent):
            pass

        # ------------------------------------------------------------------ #
        # Object Properties
        # ------------------------------------------------------------------ #
        class hasOrganizationalContext(ObjectProperty):
            domain = [Context, DataRecord, Observation, CalculationExecution]
            range = [OrganizationalContext]

        class hasTemporalContext(ObjectProperty):
            domain = [Context, DataRecord, Observation, CalculationExecution]
            range = [TemporalContext]

        class refersToProperty(ObjectProperty):
            domain = [DataRecord, Observation, EmissionCycle, EmissionResult, CalculationResult]
            range = [Property]

        class refersToAnimal(ObjectProperty):
            domain = [DataRecord, Observation]
            range = [Animal]

        class belongsToCycle(ObjectProperty):
            domain = [Observation, EmissionResult, CalculationResult, CalculationExecution]
            range = [EmissionCycle]

        class hasPreviousResult(ObjectProperty):
            domain = [EmissionResult, CalculationResult]
            range = [CalculationResult]

        class hasObservation(ObjectProperty):
            domain = [DataRecord]
            range = [Observation]

        class observesVariable(ObjectProperty):
            domain = [Observation]
            range = [CanonicalVariable]

        class hasUnit(ObjectProperty):
            domain = [QuantitativeObservation, EmissionResult, CalculationResult]
            range = [Unit]

        class belongsToRecord(ObjectProperty):
            domain = [Observation]
            range = [DataRecord]

        class hasRecordType(ObjectProperty):
            domain = [DataRecord]
            range = [Thing]

        class hasCalculationMethod(ObjectProperty):
            domain = [CalculationExecution, CalculationMethod]
            range = [CalculationMethod]

        class implementedByFunction(ObjectProperty):
            domain = [CalculationMethod]
            range = [SoftwareFunction]

        class implementedInSoftwareComponent(ObjectProperty):
            domain = [CalculationMethod, SoftwareFunction]
            range = [SoftwareComponent]

        class calculatesGas(ObjectProperty):
            domain = [EmissionCalculationMethod, EmissionResult]
            range = [GreenhouseGas]

        class calculatesEmissionSource(ObjectProperty):
            domain = [EmissionCalculationMethod, EmissionResult]
            range = [EmissionSource]

        class requiresInputVariable(ObjectProperty):
            domain = [CalculationMethod]
            range = [CanonicalVariable]

        class usesEmissionFactor(ObjectProperty):
            domain = [CalculationMethod, CalculationExecution]
            range = [EmissionFactor]

        class usesGWPParameterSet(ObjectProperty):
            domain = [CalculationMethod, CalculationExecution, CO2EquivalentResult]
            range = [GWPParameterSet]

        class hasCalculationInput(ObjectProperty):
            domain = [CalculationExecution]
            range = [CalculationInput]

        class generatesCalculationResult(ObjectProperty):
            domain = [CalculationExecution]
            range = [CalculationResult]

        class hasPartialResult(ObjectProperty):
            domain = [AggregatedResult, TotalGHGCO2eCalculationMethod]
            range = [CalculationResult]

        class hasTotalResult(ObjectProperty):
            domain = [AggregatedResult, CalculationExecution]
            range = [CalculationResult]

        class convertsFromGranularity(ObjectProperty):
            domain = [ConversionCalculationMethod]
            range = [TemporalContext]

        class convertsToGranularity(ObjectProperty):
            domain = [ConversionCalculationMethod]
            range = [TemporalContext]

        class usesObservation(ObjectProperty):
            domain = [CalculationInput, CalculationExecution]
            range = [Observation]

        class usesCanonicalVariable(ObjectProperty):
            domain = [CalculationInput, CalculationMethod]
            range = [CanonicalVariable]

        # ------------------------------------------------------------------ #
        # Data Properties
        # ------------------------------------------------------------------ #
        class hasIdentifier(DataProperty):
            range = [str]

        class hasPropertyName(DataProperty):
            range = [str]

        class hasOwnerName(DataProperty):
            range = [str]

        class hasInformationResponsible(DataProperty):
            range = [str]

        class hasLocationName(DataProperty):
            range = [str]

        class hasOrganizationalGranularity(DataProperty):
            range = [str]

        class hasTemporalType(DataProperty):
            range = [str]

        class hasTemporalGranularity(DataProperty):
            range = [str]

        class hasStartDate(DataProperty):
            range = [str]

        class hasEndDate(DataProperty):
            range = [str]

        class hasYear(DataProperty):
            range = [str]

        class hasDate(DataProperty):
            range = [str]

        class hasNumericValue(DataProperty):
            range = [float]

        class hasTextValue(DataProperty):
            range = [str]

        class hasCanonicalName(DataProperty):
            range = [str]

        class hasDisplayName(DataProperty):
            range = [str]

        class hasOriginalColumnName(DataProperty):
            range = [str]

        class hasExpectedUnit(DataProperty):
            range = [str]

        class hasFunctionName(DataProperty):
            range = [str]

        class hasModulePath(DataProperty):
            range = [str]

        class hasFormulaExpression(DataProperty):
            range = [str]

        class hasCalculationVersion(DataProperty):
            range = [str]

        class hasMethodDescription(DataProperty):
            range = [str]

        class hasParameterName(DataProperty):
            range = [str]

        class hasParameterValue(DataProperty):
            range = [float]

        class hasParameterLifecycleStatus(DataProperty):
            """Lifecycle: pending | corrected | confirmed | published."""
            domain = [CalculationParameter]
            range = [str]

        class hasNumericResult(DataProperty):
            range = [float]

        class hasResultUnit(DataProperty):
            range = [str]

        class hasResultLifecycleStatus(DataProperty):
            """Lifecycle: preliminary | recalculated | approved | published."""
            domain = [CalculationResult]
            range = [str]

        class hasResultKey(DataProperty):
            """Deterministic logical key for upsert of results."""
            domain = [CalculationResult]
            range = [str]

        class hasCO2eValue(DataProperty):
            domain = [CalculationResult]
            range = [float]

        class hasCO2eUnit(DataProperty):
            domain = [CalculationResult]
            range = [str]

        class hasFormulaId(DataProperty):
            domain = [CalculationResult, CalculationExecution]
            range = [str]

        class hasMethodId(DataProperty):
            domain = [CalculationResult]
            range = [str]

        class hasMethodVersion(DataProperty):
            domain = [CalculationResult]
            range = [str]

        class hasCalculatedAt(DataProperty):
            domain = [CalculationResult]
            range = [str]

        class hasOntologyVersion(DataProperty):
            domain = [EmissionCycle, CalculationResult]
            range = [str]

        class hasCycleId(DataProperty):
            domain = [EmissionCycle]
            range = [str]

        class hasCycleStatus(DataProperty):
            """PendingApproval | Approved | Rejected | Published."""
            domain = [EmissionCycle]
            range = [str]

        class hasReportingPeriod(DataProperty):
            domain = [EmissionCycle, CalculationResult]
            range = [str]

        class hasWorkingOntologyPath(DataProperty):
            domain = [EmissionCycle]
            range = [str]

        class hasPublishedOntologyPath(DataProperty):
            domain = [EmissionCycle]
            range = [str]

        class hasObservationLifecycleStatus(DataProperty):
            """pending | corrected | confirmed | published for activity values."""
            domain = [Observation]
            range = [str]

        class hasObservationOrigin(DataProperty):
            domain = [Observation]
            range = [str]

        class isActiveResult(DataProperty):
            domain = [CalculationResult]
            range = [bool]

        class hasGWP_CH4(DataProperty):
            range = [float]

        class hasGWP_N2O(DataProperty):
            range = [float]

        class hasGWP_CO2(DataProperty):
            range = [float]

        class hasAggregationStrategy(DataProperty):
            range = [str]

        class hasCompatibilityMode(DataProperty):
            range = [str]

        class hasSourceLayout(DataProperty):
            range = [str]

        class requiresGWPParameterSet(DataProperty):
            range = [bool]

        # ------------------------------------------------------------------ #
        # Minimal restrictions (structural)
        # ------------------------------------------------------------------ #
        DataRecord.is_a.append(hasOrganizationalContext.some(OrganizationalContext))
        DataRecord.is_a.append(hasTemporalContext.some(TemporalContext))

        Observation.is_a.append(observesVariable.some(CanonicalVariable))
        Observation.is_a.append(hasOrganizationalContext.some(OrganizationalContext))
        Observation.is_a.append(hasTemporalContext.some(TemporalContext))

        QuantitativeObservation.is_a.append(hasNumericValue.some(float))
        QuantitativeObservation.is_a.append(hasUnit.some(Unit))

        QualitativeObservation.is_a.append(hasTextValue.some(str))

        CalculationExecution.is_a.append(hasCalculationMethod.some(CalculationMethod))
        CalculationExecution.is_a.append(hasOrganizationalContext.some(OrganizationalContext))
        CalculationExecution.is_a.append(hasTemporalContext.some(TemporalContext))

        EmissionCalculationExecution.is_a.append(
            generatesCalculationResult.some(EmissionResult)
        )

        EmissionResult.is_a.append(calculatesGas.some(GreenhouseGas))
        EmissionResult.is_a.append(calculatesEmissionSource.some(EmissionSource))
        EmissionResult.is_a.append(hasNumericResult.some(float))
        EmissionResult.is_a.append(hasResultUnit.some(str))

        CO2EquivalentResult.is_a.append(usesGWPParameterSet.some(GWPParameterSet))

    return onto


# Registry for validators and tests
REQUIRED_CLASSES = [
    "Context", "OrganizationalContext", "TemporalContext",
    "FarmEntity", "Property", "Animal", "Location", "EmissionCycle",
    "DataRecord", "AnnualPropertyInventoryRecord", "MonthlyPropertyRecord",
    "DailyAnimalProductionRecord", "DailyAnimalNutritionRecord",
    "Observation", "QuantitativeObservation", "QualitativeObservation",
    "FeedInputObservation", "HerdCountObservation", "AnimalWeightObservation",
    "MilkProductionObservation", "MilkCompositionObservation", "MilkSalesObservation",
    "EnergyUseObservation", "FuelUseObservation", "FertilizerUseObservation",
    "LandUseObservation", "SoilTypeObservation", "NutritionObservation",
    "EconomicObservation", "EmissionObservation", "DestinationObservation",
    "ResponsiblePersonObservation", "AdministrativeObservation",
    "CanonicalVariable", "FeedVariable", "HerdVariable", "WeightVariable",
    "MilkVariable", "MilkCompositionVariable", "EnergyVariable", "FuelVariable",
    "FertilizerVariable", "LandVariable", "SoilVariable", "NutritionVariable",
    "EmissionVariable", "EconomicVariable", "AdministrativeVariable",
    "Unit",
    "CalculationEntity", "CalculationMethod", "EmissionCalculationMethod",
    "ConversionCalculationMethod", "ConfigurationMethod",
    "EntericFermentationCH4CalculationMethod", "ManureManagementCH4CalculationMethod",
    "FertilizerN2OCalculationMethod", "EnergyCO2CalculationMethod",
    "TotalGHGCO2eCalculationMethod", "MonthlyToAnnualSumMethod",
    "MonthlyToAnnualProrationMethod", "DefaultConfigurationProvider",
    "CalculationExecution", "EmissionCalculationExecution",
    "ConversionCalculationExecution", "BatchCalculationExecution",
    "LegacyCompatibilityExecution", "CalculationInput", "ObservationInput",
    "ParameterInput", "EmissionFactorInput", "GWPInput", "ConvertedInput",
    "CalculationParameter", "EmissionFactor", "GWPParameterSet",
    "CalculationResult", "EmissionResult", "CH4EmissionResult", "N2OEmissionResult",
    "CO2EmissionResult", "CO2EquivalentResult", "ProductivityResult", "DMIResult",
    "AggregatedResult",
    "GreenhouseGas", "CarbonDioxide", "Methane", "NitrousOxide",
    "EmissionSource", "EntericFermentation", "ManureManagement",
    "FertilizerApplication", "EnergyUse", "TotalGHG",
    "SoftwareComponent", "SoftwareFunction", "BatchCalculationRunner",
    "LegacyCompatibilityAdapter",
]

REQUIRED_OBJECT_PROPERTIES = [
    "hasOrganizationalContext", "hasTemporalContext", "refersToProperty",
    "refersToAnimal", "belongsToCycle", "hasPreviousResult",
    "hasObservation", "observesVariable", "hasUnit",
    "belongsToRecord", "hasRecordType", "hasCalculationMethod",
    "implementedByFunction", "implementedInSoftwareComponent", "calculatesGas",
    "calculatesEmissionSource", "requiresInputVariable", "usesEmissionFactor",
    "usesGWPParameterSet", "hasCalculationInput", "generatesCalculationResult",
    "hasPartialResult", "hasTotalResult", "convertsFromGranularity",
    "convertsToGranularity", "usesObservation", "usesCanonicalVariable",
]

REQUIRED_DATA_PROPERTIES = [
    "hasIdentifier", "hasPropertyName", "hasOwnerName", "hasInformationResponsible",
    "hasLocationName", "hasOrganizationalGranularity", "hasTemporalType",
    "hasTemporalGranularity", "hasStartDate", "hasEndDate", "hasYear", "hasDate",
    "hasNumericValue", "hasTextValue", "hasCanonicalName", "hasDisplayName",
    "hasOriginalColumnName", "hasExpectedUnit", "hasFunctionName", "hasModulePath",
    "hasFormulaExpression", "hasCalculationVersion", "hasMethodDescription",
    "hasParameterName", "hasParameterValue", "hasParameterLifecycleStatus",
    "hasNumericResult", "hasResultUnit",
    "hasResultLifecycleStatus", "hasResultKey", "hasCO2eValue", "hasCO2eUnit",
    "hasFormulaId", "hasMethodId", "hasMethodVersion", "hasCalculatedAt",
    "hasOntologyVersion", "hasCycleId", "hasCycleStatus", "hasReportingPeriod",
    "hasWorkingOntologyPath", "hasPublishedOntologyPath",
    "hasObservationLifecycleStatus", "hasObservationOrigin", "isActiveResult",
    "hasGWP_CH4", "hasGWP_N2O", "hasGWP_CO2", "hasAggregationStrategy",
    "hasCompatibilityMode", "hasSourceLayout", "requiresGWPParameterSet",
]
