import os
import sys
from finkernel.psl.compiler.compiler import PSLCompiler

def main():
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "examples", "phoenix_autocall_worst_of", "phoenix_autocall.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("=== FINKERNEL Platform v1.0: PSL Compiler & FIR Generation ===")
    success, fir, errors = PSLCompiler.compile_yaml(content)
    
    if not success:
        print("Compilation FAILED:", errors)
        sys.exit(1)
        
    print("Compilation SUCCESSFUL!")
    print(f"Product ID: {fir.product_id}")
    print(f"Canonical Hash (SHA-256): {fir.canonical_hash}")
    print(f"Compiled At: {fir.compiled_at}")
    print(f"Underlyings Count: {len(fir.underlyings)}")
    print(f"Payoff Components: {len(fir.components)}")

if __name__ == "__main__":
    main()
