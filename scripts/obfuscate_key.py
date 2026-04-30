import os
import base64

def obfuscate():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found in environment. Generating empty secret.")
        encoded_str = ""
    else:
        # Simple obfuscation: reverse string and base64 encode
        reversed_key = api_key[::-1]
        encoded_bytes = base64.b64encode(reversed_key.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')

    code = f'# Auto-generated file by build script. DO NOT COMMIT.\nOBFUSCATED_KEY = "{encoded_str}"\n'

    # Create directory if it doesn't exist
    out_dir = os.path.join("src", "core")
    os.makedirs(out_dir, exist_ok=True)
    
    out_path = os.path.join(out_dir, "_secret.py")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"Obfuscated key written to {out_path}")

if __name__ == "__main__":
    obfuscate()
