"""Quick check of processors/processor_D.json with the kit's own validate_processor_d (same rules as
tools/check_processor_d.py).  Run:  python check_d.py     (the kit's tools/check_processor_d.py stays the final authority)"""
import sys
import qff_sim as q

path = sys.argv[1] if len(sys.argv) > 1 else "processors/processor_D.json"
D = q.load_processor(path)
errs = q.validate_processor_d(D, 4)
if errs:
    print("INVALID:")
    for e in errs:
        print(" -", e)
    sys.exit(1)
print(f"OK: {D['name']} passes the rules ({D['num_qubits']} qubits, {len(D['edges'])} couplings, basis {D['basis_gates']})")
