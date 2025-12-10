#!/usr/bin/env python3
"""
Step 2: Refine Types and Predicates using LLM

Converts messy extracted types/predicates into DBpedia-style ontology terms.

Output: step2_refined.json
"""

import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    EXTRACTED_DATA, REFINED_DATA, OUTPUT_DIR,
    LLM_MODEL, LLM_BASE_URL
)
from steps.prompts import TYPE_PROMPT, PREDICATE_PROMPT

BATCH_SIZE = 10


def call_ollama(prompt: str) -> str:
    """Call Ollama API."""
    try:
        response = requests.post(
            f"{LLM_BASE_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"    LLM error: {e}")
        return ""


def check_llm_available() -> bool:
    """Check if Ollama is running."""
    try:
        response = requests.get(f"{LLM_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = [m["name"] for m in response.json().get("models", [])]
            if any(LLM_MODEL in m for m in models):
                return True
            print(f"  Model '{LLM_MODEL}' not found. Available: {models}")
        return False
    except Exception:
        return False


def heuristic_type(type_name: str) -> str:
    """Simple PascalCase conversion."""
    words = type_name.split()
    result = ''.join(word.capitalize() for word in words)
    return re.sub(r'[^a-zA-Z0-9]', '', result) or "Thing"


def heuristic_predicate(desc: str) -> str:
    """Simple camelCase extraction."""
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of',
                  'in', 'on', 'at', 'for', 'with', 'and', 'or', 'but'}
    words = [w for w in desc.lower().split() if w not in stop_words and len(w) > 2][:3]
    if words:
        result = words[0] + ''.join(w.capitalize() for w in words[1:])
        return re.sub(r'[^a-zA-Z0-9]', '', result)
    return "relatedTo"


def refine_types_batch(types_data: dict) -> dict:
    """Refine all types in one LLM call."""
    type_list = list(types_data.keys())
    items = "\n".join(f"{i+1}. \"{t}\"" for i, t in enumerate(type_list))
    
    prompt = TYPE_PROMPT.format(items=items)
    result = call_ollama(prompt)
    
    refined = {}
    for line in result.split('\n'):
        match = re.match(r'(\d+)\.\s*(\w+)', line.strip())
        if match:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(type_list):
                refined[type_list[idx]] = match.group(2)
    
    for t in type_list:
        if t not in refined:
            refined[t] = heuristic_type(t)
    
    return refined


def refine_predicates_batch(batch_items: list) -> dict:
    """
    Refine a batch of predicates in one LLM call.
    batch_items: list of (description, source, target) tuples
    """
    items = "\n".join(
        f'{i+1}. "{desc[:80]}..." | {src} → {tgt}' if len(desc) > 80 
        else f'{i+1}. "{desc}" | {src} → {tgt}'
        for i, (desc, src, tgt) in enumerate(batch_items)
    )
    
    prompt = PREDICATE_PROMPT.format(items=items)
    result = call_ollama(prompt)
    
    refined = {}
    for line in result.split('\n'):
        match = re.match(r'(\d+)\.\s*(\w+)', line.strip())
        if match:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(batch_items):
                pred = match.group(2)
                if pred:
                    pred = pred[0].lower() + pred[1:] if len(pred) > 1 else pred.lower()
                desc = batch_items[idx][0]
                refined[desc] = pred
    
    for desc, src, tgt in batch_items:
        if desc not in refined:
            refined[desc] = heuristic_predicate(desc)
    
    return refined


def run():
    """Run step 2."""
    print("\n" + "=" * 80)
    print("STEP 2: REFINE TYPES AND PREDICATES WITH LLM")
    print("=" * 80)

    if not EXTRACTED_DATA.exists():
        print(f"Error: {EXTRACTED_DATA} not found. Run step 1 first.")
        return None

    with open(EXTRACTED_DATA) as f:
        data = json.load(f)

    num_types = len(data['types'])
    num_preds = len(data['predicates'])
    print(f"\nLoaded: {num_types} types, {num_preds} predicates")

    llm_available = check_llm_available()
    
    if not llm_available:
        print(f"\n⚠ Ollama not available at {LLM_BASE_URL}")
        print("  Using heuristic refinement...")
        use_llm = False
    else:
        print(f"✓ Using LLM: {LLM_MODEL}")
        use_llm = True

    # === REFINE TYPES ===
    print("\n" + "-" * 80)
    print("ENTITY TYPES" + (" (LLM)" if use_llm else " (heuristic)"))
    print("-" * 80)
    
    if use_llm:
        type_mappings = refine_types_batch(data["types"])
    else:
        type_mappings = {t: heuristic_type(t) for t in data["types"]}
    
    refined_types = {}
    for type_name, info in data["types"].items():
        refined = type_mappings.get(type_name, heuristic_type(type_name))
        refined_types[type_name] = {**info, "refined": refined}
        print(f"  \"{type_name}\" → {refined}")

    # === REFINE PREDICATES ===
    print("\n" + "-" * 80)
    print("RELATIONSHIP PREDICATES" + (" (LLM)" if use_llm else " (heuristic)"))
    print("-" * 80)
    
    pred_items = []
    for desc, info in data["predicates"].items():
        source = info.get("example_source", "?")
        target = info.get("example_target", "?")
        pred_items.append((desc, source, target))
    
    num_batches = (len(pred_items) + BATCH_SIZE - 1) // BATCH_SIZE
    
    pred_mappings = {}
    if use_llm:
        for i in range(0, len(pred_items), BATCH_SIZE):
            batch = pred_items[i:i+BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            
            print(f"\n[Batch {batch_num}/{num_batches}]")
            print("-" * 40)
            
            for desc, src, tgt in batch:
                short_desc = desc[:60] + "..." if len(desc) > 60 else desc
                print(f"  {src} → {tgt}")
                print(f"    \"{short_desc}\"")
            
            batch_results = refine_predicates_batch(batch)
            pred_mappings.update(batch_results)
            
            print("\n  Results:")
            for desc, src, tgt in batch:
                refined = batch_results.get(desc, "?")
                print(f"    {src} → {tgt} : {refined}")
    else:
        for desc, src, tgt in pred_items:
            refined = heuristic_predicate(desc)
            pred_mappings[desc] = refined
            short_desc = desc[:50] + "..." if len(desc) > 50 else desc
            print(f"  {src} → {tgt}")
            print(f"    \"{short_desc}\" → {refined}")
    
    refined_predicates = {}
    for desc, info in data["predicates"].items():
        refined = pred_mappings.get(desc, heuristic_predicate(desc))
        refined_predicates[desc] = {**info, "refined": refined}

    # === SAVE ===
    refined = {
        "types": refined_types,
        "predicates": refined_predicates,
        "entities": data["entities"],
        "relationships": data["relationships"]
    }

    print("\n" + "-" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"  Types refined:      {len(refined_types)}")
    print(f"  Predicates refined: {len(refined_predicates)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REFINED_DATA, 'w') as f:
        json.dump(refined, f, indent=2)

    print(f"\n✓ Saved: {REFINED_DATA}")
    return refined


if __name__ == "__main__":
    run()
