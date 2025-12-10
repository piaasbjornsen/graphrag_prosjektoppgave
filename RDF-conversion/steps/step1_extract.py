#!/usr/bin/env python3
"""
Step 1: Extract Types and Predicates from GraphRAG Parquet Files

Reads the GraphRAG parquet output and extracts:
- All unique entity types
- All unique relationship descriptions (which become predicates)

Output: step1_extracted.json
"""

from config import (
    ENTITIES_PARQUET, RELATIONSHIPS_PARQUET,
    EXTRACTED_DATA, OUTPUT_DIR, PIPELINE_DIR
)
import json
import re
import sys
from pathlib import Path

import pandas as pd

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def clean_string(s: str) -> str:
    """Clean GraphRAG string (remove quotes, LLM artifacts)."""
    if pd.isna(s) or not s:
        return ""
    s = str(s).strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    s = re.sub(r'<\|[A-Z]+\|>', '', s)
    s = re.sub(r'\)\s*\("entity".*$', '', s)
    return s.strip()


def extract_types_and_predicates(
    entities_path: Path,
    relationships_path: Path
) -> dict:
    """
    Extract all unique types and predicates from GraphRAG parquet files.

    Returns:
        Dictionary with:
        - types: {type_name: {count, example_entities}}
        - predicates: {description: {count, example_source, example_target}}
        - entities: [{id, name, type}]
        - relationships: [{source, target, description}]
    """
    print("Step 1: Extracting types and predicates from parquet files")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # Extract entities and types
    # -------------------------------------------------------------------------
    print(f"\nReading entities from: {entities_path}")
    entities_df = pd.read_parquet(entities_path)

    entities = []
    types = {}

    for _, row in entities_df.iterrows():
        entity_id = row['id']
        name = clean_string(row['name'])
        entity_type = clean_string(row.get('type', ''))

        entities.append({
            "id": entity_id,
            "name": name,
            "original_type": entity_type
        })

        if entity_type:
            if entity_type not in types:
                types[entity_type] = {
                    "count": 0,
                    "example_entities": []
                }
            types[entity_type]["count"] += 1
            if len(types[entity_type]["example_entities"]) < 3:
                types[entity_type]["example_entities"].append(name)

    print(f"  Found {len(entities)} entities")
    print(f"  Found {len(types)} unique types")

    # -------------------------------------------------------------------------
    # Extract relationships and predicates
    # -------------------------------------------------------------------------
    print(f"\nReading relationships from: {relationships_path}")
    rels_df = pd.read_parquet(relationships_path)

    relationships = []
    predicates = {}

    for _, row in rels_df.iterrows():
        source = clean_string(row['source'])
        target = clean_string(row['target'])
        description = clean_string(row.get('description', ''))

        relationships.append({
            "source": source,
            "target": target,
            "original_description": description
        })

        if description:
            if description not in predicates:
                predicates[description] = {
                    "count": 0,
                    "example_source": source,
                    "example_target": target
                }
            predicates[description]["count"] += 1

    print(f"  Found {len(relationships)} relationships")
    print(f"  Found {len(predicates)} unique predicates/descriptions")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("Types found:")
    for t, info in sorted(types.items(), key=lambda x: -x[1]["count"])[:10]:
        print(f"  {t:30} (count: {info['count']})")
    if len(types) > 10:
        print(f"  ... and {len(types) - 10} more")

    print("\nPredicate descriptions (sample):")
    for desc, info in list(predicates.items())[:5]:
        short_desc = desc[:50] + "..." if len(desc) > 50 else desc
        print(f"  \"{short_desc}\" (count: {info['count']})")
    if len(predicates) > 5:
        print(f"  ... and {len(predicates) - 5} more")

    return {
        "types": types,
        "predicates": predicates,
        "entities": entities,
        "relationships": relationships
    }


def run():
    """Run step 1."""
    # Resolve paths
    entities_path = (PIPELINE_DIR / ENTITIES_PARQUET).resolve()
    relationships_path = (PIPELINE_DIR / RELATIONSHIPS_PARQUET).resolve()

    if not entities_path.exists():
        print(f"Error: {entities_path} not found")
        return None
    if not relationships_path.exists():
        print(f"Error: {relationships_path} not found")
        return None

    # Extract
    data = extract_types_and_predicates(entities_path, relationships_path)

    # Save output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXTRACTED_DATA, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ Saved to: {EXTRACTED_DATA}")
    return data


if __name__ == "__main__":
    run()
