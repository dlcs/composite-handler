import os
import logging

from django.conf import settings
from pdf2image import convert_from_path
from PIL import Image

logger = logging.Logger(__name__)

Image.MAX_IMAGE_PIXELS = 1000000000


class PdfRasterizer:
    def __init__(self):
        self._dpi = settings.PDF_RASTERIZER["dpi"]
        self._fmt = settings.PDF_RASTERIZER["format"]
        self._thread_count = settings.PDF_RASTERIZER["thread_count"]
        self._max_length = settings.PDF_RASTERIZER["max_length"]

    def rasterize_pdf(self, subfolder_path):
        # Typically, pdf2image will write generated images to a temporary path, after
        # which you can manipulate them. By providing 'output_file' and 'output_folder',
        # we can skip that second step and make pdf2image write directly to our desired
        # output folder, using our desired file name pattern.
        images = convert_from_path(
            os.path.join(subfolder_path, "source.pdf"),
            dpi=self._dpi,
            fmt=self._fmt,
            thread_count=self._thread_count,
            output_file="image-",
            output_folder=subfolder_path,
        )

        return self.__rescale(images)

    def __rescale(self, images):
        if not self._max_length:
            return images

        idx = 0
        for im in images:
            w = im.width
            h = im.height
            filename = im.filename
            if max(w, h) == 1:
                logger.warning(f"image index {idx} is 1x1 pixel output")
            if max(w, h) > self._max_length:
                # exceeds max_length so reduce
                scale = min(self._max_length / w, self._max_length / h)
                scale_w = int(w * scale)
                scale_h = int(h * scale)

                logger.info(
                    f"resizing image index {idx} from {w},{h} to {scale_w},{scale_h}"
                )
                resized = im.resize((scale_w, scale_h), resample=Image.LANCZOS)
                resized.save(filename)

            idx += 1
        return images
