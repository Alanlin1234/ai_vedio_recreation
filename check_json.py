import json

# Check FLUX_GGUF_WORKFLOW .json
print("Checking FLUX_GGUF_WORKFLOW .json...")
try:
    with open('FLUX_GGUF_WORKFLOW .json', 'r', encoding='utf-8') as f:
        flux_data = json.load(f)
    print("✓ FLUX_GGUF_WORKFLOW .json is valid JSON")
    print(f"  Nodes: {len(flux_data.get('nodes', []))}")
    print(f"  Node IDs: {[node['id'] for node in flux_data.get('nodes', []) if 'id' in node]}")
except Exception as e:
    print(f"✗ FLUX_GGUF_WORKFLOW .json error: {e}")

# Check wan2.1_t2v.json
print("\nChecking wan2.1_t2v.json...")
try:
    with open('wan2.1_t2v.json', 'r', encoding='utf-8') as f:
        wan_data = json.load(f)
    print("✓ wan2.1_t2v.json is valid JSON")
    print(f"  Nodes: {len(wan_data.get('nodes', []))}")
    print(f"  Node IDs: {[node['id'] for node in wan_data.get('nodes', []) if 'id' in node]}")
except Exception as e:
    print(f"✗ wan2.1_t2v.json error: {e}")
