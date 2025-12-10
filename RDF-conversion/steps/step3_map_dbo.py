#!/usr/bin/env python3
"""
Step 3: Map Refined Types/Predicates to DBpedia Ontology

Uses embedding-based similarity matching to find the best DBpedia
class/property for each refined type/predicate.

Items below the similarity threshold use fallback values.

Output: step3_mapped.json
"""

from config import (
    REFINED_DATA, MAPPED_DATA, OUTPUT_DIR, CACHE_DIR,
    DBO_CLASSES_CACHE, DBO_PROPERTIES_CACHE,
    TYPE_SIMILARITY_THRESHOLD, PREDICATE_SIMILARITY_THRESHOLD,
    EMBEDDING_MODEL, DBPEDIA_SPARQL_ENDPOINT,
    FALLBACK_PREDICATE, DBO_NS
)
import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from SPARQLWrapper import SPARQLWrapper, JSON

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# DBPEDIA ONTOLOGY FETCHERS
# ============================================================================

def fetch_dbo_classes() -> dict[str, str]:
    """Fetch DBpedia ontology classes via SPARQL."""
    print("  Fetching DBpedia classes via SPARQL...")

    sparql = SPARQLWrapper(DBPEDIA_SPARQL_ENDPOINT)
    sparql.setReturnFormat(JSON)
    sparql.setQuery("""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        
        SELECT DISTINCT ?class ?label ?comment WHERE {
            ?class a owl:Class .
            FILTER(STRSTARTS(STR(?class), "http://dbpedia.org/ontology/"))
            OPTIONAL { ?class rdfs:label ?label . FILTER(LANG(?label) = "en") }
            OPTIONAL { ?class rdfs:comment ?comment . FILTER(LANG(?comment) = "en") }
        }
    """)

    try:
        results = sparql.query().convert()["results"]["bindings"]
    except Exception as e:
        print(f"  SPARQL failed: {e}")
        return {}

    classes = {}
    for r in results:
        uri = r["class"]["value"]
        name = uri.replace("http://dbpedia.org/ontology/", "")
        if "/" in name or "(" in name:
            continue
        label = r.get("label", {}).get("value", name)
        comment = r.get("comment", {}).get("value", "")
        classes[name] = f"{label}: {comment}" if comment else label

    print(f"  Found {len(classes)} classes")
    return classes


def fetch_dbo_properties() -> dict[str, str]:
    """Fetch DBpedia ontology properties via SPARQL."""
    print("  Fetching DBpedia properties via SPARQL...")

    sparql = SPARQLWrapper(DBPEDIA_SPARQL_ENDPOINT)
    sparql.setReturnFormat(JSON)
    sparql.setQuery("""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?prop ?label ?comment WHERE {
            { ?prop a owl:ObjectProperty }
            UNION
            { ?prop a rdf:Property }
            FILTER(STRSTARTS(STR(?prop), "http://dbpedia.org/ontology/"))
            OPTIONAL { ?prop rdfs:label ?label . FILTER(LANG(?label) = "en") }
            OPTIONAL { ?prop rdfs:comment ?comment . FILTER(LANG(?comment) = "en") }
        }
    """)

    try:
        results = sparql.query().convert()["results"]["bindings"]
    except Exception as e:
        print(f"  SPARQL failed: {e}")
        return {}

    props = {}
    for r in results:
        uri = r["prop"]["value"]
        name = uri.replace("http://dbpedia.org/ontology/", "")
        if "/" in name:
            continue
        label = r.get("label", {}).get("value", name)
        comment = r.get("comment", {}).get("value", "")
        props[name] = f"{label}: {comment}" if comment else label

    print(f"  Found {len(props)} properties")
    return props


def load_or_fetch(cache_file: Path, fetch_func) -> dict[str, str]:
    """Load from cache or fetch and cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        print(f"  Loading from cache: {cache_file.name}")
        with open(cache_file) as f:
            data = json.load(f)
        print(f"  Loaded {len(data)} items")
        return data

    data = fetch_func()
    if data:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  Cached to {cache_file.name}")
    return data


# ============================================================================
# EMBEDDING-BASED MAPPER
# ============================================================================

class EmbeddingMapper:
    """Maps terms to DBpedia using embedding similarity."""

    def __init__(self):
        self.model = None
        self._embeddings = {}

    def _load_model(self):
        if self.model is None:
            print(f"  Loading embedding model: {EMBEDDING_MODEL}")
            self.model = SentenceTransformer(EMBEDDING_MODEL)

    def _get_embeddings(self, texts: list[str], key: str):
        """Get embeddings with caching."""
        if key not in self._embeddings:
            self._load_model()
            print(f"  Computing embeddings for {len(texts)} {key}...")
            self._embeddings[key] = self.model.encode(
                texts, normalize_embeddings=True, show_progress_bar=True
            )
        return self._embeddings[key]

    def find_best_match(
        self,
        query: str,
        candidates: dict[str, str],
        cache_key: str
    ) -> tuple[str, float]:
        """Find best matching candidate using cosine similarity."""
        self._load_model()

        names = list(candidates.keys())
        descriptions = list(candidates.values())

        cand_emb = self._get_embeddings(descriptions, cache_key)
        query_emb = self.model.encode([query], normalize_embeddings=True)[0]

        similarities = np.dot(cand_emb, query_emb)
        best_idx = np.argmax(similarities)

        return names[best_idx], float(similarities[best_idx])


def map_to_dbo(data: dict, dbo_classes: dict, dbo_props: dict) -> dict:
    """
    Map refined types and predicates to DBpedia ontology.
    """
    mapper = EmbeddingMapper()

    # -------------------------------------------------------------------------
    # Map types to DBpedia classes
    # -------------------------------------------------------------------------
    print("\nMapping types to DBpedia classes...")
    print(f"  Threshold: {TYPE_SIMILARITY_THRESHOLD}")

    mapped_types = {}
    type_mapped = type_fallback = 0

    for orig_type, info in data["types"].items():
        refined = info["refined"]
        best_class, score = mapper.find_best_match(
            refined, dbo_classes, "classes")

        if score >= TYPE_SIMILARITY_THRESHOLD:
            mapped_types[orig_type] = {
                **info,
                "dbo_class": best_class,
                "dbo_uri": f"{DBO_NS}{best_class}",
                "similarity": round(score, 3)
            }
            type_mapped += 1
        else:
            # Fallback: use dbo:Thing
            mapped_types[orig_type] = {
                **info,
                "dbo_class": "Thing",
                "dbo_uri": f"{DBO_NS}Thing",
                "similarity": round(score, 3),
                "fallback": True,
                "best_match": best_class
            }
            type_fallback += 1

        print(
            f"    {refined:25} → dbo:{mapped_types[orig_type]['dbo_class']:20} [{score:.3f}]")

    print(
        f"  Results: {type_mapped} mapped, {type_fallback} fallback to Thing")

    # -------------------------------------------------------------------------
    # Map predicates to DBpedia properties
    # -------------------------------------------------------------------------
    print("\nMapping predicates to DBpedia properties...")
    print(f"  Threshold: {PREDICATE_SIMILARITY_THRESHOLD}")

    mapped_predicates = {}
    pred_mapped = pred_fallback = 0

    for orig_desc, info in data["predicates"].items():
        refined = info["refined"]
        best_prop, score = mapper.find_best_match(
            refined, dbo_props, "properties")

        if score >= PREDICATE_SIMILARITY_THRESHOLD:
            mapped_predicates[orig_desc] = {
                **info,
                "dbo_property": best_prop,
                "dbo_uri": f"{DBO_NS}{best_prop}",
                "similarity": round(score, 3)
            }
            pred_mapped += 1
        else:
            # Fallback: use generic link predicate
            mapped_predicates[orig_desc] = {
                **info,
                "dbo_property": FALLBACK_PREDICATE,
                "dbo_uri": f"{DBO_NS}{FALLBACK_PREDICATE}",
                "similarity": round(score, 3),
                "fallback": True,
                "best_match": best_prop
            }
            pred_fallback += 1

    # Show progress
    total = len(mapped_predicates)
    print(
        f"  Results: {pred_mapped} mapped, {pred_fallback} fallback to {FALLBACK_PREDICATE}")

    return {
        "types": mapped_types,
        "predicates": mapped_predicates,
        "entities": data["entities"],
        "relationships": data["relationships"]
    }


def run():
    """Run step 3."""
    print("Step 3: Mapping to DBpedia Ontology")
    print("=" * 60)

    # Load refined data
    if not REFINED_DATA.exists():
        print(f"Error: {REFINED_DATA} not found. Run step 2 first.")
        return None

    with open(REFINED_DATA) as f:
        data = json.load(f)

    print(
        f"Loaded {len(data['types'])} types and {len(data['predicates'])} predicates")

    # Load DBpedia ontology
    print("\nLoading DBpedia ontology...")
    dbo_classes = load_or_fetch(DBO_CLASSES_CACHE, fetch_dbo_classes)
    dbo_props = load_or_fetch(DBO_PROPERTIES_CACHE, fetch_dbo_properties)

    if not dbo_classes or not dbo_props:
        print("Error: Could not load DBpedia ontology")
        return None

    # Map to DBpedia
    mapped = map_to_dbo(data, dbo_classes, dbo_props)

    # Save output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(MAPPED_DATA, 'w') as f:
        json.dump(mapped, f, indent=2)

    print(f"\n✓ Saved to: {MAPPED_DATA}")
    return mapped


if __name__ == "__main__":
    run()
