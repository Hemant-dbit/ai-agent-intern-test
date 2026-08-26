#!/usr/bin/env python3
"""Run evaluation framework."""

import json
import uuid
from datetime import datetime
from pathlib import Path
import os
import sys

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.orchestrator import handle_message, session_store
from app.evaluation import evaluate_assertions

def main():
    base_dir = Path(__file__).resolve().parents[1]
    eval_dir = base_dir / "evaluation"
    
    cases_files = [
        eval_dir / "visible-cases.json",
        eval_dir / "custom-cases.json"
    ]
    
    all_results = []
    category_stats = {}
    
    print(f"{'ID':<15} | {'Category':<15} | {'Passed':<8} | {'Errors'}")
    print("-" * 60)
    
    for case_file in cases_files:
        if not case_file.exists():
            continue
            
        with open(case_file, "r") as f:
            data = json.load(f)
            cases = data.get("cases", []) if isinstance(data, dict) else data
            
        for case in cases:
            # We use a fresh session ID for each case
            session_id = str(uuid.uuid4())
            case_id = case.get("id", "unknown")
            category = case.get("category", "unknown")
            messages = case.get("messages", [])
            
            # Reset session store for this ID
            session_store._sessions.pop(session_id, None)
            
            # Send messages (could be multi-turn)
            final_resp = None
            for msg_dict in messages:
                # msg_dict is {"role": "user", "content": "..."} in the original schema
                content = msg_dict.get("content", "")
                final_resp = handle_message(session_id, content)
                
            if not final_resp:
                continue
                
            expect = case.get("expect", {})
            passed, fails = evaluate_assertions(final_resp, expect, final_resp.tools_called)
            
            if category not in category_stats:
                category_stats[category] = {"total": 0, "passed": 0}
            category_stats[category]["total"] += 1
            if passed:
                category_stats[category]["passed"] += 1
                
            res_str = "PASS" if passed else "FAIL"
            err_str = "; ".join(fails) if fails else "-"
            print(f"{case_id:<15} | {category:<15} | {res_str:<8} | {err_str}")
            
            all_results.append({
                "id": case_id,
                "category": category,
                "passed": passed,
                "failures": fails,
                "final_answer": final_resp.answer
            })
            
    print("\n--- Category Rollup ---")
    total_passed = 0
    total_cases = 0
    for cat, stats in category_stats.items():
        print(f"{cat}: {stats['passed']} / {stats['total']} passed")
        total_passed += stats['passed']
        total_cases += stats['total']
    
    print(f"\nOverall: {total_passed} / {total_cases} passed")
    
    # Save results
    out_dir = eval_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"{ts}.json"
    
    with open(out_file, "w") as f:
        json.dump({"summary": category_stats, "details": all_results}, f, indent=2)
    print(f"Results saved to {out_file}")

if __name__ == "__main__":
    main()
