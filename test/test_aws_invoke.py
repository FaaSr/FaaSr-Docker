import argparse
import json
import os
import sys

def main():
    """
    Get url, overwritten fields, and secrets from command line.
    Then, directly invoke entry script
    """
    parser = argparse.ArgumentParser(
        description="Set environment variables from url and payload/secrets files"
    )
    parser.add_argument("url")
    parser.add_argument("overwritten")
    parser.add_argument("secrets_file")

    args = parser.parse_args()

    with open(args.url, "r") as file:
        url = file.read().strip()

    with open(args.overwritten, "r") as file:
        overwritten = file.read().strip()

    with open(args.secrets_file, "r") as file:
        secrets = file.read().strip()

    event = {
        "OVERWRITTEN": json.loads(overwritten),
        "PAYLOAD_URL": url,
    }

    os.environ["SECRET_PAYLOAD"] = secrets
    if "My_GitHub_Account_TOKEN" in json.loads(secrets):
        os.environ["TOKEN"] = json.loads(secrets)["My_GitHub_Account_TOKEN"]
    
    sys.path.insert(1, '../faas_specific')
    import faasr_start_invoke_aws

    faasr_start_invoke_aws.handler(event, None)


if __name__ == "__main__":
    main()
