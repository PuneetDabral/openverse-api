from drf_yasg import openapi

from catalog.api.docs.media_docs import (
    fields_to_md,
    refer_sample,
    MediaSearch,
    MediaStats,
    MediaDetail,
    MediaRelated,
    MediaComplain,
)
from catalog.api.examples import (
    image_search_curl,
    image_search_200_example,
    image_search_400_example,
    recommendations_images_read_curl,
    recommendations_images_read_200_example,
    recommendations_images_read_404_example,
    image_detail_curl,
    image_detail_200_example,
    image_detail_404_example,
    image_stats_curl,
    image_stats_200_example,
    report_image_curl,
    images_report_create_201_example,
    oembed_list_curl,
    oembed_list_200_example,
    oembed_list_404_example,
)
from catalog.api.serializers.error_serializers import (
    InputErrorSerializer,
    NotFoundErrorSerializer,
)
from catalog.api.serializers.image_serializers import (
    ImageSearchQueryStringSerializer,
    ImageSearchResultsSerializer,
    ImageSerializer,
    ReportImageSerializer,
    OembedRequestSerializer,
    OembedSerializer,
)
from catalog.api.serializers.provider_serializers import ProviderSerializer


class ImageSearch(MediaSearch):
    desc = f"""
image_search is an API endpoint to search images using a query string.

By using this endpoint, you can obtain search results based on specified query
and optionally filter results by
{fields_to_md(ImageSearchQueryStringSerializer.fields_names)}.

{MediaSearch.desc}"""  # noqa

    responses = {
        "200": openapi.Response(
            description="OK",
            examples=image_search_200_example,
            schema=ImageSearchResultsSerializer
        ),
        "400": openapi.Response(
            description="Bad Request",
            examples=image_search_400_example,
            schema=InputErrorSerializer
        )
    }

    code_examples = [
        {
            'lang': 'Bash',
            'source': image_search_curl,
        },
    ]

    swagger_setup = {
        'operation_id': 'image_search',
        'operation_description': desc,
        'query_serializer': ImageSearchQueryStringSerializer,
        'responses': responses,
        'code_examples': code_examples,
    }


class ImageStats(MediaStats):
    desc = f"""
image_stats is an API endpoint to get a list of all content providers and their
respective number of images in the Openverse catalog.

{MediaStats.desc}"""  # noqa

    responses = {
        "200": openapi.Response(
            description="OK",
            examples=image_stats_200_example,
            schema=ProviderSerializer(many=True)
        )
    }

    code_examples = [
        {
            'lang': 'Bash',
            'source': image_stats_curl,
        }
    ]

    swagger_setup = {
        'operation_id': 'image_stats',
        'operation_description': desc,
        'responses': responses,
        'code_examples': code_examples
    }


class ImageDetail(MediaDetail):
    desc = f"""
image_detail is an API endpoint to get the details of a specified image ID.

By using this endpoint, you can image details such as
{fields_to_md(ImageSerializer.fields_names)}.

{MediaDetail.desc}"""  # noqa

    responses = {
        "200": openapi.Response(
            description="OK",
            examples=image_detail_200_example,
            schema=ImageSerializer
        ),
        "404": openapi.Response(
            description='Not Found',
            examples=image_detail_404_example,
            schema=NotFoundErrorSerializer
        )
    }

    code_examples = [
        {
            'lang': 'Bash',
            'source': image_detail_curl
        }
    ]

    swagger_setup = {
        'operation_id': "image_detail",
        'operation_description': desc,
        'responses': responses,
        'code_examples': code_examples,
    }


class ImageRelated(MediaRelated):
    desc = f"""
recommendations_images_read is an API endpoint to get related images 
for a specified image ID.

By using this endpoint, you can get the details of related images such as 
{fields_to_md(ImageSerializer.fields_names)}.

{MediaRelated.desc}"""  # noqa

    responses = {
        "200": openapi.Response(
            description="OK",
            examples=recommendations_images_read_200_example,
            schema=ImageSerializer
        ),
        "404": openapi.Response(
            description="Not Found",
            examples=recommendations_images_read_404_example,
            schema=NotFoundErrorSerializer
        )
    }

    code_examples = [
        {
            'lang': 'Bash',
            'source': recommendations_images_read_curl
        }
    ]

    swagger_setup = {
        'operation_id': "image_related",
        'operation_description': desc,
        'responses': responses,
        'code_examples': code_examples
    }


class ImageComplain(MediaComplain):
    desc = f"""
images_report_create is an API endpoint to report an issue about a specified
image ID to Openverse.

By using this endpoint, you can report an image if it infringes copyright,
contains mature or sensitive content and others.

{MediaComplain.desc}"""  # noqa

    responses = {
        "201": openapi.Response(
            description="OK",
            examples=images_report_create_201_example,
            schema=ReportImageSerializer
        )
    }

    code_examples = [
        {
            'lang': 'Bash',
            'source': report_image_curl,
        }
    ]

    swagger_setup = {
        'operation_id': 'image_report',
        'operation_description': desc,
        'query_serializer': ReportImageSerializer,
        'responses': responses,
        'code_examples': code_examples,
    }


class ImageOembed:
    desc = f"""
oembed_list is an API endpoint to retrieve embedded content from a
specified image URL.

By using this endpoint, you can retrieve embedded content such as `version`,
`type`, `width`, `height`, `title`, `author_name`, `author_url` and
`license_url`.

{refer_sample}"""  # noqa

    responses = {
        "200": openapi.Response(
            description="OK",
            examples=oembed_list_200_example,
            schema=OembedSerializer
        ),
        "404": openapi.Response(
            description="Not Found",
            examples=oembed_list_404_example,
            schema=NotFoundErrorSerializer
        )
    }

    code_examples = [
        {
            'lang': 'Bash',
            'source': oembed_list_curl,
        },
    ]

    swagger_setup = {
        'operation_id': "oembed_list",
        'operation_description': desc,
        'query_serializer': OembedRequestSerializer,
        'responses': responses,
        'code_examples': code_examples
    }