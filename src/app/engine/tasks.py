import logging
import shutil

from app.common.dlcs import DLCS
from app.common.models import Member
from app.engine.builder import MemberBuilder
from app.engine.origins import HttpOrigin
from app.engine.rasterizers import PdfRasterizer
from app.engine.s3 import S3Client
from app.engine.serializers import DLCSBatchSerializer

logger = logging.Logger(__name__)
http_origin = HttpOrigin()
pdf_rasterizer = PdfRasterizer()
s3_client = S3Client()
dlcs = DLCS()


def cleanup_scratch(folder_path):
    try:
        shutil.rmtree(folder_path)
    except FileNotFoundError:
        logger.info(f"cleanup failed for {folder_path}, not found")


def process_member(args):
    member = Member.objects.get(id=args["id"])
    folder_path = None
    try:
        folder_path = __fetch_origin(member, member.json_data["origin"])
        image_paths = __rasterize_composite(member, folder_path)
        s3_urls = __push_images_to_dlcs(member, image_paths)
        dlcs_requests = __build_dlcs_requests(member, s3_urls)
        dlcs_responses = __initiate_dlcs_ingest(member, dlcs_requests, args["auth"])
        return __build_result(member, dlcs_responses)
    except Exception as error:
        __process_error(member, error)
    finally:
        cleanup_scratch(folder_path)


def __fetch_origin(member, origin_uri):
    __update_status(member, "FETCHING_ORIGIN")
    return http_origin.fetch(member.id, origin_uri)


def __rasterize_composite(member, pdf_path):
    __update_status(member, "RASTERIZING")
    return pdf_rasterizer.rasterize_pdf(pdf_path)


def __push_images_to_dlcs(member, image_paths):
    __update_status(member, "PUSHING_TO_DLCS", image_count=len(image_paths))
    composite_id = member.json_data.get("compositeId")
    customer = member.collection.customer
    space = member.json_data["space"]
    return s3_client.put_images(image_paths, member.id, composite_id, customer, space)


def __build_dlcs_requests(member, dlcs_uris):
    __update_status(member, "BUILDING_DLCS_REQUEST")
    member_builder = MemberBuilder(member.json_data)
    for dlcs_uri in dlcs_uris:
        member_builder.build_member(dlcs_uri)
    return member_builder.build_collections()


def __initiate_dlcs_ingest(member, dlcs_requests, auth):
    dlcs_responses = []
    for dlcs_request in dlcs_requests:
        dlcs_responses.append(
            dlcs.ingest(member.collection.customer, dlcs_request, auth)
        )
    return dlcs_responses


def __build_result(member, dlcs_responses):
    __update_status(member, "COMPLETED", dlcs_responses=dlcs_responses)
    return dlcs_responses


def __process_error(member, error):
    __update_status(member, "ERROR", error=str(error))
    raise error


def __update_status(member, status, image_count=None, dlcs_responses=None, error=None):
    member.status = status
    if image_count:
        member.image_count = image_count
    if error:
        member.error = error

    if dlcs_responses:
        serializers = [
            DLCSBatchSerializer(
                data={
                    "member": member.id,
                    "json_data": dlcs_response,
                    "uri": dlcs_response["@id"],
                }
            )
            for dlcs_response in dlcs_responses
        ]
        if not all(serializer.is_valid() for serializer in serializers):
            raise
        for serializer in serializers:
            serializer.save()

    member.save()
