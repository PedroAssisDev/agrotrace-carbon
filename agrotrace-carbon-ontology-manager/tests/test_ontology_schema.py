"""Tests for AgroMRV-O Lite schema."""

from ontology.schema import (
    REQUIRED_CLASSES,
    REQUIRED_DATA_PROPERTIES,
    REQUIRED_OBJECT_PROPERTIES,
)


def test_base_ontology_classes_created(base_ontology):
    onto = base_ontology
    for cls_name in REQUIRED_CLASSES:
        assert hasattr(onto, cls_name), f"Missing class {cls_name}"


def test_base_ontology_properties_created(base_ontology):
    onto = base_ontology
    for prop_name in REQUIRED_OBJECT_PROPERTIES:
        assert hasattr(onto, prop_name), f"Missing object property {prop_name}"
    for prop_name in REQUIRED_DATA_PROPERTIES:
        assert hasattr(onto, prop_name), f"Missing data property {prop_name}"
