import os
import logging
from enum import Enum

from django.conf import settings
from pdf2image import convert_from_path
from PIL import Image

logger = logging.Logger(__name__)

Image.MAX_IMAGE_PIXELS = 1000000000


class ResizeResult(Enum):
    NOOP = 1
    RESIZED = 2
    SINGLE_PIXEL = 3


class PdfRasterizer:
    def __init__(self):
        self._dpi = settings.PDF_RASTERIZER["dpi"]
        self._fallback_dpi = settings.PDF_RASTERIZER["fallback_dpi"]
        self._fmt = settings.PDF_RASTERIZER["format"]
        self._thread_count = settings.PDF_RASTERIZER["thread_count"]
        self._max_length = settings.PDF_RASTERIZER["max_length"]
        self._use_cropbox = settings.PDF_RASTERIZER["use_cropbox"]

    def rasterize_pdf(self, subfolder_path):
        # Typically, pdf2image will write generated images to a temporary path, after
        # which you can manipulate them. By providing 'output_file' and 'output_folder',
        # we can skip that second step and make pdf2image write directly to our desired
        # output folder, using our desired file name pattern.
        pdf_source = os.path.join(subfolder_path, "source.pdf")
        images = self.__rasterize(pdf_source, subfolder_path, dpi=self._dpi)
        images = self.__validate_rasterized_images(images, pdf_source, subfolder_path)
        return [i.filename for i in images]

    def __rasterize(
        self, pdf_source, subfolder_path, start_page=None, last_page=None, dpi=None
    ):
        # return value from convert_from_path is a list of all images in output directory that have appropriate
        # extension and start with output_file. Due to this use a different output_file name for initial rasterizing and
        # further page-by-page rasterizing
        output_file = "imager-" if start_page else "image-"
        return convert_from_path(
            pdf_source,
            first_page=start_page,
            last_page=last_page,
            dpi=dpi or self._fallback_dpi,
            fmt=self._fmt,
            thread_count=self._thread_count,
            output_file=output_file,
            output_folder=subfolder_path,
            use_cropbox=self._use_cropbox,
        )

    def __validate_rasterized_images(self, images, pdf_source, subfolder_path):
        """
        Validate that rasterized images don't exceed max_size (if set) and that a single 1x1 pixel output has not been
        generated. see https://github.com/Belval/pdf2image/issues/34
        """
        single_pixel_pages = []
        idx = 0
        for im in images:
            res = self.__ensure_image_size(idx, im)
            if res == ResizeResult.SINGLE_PIXEL:
                single_pixel_pages.append(idx + 1)
            idx += 1
            im.close()

        if single_pixel_pages:
            return self.__rescale_single_page_default_dpi(
                pdf_source, subfolder_path, single_pixel_pages, images
            )

        return images

    def __ensure_image_size(self, idx, im: Image):
        w = im.width
        h = im.height
        filename = im.filename
        if max(w, h) == 1:
            logger.warning(f"image index {idx} is 1x1 pixel output")
            return ResizeResult.SINGLE_PIXEL
        if self._max_length and max(w, h) > self._max_length:
            # exceeds max_length so reduce
            scale = min(self._max_length / w, self._max_length / h)
            scale_w = int(w * scale)
            scale_h = int(h * scale)

            logger.info(
                f"resizing image index {idx} from {w},{h} to {scale_w},{scale_h}"
            )

            with im.resize((scale_w, scale_h), resample=Image.LANCZOS) as resized:
                resized.save(filename)
            return ResizeResult.RESIZED

        return ResizeResult.NOOP

    def __rescale_single_page_default_dpi(
        self, pdf_source, subfolder_path, pages, images
    ):
        count = 0
        for p in pages:
            idx = p - 1
            res = self.__rasterize(
                pdf_source, subfolder_path, start_page=p, last_page=p
            )
            updated_image = res[count]
            self.__ensure_image_size(idx, updated_image)

            logger.debug(f"re-rasterizing page {p} - {updated_image.filename}")

            images[idx] = updated_image
            count += 1

        return images
