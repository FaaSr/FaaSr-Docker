import argparse
import json
import os

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
        "SECRET_PAYLOAD": secrets,
        "OVERWRITTEN": json.loads(overwritten),
        "PAYLOAD_URL": url,
    }
    if "My_GitHub_Account_TOKEN" in json.loads(secrets):
        os.environ["TOKEN"] = json.loads(secrets)["My_GitHub_Account_TOKEN"]
    if "My_S3_Bucket_ACCESS_KEY" in json.loads(secrets):
        os.environ["ACCESS_KEY"] = json.loads(secrets)["My_S3_Bucket_ACCESS_KEY"]
    if "My_S3_Bucket_SECRET_KEY" in json.loads(secrets):
        os.environ["SECRET_KEY"] = json.loads(secrets)["My_S3_Bucket_SECRET_KEY"]
    if "My_Lambda_Account_ACCESS_KEY" in json.loads(secrets):
        os.environ["ACCESS_KEY"] = json.loads(secrets)["My_Lambda_Account_ACCESS_KEY"]
    if "My_Lambda_Account_SECRET_KEY" in json.loads(secrets):
        os.environ["SECRET_KEY"] = json.loads(secrets)["My_Lambda_Account_SECRET_KEY"]

    import faasr_start_invoke_aws

    faasr_start_invoke_aws.handler(event, None)


if __name__ == "__main__":
    main()
