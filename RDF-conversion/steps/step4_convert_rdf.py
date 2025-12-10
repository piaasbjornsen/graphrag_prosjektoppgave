#!/usr/bin/env python3
"""
Step 4: Convert to Final RDF

Creates the final RDF file using:
- Entities with DBpedia types
- Relationships with DBpedia predicates

Output: graphrag_dbo.ttl
"""

from config import (
    MAPPED_DATA, FINAL_RDF, OUTPUT_DIR,
    GRAPHRAG_NS, DBO_NS, FALLBACK_TYPE
)
import json
import sys
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef

sys.path.insert(0, str(Path(__file__).parent.parent))


# Namespaces
GRAPHRAG = Namespace(GRAPHRAG_NS)
DBO = Namespace(DBO_NS)


def create_entity_uri(name: str, entity_id: str) -> str:
    """Create URI-safe identifier for an entity."""
    safe_name = quote(name.replace(" ", "_"), safe="")
    return f"{safe_name}_{entity_id}"


def convert_to_rdf(data: dict) -> Graph:
    """
    Convert mapped data to RDF graph.
    """
    print("\nBuilding RDF graph...")

    graph = Graph()
    graph.bind("gr", GRAPHRAG)
    graph.bind("dbo", DBO)

    # Build entity lookup: name -> {uri, type_uri}
    entity_lookup = {}

    # Create type lookup: original_type -> dbo_uri
    type_lookup = {
        orig: info["dbo_uri"]
        for orig, info in data["types"].items()
    }

    # Create predicate lookup: original_description -> dbo_uri
    pred_lookup = {
        orig: info["dbo_uri"]
        for orig, info in data["predicates"].items()
    }

    # -------------------------------------------------------------------------
    # Add entities
    # -------------------------------------------------------------------------
    print("  Adding entities...")
    entities_added = 0
    entities_typed = 0
    entities_fallback = 0

    for entity in data["entities"]:
        entity_id = entity["id"]
        name = entity["name"]
        orig_type = entity.get("original_type", "")

        # Create entity URI
        uri_id = create_entity_uri(name, entity_id)
        entity_uri = GRAPHRAG[uri_id]

        # Store in lookup
        entity_lookup[name] = entity_uri

        # Add label
        graph.add((entity_uri, RDFS.label, Literal(name)))

        # Add type - use mapped type if available, otherwise fallback to owl:Thing
        # This ensures all entities have at least one type for SDType/SDValidate
        # See: Paulheim & Bizer (2014) "Improving the Quality of Linked Data Using Statistical Distributions"
        if orig_type and orig_type in type_lookup:
            type_uri = URIRef(type_lookup[orig_type])
            graph.add((entity_uri, RDF.type, type_uri))
            entities_typed += 1
        else:
            # Fallback type for entities without a mapped type
            # SDType can infer proper types from relationship patterns
            graph.add((entity_uri, RDF.type, URIRef(FALLBACK_TYPE)))
            entities_fallback += 1

        entities_added += 1

    print(f"    {entities_added} entities ({entities_typed} with DBpedia types, {entities_fallback} with owl:Thing fallback)")

    # -------------------------------------------------------------------------
    # Add relationships
    # -------------------------------------------------------------------------
    print("  Adding relationships...")
    rels_added = 0
    rels_skipped = 0

    for rel in data["relationships"]:
        source_name = rel["source"]
        target_name = rel["target"]
        orig_desc = rel.get("original_description", "")

        # Look up entity URIs
        source_uri = entity_lookup.get(source_name)
        target_uri = entity_lookup.get(target_name)

        if not source_uri or not target_uri:
            rels_skipped += 1
            continue

        # Get predicate URI
        if orig_desc and orig_desc in pred_lookup:
            pred_uri = URIRef(pred_lookup[orig_desc])
        else:
            pred_uri = DBO.wikiPageWikiLink  # Fallback

        graph.add((source_uri, pred_uri, target_uri))
        rels_added += 1

    print(f"    {rels_added} relationships ({rels_skipped} skipped)")

    return graph


def run():
    """Run step 4."""
    print("Step 4: Converting to RDF")
    print("=" * 60)

    # Load mapped data
    if not MAPPED_DATA.exists():
        print(f"Error: {MAPPED_DATA} not found. Run step 3 first.")
        return None

    with open(MAPPED_DATA) as f:
        data = json.load(f)

    print(
        f"Loaded {len(data['entities'])} entities and {len(data['relationships'])} relationships")

    # Convert to RDF
    graph = convert_to_rdf(data)

    # Serialize
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nSerializing to: {FINAL_RDF}")
    graph.serialize(destination=str(FINAL_RDF), format="turtle")

    print(f"  Total triples: {len(graph)}")
    print(f"\n✓ Saved to: {FINAL_RDF}")

    # Show sample
    print("\n" + "-" * 60)
    print("Sample output (first 30 lines):")
    with open(FINAL_RDF) as f:
        for i, line in enumerate(f):
            if i >= 30:
                print("...")
                break
            print(line.rstrip())

    return graph


if __name__ == "__main__":
    run()
