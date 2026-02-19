import os
import boto3

def s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT")  # e.g. http://minio:9000
    access = os.getenv("MINIO_ACCESS_KEY")
    secret = os.getenv("MINIO_SECRET_KEY")

    # MinIO is S3-compatible
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name="us-east-1",
    )

def ensure_bucket(bucket: str):
    client = s3_client()
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)

def upload_bytes(bucket: str, key: str, data: bytes, content_type: str | None = None):
    client = s3_client()
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    client.put_object(Bucket=bucket, Key=key, Body=data, **extra)

def download_bytes(bucket: str, key: str) -> bytes:
    client = s3_client()
    obj = client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()
