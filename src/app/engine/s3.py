import os
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat

import boto3
import tqdm
from django.conf import settings


class S3Client:
    def __init__(self):
        self._client = boto3.session.Session().client("s3")
        self._bucket_name = settings.DLCS["s3_bucket_name"]
        self._bucket_base_url = self.__build_bucket_base_url()
        self._object_key_prefix = settings.DLCS["s3_object_key_prefix"].strip("/")
        self._upload_threads = settings.DLCS["s3_upload_threads"]

    def __build_bucket_base_url(self):
        # Bucket located in 'us-east-1' don't have a location constraint in the hostname
        location = self._client.get_bucket_location(Bucket=self._bucket_name)[
            "LocationConstraint"
        ]

        if location:
            return f"https://s3-{location}.amazonaws.com/{self._bucket_name}"
        else:
            return f"https://s3.amazonaws.com/{self._bucket_name}"

    def put_images(
        self, image_paths, submission_id, composite_id, customer_id, space_id
    ):
        s3_uris = []

        key_prefix = self.__get_key_prefix(
            submission_id, composite_id, customer_id, space_id
        )

        with tqdm.tqdm(
            desc=f"[{submission_id}] Upload images to S3",
            unit=" image",
            total=len(image_paths),
        ) as progress_bar:
            with ThreadPoolExecutor(max_workers=self._upload_threads) as executor:
                # It's critical that the list of S3 URI's returned by this method is in the
                # same order as the list of images provided to it. '.map(...)' gives us that,
                # whilst '.submit(...)' does not.
                for s3_uri in executor.map(
                    self.__put_image, repeat(key_prefix), image_paths
                ):
                    s3_uris.append(s3_uri)
                    progress_bar.update(1)
        return s3_uris

    def __get_key_prefix(self, submission_id, composite_id, customer, space):
        return f"{self._object_key_prefix}/{customer}/{space}/{composite_id or submission_id}"

    def __put_image(self, key_prefix, image_path):
        object_key = f"{key_prefix}/{os.path.basename(image_path)}"
        with open(image_path, "rb") as file:
            self._client.put_object(Bucket=self._bucket_name, Key=object_key, Body=file)
        return f"{self._bucket_base_url}/{object_key}"
