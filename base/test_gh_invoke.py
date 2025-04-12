import os
import json
import argparse

parser = argparse.ArgumentParser(description="Set environment variables from token and payload/secrets files")
parser.add_argument('token_file')
parser.add_argument('payload_file')
parser.add_argument('secrets_file')

args = parser.parse_args()

with open(args.token_file, 'r', encoding='utf-8') as file:
    token = file.read().strip() 

with open(args.payload_file, 'r', encoding='utf-8') as file:
    payload = file.read().strip()
json.loads(payload)

with open(args.secrets_file, 'r', encoding='utf-8') as file:
    secrets = file.read().strip()
json.loads(secrets)

os.environ["SECRET_PAYLOAD"] = secrets
os.environ["GITHUB_PAT"] = token
os.environ['PAYLOAD'] = payload


import faasr_start_invoke_github_actions
