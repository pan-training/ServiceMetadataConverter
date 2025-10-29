from rdflib import Graph, RDF, Namespace
from bs4 import BeautifulSoup
from slugify import slugify
import requests
import json
import argparse

SDO = Namespace("http://schema.org/")  # The SDO import from rdflib is a https url
DEFAULT_SOURCE_URL = "https://tesshub.hzdr.de/materials?collections=PaNOSC+Node+Service+Collection"
DEFAULT_TARGET_LOCATION = "services.json"


def get_metadata_graph(source_url):
    graph = Graph()

    for page in range(1, 1000):
        empty_page = True

        html = requests.get(source_url, params={"page": page}).text
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            if data := script.string:
                empty_page = False
                graph.parse(data=data, format="json-ld")

        if empty_page:
            break

    return graph


def serialize_service(service_iri, metadata: Graph):
    def val(predicate):
        return metadata.value(service_iri, predicate)
    
    def keyword_map(default=None, **kwargs):
        results = [v for k in keywords if (v := kwargs.get(slugify(k, separator="_")))]
        if default is not None and not results:
            results.append(default)
        return results
    
    name = val(SDO.name)
    slug = slugify(name)
    service_id = f"panosc-node:services:{slug}"
    keywords = list(metadata.objects(service_iri, SDO.keywords))

    return {
        "id": service_id,
        "service": {
            # properties from PaN-Training
            "id": service_id,
            "name": name,
            "webpage": val(SDO.url),
            "description": val(SDO.description),
            "tags": keywords,

            "scientificDomains": keyword_map(  # https://github.com/EOSC-Lot-1/een-resource-catalogue-docs/blob/eosc/vocabularies/SCIENTIFIC_DOMAIN.json
                default={"scientificDomain": "scientific_domain-natural_sciences"},
                generic={"scientificDomain": "scientific_domain-generic"},
                pan={"scientificDomain": "scientific_domain-natural_sciences"},
                photon={"scientificDomain": "scientific_domain-natural_sciences"},
                neutron={"scientificDomain": "scientific_domain-natural_sciences"},
                agriculture={"scientificDomain": "scientific_domain-agricultural_sciences"},
                engineering={"scientificDomain": "scientific_domain-engineering_and_technology"},
                humanities={"scientificDomain": "scientific_domain-humanities"},
                health={"scientificDomain": "scientific_domain-medical_and_health_sciences"},
                social={"scientificDomain": "scientific_domain-social_sciences"},
            ),
            "categories": keyword_map(  # https://github.com/EOSC-Lot-1/een-resource-catalogue-docs/blob/eosc/vocabularies/CATEGORY.json
                default={"category": "category-other-other"},
                compute_hardware={"category": "category-access_physical_and_eInfrastructures-compute"},
                storage_hardware={"category": "category-access_physical_and_eInfrastructures-data_storage"},
                network_hardware={"category": "category-access_physical_and_eInfrastructures-network"},
                equipment={"category": "category-access_physical_and_eInfrastructures-instrument_and_equipment"},
                storage={"category": "category-access_physical_and_eInfrastructures-material_storage"},
                aggregation={"category": "category-aggregators_and_integrators-aggregators_and_integrators"},
                data_analysis={"category": "category-processing_and_analysis-data_analysis"},
                data_management={"category": "category-processing_and_analysis-data_management"},
                access_control={"category": "category-security_and_operations-security_and_identity"},
                discovery={"category": "category-sharing_and_discovery-applications"},
                data={"category": "category-sharing_and_discovery-data"},
                dev={"category": "category-sharing_and_discovery-development_resources"},
                samples={"category": "category-sharing_and_discovery-samples"},
                scholarly_communication={"category": "category-sharing_and_discovery-scholarly_communication"},
                consultancy={"category": "category-training_and_support-consultancy_and_support"},
                training={"category": "category-training_and_support-education_and_training"},
            ),
            "targetUsers": keyword_map(  # https://github.com/EOSC-Lot-1/een-resource-catalogue-docs/blob/eosc/vocabularies/TARGET_USER.json
                default="target_user-researchers",
                funders="target_user-funders",
                providers="target_user-providers",
                organisations="target_user-research_organisations",
                publishers="target_user-publishers",
                students="target_user-students",
            ),
            "languageAvailabilities": ["EN"],
            "trl": keyword_map(  # https://github.com/EOSC-Lot-1/een-resource-catalogue-docs/blob/eosc/vocabularies/TRL.json
                default="trl-8",
                concept="trl-2",
                prototype="trl-7",
                mature="trl-9",
            )[0],
            "orderType": keyword_map(  # https://github.com/madgeek-arc/resource-catalogue-docs/blob/master/vocabularies/ORDER_TYPE.json
                default="order_type-fully_open_access",
                login_required="order_type-open_access",
            )[0]
        }
    }


def main(argv=None):
    args = parser.parse_args(argv)

    metadata = get_metadata_graph(args.source_url)
    if args.debug:
        print(metadata.serialize())
    serialized = [serialize_service(s, metadata) for s in metadata.subjects(RDF.type, SDO.LearningResource)]
    with open(args.target_location, "w") as f:
        json.dump(serialized, f, indent=3)
    print(f"wrote {len(serialized)} services to {args.target_location}")


parser = argparse.ArgumentParser(
    description="Extracts JSON-LD metadata from an HTML page and produces EOSC service metadata."
)
parser.add_argument(
    "-s", "--source-url",
    default=DEFAULT_SOURCE_URL,
    help=f"URL to fetch HTML from (default: {DEFAULT_SOURCE_URL})",
)
parser.add_argument(
    "-t", "--target-location",
    default=DEFAULT_TARGET_LOCATION,
    help=f"File path to write JSON output (default: {DEFAULT_TARGET_LOCATION})",
)
parser.add_argument(
    "-d", "--debug",
    action="store_true",
    help="Print the full RDF metadata graph for debugging.",
)

if __name__ == "__main__":
    main()
