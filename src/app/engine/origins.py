import logging
import os
from pathlib import Path

import requests
from django.conf import settings

from app.engine.origin_rules import headers_for

logger = logging.getLogger(__name__)


class HttpOrigin:
    def __init__(self):
        self._scratch_path = settings.SCRATCH_DIRECTORY
        self._chunk_size = settings.ORIGIN_CONFIG["chunk_size"]
        self._http_rules = settings.ORIGIN_CONFIG["http_rules"]

    def fetch(self, submission_id, url, customer, file_extension="pdf"):
        subfolder_path = self.__generate_subfolder_path(submission_id)
        file_path = os.path.join(subfolder_path, "source." + file_extension)
        headers = headers_for(self._http_rules, customer, url)
        if headers:
            logger.info(
                f"Applying custom origin headers {sorted(headers)} for submission {submission_id}",
            )
        with requests.get(url, stream=True, headers=headers or None) as response:
            response.raise_for_status()
            with open(file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=self._chunk_size):
                    file.write(chunk)
        return subfolder_path

    def __generate_subfolder_path(self, submission_id):
        subfolder_path = self._scratch_path / Path(str(submission_id))
        Path(subfolder_path).mkdir(parents=True, exist_ok=True)
        return subfolder_path
