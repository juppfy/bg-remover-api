"""
Upload processed images to an S3-compatible storage bucket (Railway, AWS S3, R2, etc.).
Returns a URL to access the file: presigned URL for Railway (private buckets), or public URL if configured.
"""
import os
import logging
from datetime import datetime
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Presigned URL expiry for Railway (private buckets). Max 90 days; 7 days is a good default.
PRESIGNED_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days


def upload_to_bucket(
    image_bytes: bytes,
    content_type: str = "image/png",
) -> str:
    """
    Upload PNG bytes to the configured bucket. Uses UUID + timestamp for filename.
    Returns a URL to access the file (presigned URL for Railway private buckets).
    """
    # Support Railway variable names (BUCKET, ACCESS_KEY_ID, SECRET_ACCESS_KEY, ENDPOINT, REGION)
    # and our legacy names (RAILWAY_BUCKET_*)
    bucket_name = os.getenv("BUCKET") or os.getenv("RAILWAY_BUCKET_NAME")
    bucket_region = os.getenv("REGION") or os.getenv("RAILWAY_BUCKET_REGION") or "auto"
    access_key = os.getenv("ACCESS_KEY_ID") or os.getenv("RAILWAY_BUCKET_ACCESS_KEY")
    secret_key = os.getenv("SECRET_ACCESS_KEY") or os.getenv("RAILWAY_BUCKET_SECRET_KEY")
    endpoint_url = os.getenv("ENDPOINT") or os.getenv("RAILWAY_BUCKET_ENDPOINT")
    # Optional: permanent public base URL (e.g. AWS S3 public bucket or CDN)
    public_base_url = os.getenv("RAILWAY_BUCKET_URL") or os.getenv("RAILWAY_BUCKET_PUBLIC_URL")

    if not all([bucket_name, access_key, secret_key]):
        raise RuntimeError(
            "Storage not configured: set BUCKET (or RAILWAY_BUCKET_NAME), ACCESS_KEY_ID, SECRET_ACCESS_KEY. "
            "On Railway, use the bucket's Credentials tab / Variable References."
        )

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = uuid4().hex[:12]
    object_key = f"bg-removed-{unique_id}-{timestamp}.png"

    client_kwargs = {
        "region_name": bucket_region if bucket_region != "auto" else "us-east-1",
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
    }
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url.rstrip("/")
        if bucket_region == "auto":
            client_kwargs["region_name"] = "us-east-1"  # boto3 needs a region even with custom endpoint

    client = boto3.client("s3", **client_kwargs)

    try:
        client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=image_bytes,
            ContentType=content_type,
        )
    except ClientError as e:
        logger.exception("Failed to upload to bucket")
        raise RuntimeError(f"Storage upload error: {e!s}") from e

    # If you set a permanent public base URL (e.g. CDN), use that
    if public_base_url:
        public_base_url = public_base_url.rstrip("/")
        return f"{public_base_url}/{object_key}"

    # Railway buckets are private: return a presigned URL (valid up to 90 days)
    if endpoint_url:
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_key},
                ExpiresIn=PRESIGNED_EXPIRY_SECONDS,
            )
            return url
        except ClientError as e:
            logger.exception("Failed to generate presigned URL")
            raise RuntimeError(f"Storage error: {e!s}") from e

    # Fallback for AWS S3 public buckets
    return f"https://{bucket_name}.s3.{client_kwargs['region_name']}.amazonaws.com/{object_key}"
