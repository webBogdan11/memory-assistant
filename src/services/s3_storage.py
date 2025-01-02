import uuid
from config import settings

import boto3


class S3StorageService:
    """
    Handles uploads to S3 (or minio, or any S3-compatible storage).
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        region: str | None = None,
    ):
        self.bucket_name = bucket_name or settings.AWS_BUCKET_NAME
        self.region = region or settings.AWS_REGION
        self.s3_client = boto3.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def upload_file(self, file_data: bytes, unique_key: str) -> str:
        """
        Uploads file_data to S3 under a unique key,
        returns the S3 key or URL to store in DB.
        """
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=unique_key,
            Body=file_data,
        )
        return f"s3://{self.bucket_name}/{unique_key}"

    def delete_file(self, file_name: str) -> None:
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_name)

    def get_file(self, file_name: str) -> bytes:
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_name)
        return response["Body"].read()
