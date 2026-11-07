# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Build administrative level 1 boundaries for non-NUTS countries from
geoBoundaries (https://www.geoboundaries.org) data.

Alternative to ``build_osm_boundaries`` when the Overpass API is unavailable.
The output has the same format: columns ``id``, ``country``, ``name``,
``osm_id`` (here the geoBoundaries ``shapeID``) and ``geometry``, clipped by
the offshore shapes.
"""

import logging

import geopandas as gpd

from scripts._helpers import configure_logging, set_scenario_config
from scripts.build_shapes import eez

logger = logging.getLogger(__name__)

GEO_CRS = "EPSG:4326"


def build_geoboundaries_adm1(country, adm1_path, offshore_shapes):
    """
    Build administrative boundaries from geoBoundaries data for a given country.

    Parameters
    ----------
        - country (str): The two-letter country code (e.g. 'BA').
        - adm1_path (str): Path to the geoBoundaries ADM1 GeoJSON file.
        - offshore_shapes (GeoDataFrame): Offshore shapes used to clip the boundaries.

    Returns
    -------
    GeoDataFrame with columns id, country, name, osm_id, geometry.
    """
    logger.info(
        f"Building administrative boundaries from geoBoundaries data for country {country}."
    )

    gdf = gpd.read_file(adm1_path).to_crs(GEO_CRS)

    gdf = gdf.rename(
        columns={"shapeISO": "id", "shapeName": "name", "shapeID": "osm_id"}
    )

    # geoBoundaries marks some ISO codes with a trailing '*' (e.g. 'BA-SRP*')
    gdf["id"] = gdf["id"].fillna("").astype(str).str.strip().str.rstrip("*")

    # If any id is missing (e.g. Kosovo), number the regions starting from 1,
    # as done in build_osm_boundaries
    if (gdf["id"] == "").any():
        gdf = gdf.sort_values(by="osm_id").reset_index(drop=True)
        gdf["id"] = country + "-" + gdf.index.to_series().add(1).astype(str)

    gdf["country"] = country
    gdf["geometry"] = gdf.geometry.make_valid()
    gdf = gdf[["id", "country", "name", "osm_id", "geometry"]]

    # Clip gdf by offshore shapes
    gdf = gpd.overlay(gdf, offshore_shapes, how="difference")

    # Keep only regions belonging to the country
    gdf = gdf[gdf["id"].str.startswith(country)]

    return gdf


if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake("build_geoboundaries_adm1", country="BA")

    configure_logging(snakemake)
    set_scenario_config(snakemake)

    country = snakemake.wildcards.country
    offshore_shapes = eez(snakemake.input.eez)

    boundaries = build_geoboundaries_adm1(
        country, snakemake.input.geojson, offshore_shapes
    )

    boundaries.to_file(snakemake.output[0], driver="GeoJSON")
