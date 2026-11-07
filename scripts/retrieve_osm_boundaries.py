# SPDX-FileCopyrightText: : 2020-2024 The PyPSA-Eur Authors
#
# SPDX-License-Identifier: MIT
"""
Retrieve administrative boundaries for the specified country using the overpass API and save it
to the specified output files.

Note that overpass requests are based on a fair
use policy. `retrieve_osm_data` is meant to be used in a way that respects this
policy by fetching the needed data once, only.
"""

import json
import logging
import time

import requests

from scripts._helpers import (  # set_scenario_config,; update_config_from_wildcards,; update_config_from_wildcards,
    configure_logging,
    set_scenario_config,
)

logger = logging.getLogger(__name__)


ADM1_SPECIALS = {
    "XK": 5,
}

# Public Overpass API instances, tried in order (see
# https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances)
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",  # Germany (main instance)
    "https://overpass.kumi.systems/api/interpreter",  # Switzerland
    "https://overpass.private.coffee/api/interpreter",  # Austria
]

USER_AGENT = "PyPSA-Eur (https://github.com/PyPSA/pypsa-eur)"


def retrieve_osm_boundaries(
    country,
    adm1_specials,
    output,
):
    """
    Retrieve OSM administrative boundaries for the specified country and save it to the specified
    output files.

    Parameters
    ----------
    country : str
        The country code for which the OSM data should be retrieved.
    """
    wait_time = 5

    osm_adm_level = "4"
    if country in adm1_specials:
        osm_adm_level = adm1_specials[country]  # special case e.g. for Kosovo

    # Build the overpass query
    op_area = f'area["ISO3166-1"="{country}"]'
    op_query = f"""
        [out:json];
        {op_area}->.searchArea;
        (
        relation["boundary"="administrative"]["admin_level"={osm_adm_level}]["name"](area.searchArea);
        );
        out body geom;
    """

    retries = 3
    for attempt in range(retries):
        # Try each server in turn within one attempt
        for overpass_url in OVERPASS_URLS:
            logger.info(
                f" - Fetching OSM administrative boundaries for {country} from "
                f"{overpass_url} (attempt {attempt + 1})..."
            )
            response = None
            try:
                # overpass-api.de rejects the default python-requests User-Agent (406)
                response = requests.post(
                    overpass_url,
                    data={"data": op_query},
                    headers={"User-Agent": USER_AGENT},
                    timeout=600,
                )
                response.raise_for_status()
                data = response.json()

                with open(output[0], mode="w") as f:
                    json.dump(data, f, indent=2)
                logger.info(" - Done.")
                return
            except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
                logger.error(
                    f"Error retrieving administrative boundaries for {country} "
                    f"from {overpass_url}: {e}"
                )
                if response is not None:
                    logger.debug(f"Response text: {response.text[:1000]}")

        if attempt < retries - 1:
            wait_time += 15
            logger.info(f"All servers failed. Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)

    raise RuntimeError(
        f"Failed to retrieve administrative boundaries for {country} from all "
        f"Overpass servers after {retries} attempts."
    )


if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake("retrieve_osm_boundaries", country="XK")
    configure_logging(snakemake)
    set_scenario_config(snakemake)

    # Retrieve the OSM data
    country = snakemake.wildcards.country
    output = snakemake.output

    retrieve_osm_boundaries(country, ADM1_SPECIALS, output)
