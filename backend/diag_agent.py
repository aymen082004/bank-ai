import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(r"c:\Users\user\Desktop\bank-ai-main\bank-ai-main\backend")
sys.path.append(str(project_root))

import importlib.util

def load_agent(agent_dir, module_name="agents.react_agent"):
    path = os.path.join(project_root, agent_dir, "agents", "react_agent.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

print("--- DIAGNOSTIC AGENT EXPERT ---")
try:
    print(f"Chargement de l'agent depuis 'reception-agent'...")
    agent_module = load_agent("reception-agent", "diag_bank_agent")
    run_bank_agent = agent_module.run_react_agent
    print("Agent chargé avec succès !")
    
    print("\nTest d'une requête simple...")
    # On simule un message utilisateur
    result = run_bank_agent(user_input="Bonjour, qui es-tu ?", user_id="test_user")
    print(f"Résultat de l'agent : {result}")
    
except Exception as e:
    print("\n[ERREUR DÉTECTÉE]")
    import traceback
    traceback.print_exc()

print("\n--- FIN DU DIAGNOSTIC ---")
