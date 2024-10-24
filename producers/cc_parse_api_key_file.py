import os
import re
import sys
from pathlib import Path

def get_latest_api_key_file(download_dir):
    api_key_files = list(Path(download_dir).glob('api-key-*'))
    if not api_key_files:
        raise FileNotFoundError("No API key file found in the downloads directory.")
    return max(api_key_files, key=os.path.getmtime)

def parse_api_key_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    api_key = re.search(r'API key:\s*(.+)', content)
    api_secret = re.search(r'API secret:\s*(.+)', content)
    bootstrap_server = re.search(r'Bootstrap server:\s*(.+)', content)
    
    if not all([api_key, api_secret, bootstrap_server]):
        raise ValueError("Could not extract all required information from the API key file.")
    
    return {
        'CC_API_KEY': api_key.group(1).strip(),
        'CC_API_KEY_SECRET': api_secret.group(1).strip(),
        'BOOTSTRAP_SERVERS': bootstrap_server.group(1).strip()
    }

def write_env_file(data, env_file_path):
    env_content = f"""BOOTSTRAP_SERVERS={data['BOOTSTRAP_SERVERS']}
SECURITY_PROTOCOL=SASL_SSL
SASL_MECHANISM=PLAIN
CC_API_KEY={data['CC_API_KEY']}
CC_API_KEY_SECRET={data['CC_API_KEY_SECRET']}
CLIENT_ID=python-producer
ACKS=1
SCHEMA_REGISTRY_URL=
SCHEMA_REGISTRY_API_KEY=
SCHEMA_REGISTRY_API_SECRET=
"""
    with open(env_file_path, 'w') as env_file:
        env_file.write(env_content)

def main(download_dir, env_file_path):
    try:
        latest_api_key_file = get_latest_api_key_file(download_dir)
        print(f"Found API key file: {latest_api_key_file}")

        parsed_data = parse_api_key_file(latest_api_key_file)
        print("Successfully parsed API key file")

        write_env_file(parsed_data, env_file_path)
        print(f"Written data to {env_file_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <download_directory> <env_file_path>")
        sys.exit(1)

    download_dir = sys.argv[1]
    env_file_path = sys.argv[2]

    main(download_dir, env_file_path)