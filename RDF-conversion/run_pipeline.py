#!/usr/bin/env python3
"""
RDF Pipeline - Main Entry Point

Converts GraphRAG parquet output to DBpedia-compatible RDF.

Usage:
    python run_pipeline.py          # Run all steps
    python run_pipeline.py --step 2 # Run specific step
    python run_pipeline.py --from 3 # Run from step 3 onwards
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from steps import step1_extract, step2_refine_llm, step3_map_dbo, step4_convert_rdf
from validate_output import validate

# All pipeline steps defined once
STEPS = [
    (1, "Extract from parquet", step1_extract.run),
    (2, "Refine with LLM", step2_refine_llm.run),
    (3, "Map to DBpedia", step3_map_dbo.run),
    (4, "Convert to RDF", step4_convert_rdf.run),
]


def run_steps(from_step: int = 1, to_step: int = 4):
    """Run pipeline steps in range [from_step, to_step]."""
    print("\n" + "=" * 70)
    print("  RDF PIPELINE - GraphRAG to DBpedia RDF")
    print("=" * 70)

    for num, name, func in STEPS:
        if from_step <= num <= to_step:
            print(f"\n{'─' * 70}")
            result = func()
            if result is None:
                print(f"\n❌ Step {num} failed. Aborting.")
                return False

    # Auto-validate at end if we completed step 4
    if to_step >= 4:
        print(f"\n{'─' * 70}")
        print("VALIDATION")
        print("─" * 70)
        validate()

    print("\n" + "=" * 70)
    print("  PIPELINE COMPLETE")
    print("=" * 70)
    print("\nOutput: output/graphrag_dbo.ttl")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="RDF Pipeline: Convert GraphRAG to DBpedia RDF"
    )
    parser.add_argument(
        "--step", "-s", type=int, choices=[1, 2, 3, 4],
        help="Run only this step"
    )
    parser.add_argument(
        "--from", "-f", dest="from_step", type=int, choices=[1, 2, 3, 4],
        help="Run from this step onwards"
    )

    args = parser.parse_args()

    if args.step:
        success = run_steps(args.step, args.step)
    elif args.from_step:
        success = run_steps(args.from_step, 4)
    else:
        success = run_steps(1, 4)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
