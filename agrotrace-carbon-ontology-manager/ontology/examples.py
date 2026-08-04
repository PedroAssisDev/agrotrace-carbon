"""End-to-end example: build, populate, export AgroMRV-O Lite."""

from __future__ import annotations

from pathlib import Path

from ontology.builder import build_full_ontology
from ontology.exporters import export_ontology
from ontology.population import populate_from_dataframe, read_dataframe_from_csv_string

ANNUAL_CSV = """\
_organizational_context;_;_temporal_context;_;calves;_;calves_weight;_;dry_cows;_;dry_cows_weight;_;lactating_cows;_;lactating_cows_weight;_;maize_silage;_;diesel;_;electricity_grid;_;milk_fat_percentage;_;milk_protein_percentage;_;pasture_area;_;predominant_soil_type;_;total_milk_production;_;property_name;_;owner_name;_;information_responsible;_;year
{"granularity":"property","identifier":"BR – 1"};_;{"type":"interval","start":"2026-01-01","end":"2026-12-31","granularity":"year"};_;15.0;_;150.0;_;4.0;_;530.0;_;13.0;_;500.0;_;47168.95;_;88410.3;_;41241.35;_;4.13;_;3.32;_;3.0;_;Latossolo Vermelho-Amarelo;_;73384.41;_;BR – 1;_;Anonymous;_;Anonymous;_;2026"""

DAILY_CSV = """\
_organizational_context;_;_temporal_context;_;animal_id;_;date;_;milk;_;weight
{"granularity":"property","identifier":"BR – 1"};_;{"type":"instant","date":"2026-01-15","granularity":"day"};_;A123;_;2026-01-15;_;22.4;_;520.0"""

DAILY_NUTRITION_CSV = """\
_organizational_context;_;_temporal_context;_;animal_id;_;date;_;milk;_;weight;_;energy_density;_;dry_matter_intake
{"granularity":"property","identifier":"BR – 1"};_;{"type":"instant","date":"2026-01-15","granularity":"day"};_;A123;_;2026-01-15;_;22.4;_;520.0;_;6.5;_;18.2"""

MONTHLY_CSV = """\
_organizational_context;_;_temporal_context;_;area_used_for_dairy_activity;_;draft_and_breeding_bulls;_;dry_cows;_;ef_enteric_kg_ch4;_;employees_during_the_month;_;enteric_tco2e;_;heifers_in_raising;_;lactating_cows;_;milk_gross_price;_;milk_production;_;milk_sales;_;number_of_dry_cows;_;number_of_lactating_cows;_;period_end;_;period_start;_;property_id
{"granularity":"property","identifier":"BR – 1"};_;{"type":"interval","start":"2026-01-01","end":"2026-01-31","granularity":"month"};_;3.0;_;0;_;4;_;4.0;_;2;_;2.5;_;8;_;13;_;2.3;_;6200.0;_;6000.0;_;4;_;13;_;2026-01-31;_;2026-01-01;_;BR – 1"""


def main() -> None:
    onto = build_full_ontology()

    populate_from_dataframe(
        onto, read_dataframe_from_csv_string(ANNUAL_CSV), layout_name="annual_inventory"
    )
    populate_from_dataframe(
        onto, read_dataframe_from_csv_string(DAILY_CSV), layout_name="daily_production"
    )
    populate_from_dataframe(
        onto,
        read_dataframe_from_csv_string(DAILY_NUTRITION_CSV),
        layout_name="daily_nutrition",
    )
    populate_from_dataframe(
        onto, read_dataframe_from_csv_string(MONTHLY_CSV), layout_name="monthly_property"
    )

    out_dir = Path("artifacts/ontology")
    export_ontology(onto, str(out_dir / "agromrv_lite.owl"), format="rdfxml")
    export_ontology(onto, str(out_dir / "agromrv_lite.rdf"), format="rdf")
    export_ontology(onto, str(out_dir / "agromrv_lite.ttl"), format="turtle")
    export_ontology(onto, str(out_dir / "agromrv_lite_instances.owl"), format="owl")

    print("AgroMRV-O Lite exported to artifacts/ontology/")


if __name__ == "__main__":
    main()
