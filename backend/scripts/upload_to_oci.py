import os
import sys
import logging
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass # Assume environment variables are loaded some other way if dotenv is not present

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def upload_file_to_oci(file_path: str, object_name: str = None):
    """
    Upload a file to Oracle Cloud Infrastructure (OCI) Object Storage using S3 Compatible API.
    """
    access_key = os.environ.get("OCI_ACCESS_KEY_ID")
    secret_key = os.environ.get("OCI_SECRET_ACCESS_KEY")
    endpoint_url = os.environ.get("OCI_ENDPOINT_URL")
    bucket_name = os.environ.get("OCI_BUCKET_NAME")

    if not all([access_key, secret_key, endpoint_url, bucket_name]):
        logger.error("Missing OCI credentials. Please check your .env file and set OCI_ACCESS_KEY_ID, OCI_SECRET_ACCESS_KEY, OCI_ENDPOINT_URL, and OCI_BUCKET_NAME.")
        sys.exit(1)

    if object_name is None:
        object_name = Path(file_path).name

    logger.info(f"Preparing to upload '{file_path}' to bucket '{bucket_name}' as '{object_name}'...")
    logger.info(f"Using endpoint: {endpoint_url}")

    try:
        # Initialize boto3 client for OCI (S3 Compatible API)
        # OCI uses AWS S3 Signature Version 4
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            # We don't need region_name if the endpoint is fully qualified for OCI
            config=Config(signature_version="s3v4")
        )

        # Let boto3 handle the multipart upload if the file is large
        # buffalo_l.zip is ~288MB, so it will use multipart upload automatically
        s3_client.upload_file(file_path, bucket_name, object_name)
        logger.info(f"✅ Successfully uploaded {file_path} to OCI Object Storage.")
        
    except FileNotFoundError:
        logger.error(f"The file {file_path} was not found.")
    except ClientError as e:
        logger.error(f"ClientError: {e}")
        logger.error("Please verify your credentials and bucket permissions in Oracle Cloud.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Please provide the path to the zip file you want to upload.")
        logger.error("Usage: python scripts/upload_to_oci.py <path_to_file>")
        sys.exit(1)
        
    target_file = sys.argv[1]

    # Assume the script is run from the backend directory
    # If the user provides a relative or absolute path in args, use it
    file_path = os.path.abspath(target_file)
    
    if not os.path.exists(file_path):
         logger.error(f"Could not find {file_path}.")
         sys.exit(1)
         
    upload_file_to_oci(file_path)
