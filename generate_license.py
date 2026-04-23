import argparse
from license_manager import generate_expected_key

def main():
    parser = argparse.ArgumentParser(description="Generate a license key for a specific Machine ID.")
    parser.add_argument("machine_id", help="The hardware-bound Machine ID provided by the client.")
    parser.add_argument("--output", "-o", default="license.key", help="Output file path (default: license.key)")

    args = parser.parse_args()

    license_key = generate_expected_key(args.machine_id)

    try:
        with open(args.output, "w") as f:
            f.write(license_key)
        print(f"Successfully generated license key for Machine ID: {args.machine_id}")
        print(f"Saved to: {args.output}")
    except Exception as e:
        print(f"Error saving license file: {e}")

if __name__ == "__main__":
    main()
