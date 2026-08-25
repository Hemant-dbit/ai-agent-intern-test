#!/usr/bin/env python3
"""Interactive CLI for the Aster & Row Agent."""

import uuid
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.orchestrator import handle_message
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    print("Welcome to Aster & Row Support!")
    print("Type 'exit' or 'quit' to end the session.")
    print("-" * 50)
    
    session_id = str(uuid.uuid4())
    
    while True:
        try:
            user_input = input("\nYou: ")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
            
        if user_input.strip().lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
            
        if not user_input.strip():
            continue
            
        response = handle_message(session_id, user_input)
        
        print("\nAgent:", response.answer)
        
        if response.handoff:
            print(f"** [System] Human handoff triggered. Reason: {response.handoff_reason} **")

if __name__ == "__main__":
    main()
