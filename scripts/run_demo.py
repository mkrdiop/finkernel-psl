import os
import sys

from finkernel.psl.compiler.compiler import PSLCompiler


def main() -> None:
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "examples", "phoenix_autocall_worst_of",
                             "phoenix_autocall.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("=== FINKERNEL Platform v1.0: PSL Compiler & FIR Generation ===")
    result = PSLCompiler().compile(content)

    for d in result.diagnostics:
        print(f"  {d.severity.value.upper():7} {d.format()}")

    if not result.success:
        print("Compilation FAILED")
        sys.exit(1)

    fir = result.fir
    print("Compilation SUCCESSFUL!")
    print(f"Product ID:        {fir.product_id}")
    print(f"Contract hash:     {fir.contract_hash}")
    print(f"Valuation hash:    {fir.valuation_hash}")
    print(f"Risk hash:         {fir.risk_hash}")
    print(f"Source hash:       {fir.provenance.source_hash}")
    print(f"Compilation ID:    {fir.provenance.compilation_id}")
    print(f"Compiled at:       {fir.provenance.compiled_at}  (not part of any hash)")
    print(f"Underlyings:       {len(fir.underlyings)}")
    print(f"Payoff components: {len(fir.components)}")


if __name__ == "__main__":
    main()
