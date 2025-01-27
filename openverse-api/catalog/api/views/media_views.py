import logging

from django.conf import settings
from django.http.response import HttpResponse
from rest_framework.authentication import BasicAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from urllib.error import HTTPError
from urllib.request import urlopen

from catalog.api.controllers import search_controller
from catalog.api.controllers.search_controller import get_sources
from catalog.api.models import ContentProvider, SourceLogo
from catalog.api.utils.exceptions import input_error_response
from catalog.api.utils.throttle import OneThousandPerMinute
from catalog.custom_auto_schema import CustomAutoSchema

log = logging.getLogger(__name__)

FOREIGN_LANDING_URL = 'foreign_landing_url'
CREATOR_URL = 'creator_url'
RESULTS = 'results'
PAGE = 'page'
PAGESIZE = 'page_size'
FILTER_DEAD = 'filter_dead'
QA = 'qa'
SUGGESTIONS = 'suggestions'
RESULT_COUNT = 'result_count'
PAGE_COUNT = 'page_count'
PAGE_SIZE = 'page_size'

refer_sample = """
You can refer to the cURL request samples for examples on how to consume this
endpoint.
"""


def fields_to_md(field_names):
    """
    Create a Markdown representation of the given list of names to use in
    Swagger documentation.

    :param field_names: the list of field names to convert to Markdown
    :return: the names as a Markdown string
    """

    *all_but_last, last = field_names
    all_but_last = ', '.join([f'`{name}`' for name in all_but_last])
    return f'{all_but_last} and `{last}`'


def _get_user_ip(request):
    """
    Read request headers to find the correct IP address.
    It is assumed that X-Forwarded-For has been sanitized by the load balancer
    and thus cannot be rewritten by malicious users.
    :param request: A Django request object.
    :return: An IP address.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class SearchMedia(APIView):
    swagger_schema = CustomAutoSchema
    search_description = (
        """
Although there may be millions of relevant records, only the most
relevant several thousand records can be viewed. This is by design:
the search endpoint should be used to find the top 10,000 most relevant
results, not for exhaustive search or bulk download of every barely
relevant result. As such, the caller should not try to access pages
beyond `page_count`, or else the server will reject the query.

For more precise results, you can go to the
[Openverse Syntax Guide](https://search.creativecommons.org/search-help)
for information about creating queries and
[Apache Lucene Syntax Guide](https://lucene.apache.org/core/2_9_4/queryparsersyntax.html)
for information on structuring advanced searches.
"""  # noqa
        f'{refer_sample}'
    )

    def _get(self,
             request,
             default_index, qa_index,
             query_serializer, media_serializer, result_serializer):
        params = query_serializer(data=request.query_params)
        if not params.is_valid():
            return input_error_response(params.errors)

        hashed_ip = hash(_get_user_ip(request))
        page_param = params.data[PAGE]
        page_size = params.data[PAGESIZE]
        qa = params.data[QA]
        filter_dead = params.data[FILTER_DEAD]

        search_index = qa_index if qa else default_index
        try:
            results, num_pages, num_results = search_controller.search(
                params,
                search_index,
                page_size,
                hashed_ip,
                request,
                filter_dead,
                page=page_param
            )
        except ValueError as value_error:
            return input_error_response(value_error)

        context = {'request': request}
        serialized_results = media_serializer(
            results,
            many=True,
            context=context
        ).data

        if len(results) < page_size and num_pages == 0:
            num_results = len(results)
        response_data = {
            RESULT_COUNT: num_results,
            PAGE_COUNT: num_pages,
            PAGE_SIZE: len(results),
            RESULTS: serialized_results
        }
        serialized_response = result_serializer(data=response_data)
        return Response(status=200, data=serialized_response.initial_data)


class RelatedMedia(APIView):
    swagger_schema = CustomAutoSchema
    recommendations_read_description = refer_sample


class MediaDetail(GenericAPIView, RetrieveModelMixin):
    swagger_schema = CustomAutoSchema
    lookup_field = 'identifier'
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    detail_description = refer_sample


class MediaStats(APIView):
    swagger_schema = CustomAutoSchema
    media_stats_description = (
        """
You can use this endpoint to get details about content providers such as 
`source_name`, `display_name`, and `source_url` along with a count of the number
of individual items indexed from them.
"""  # noqa
        f'{refer_sample}'
    )

    def _get(self, request, index_name):
        CODENAME = 'provider_identifier'
        NAME = 'provider_name'
        FILTER = 'filter_content'
        URL = 'domain_name'
        ID = 'id'

        source_data = ContentProvider \
            .objects \
            .filter(media_type=index_name) \
            .values(ID, CODENAME, NAME, FILTER, URL)
        source_counts = get_sources(index_name)

        response = []
        for source in source_data:
            source_codename = source[CODENAME]
            _id = source[ID]
            display_name = source[NAME]
            filtered = source[FILTER]
            source_url = source[URL]
            count = source_counts.get(source_codename, None)
            try:
                source_logo = SourceLogo.objects.get(source_id=_id)
                logo_path = source_logo.image.url
                full_logo_url = request.build_absolute_uri(logo_path)
            except SourceLogo.DoesNotExist:
                full_logo_url = None
            if not filtered and source_codename in source_counts:
                response.append(
                    {
                        'source_name': source_codename,
                        f'{index_name}_count': count,
                        'display_name': display_name,
                        'source_url': source_url,
                        'logo_url': full_logo_url
                    }
                )
        return Response(status=200, data=response)


class ImageProxy(APIView):
    swagger_schema = None

    lookup_field = 'identifier'
    throttle_classes = [OneThousandPerMinute]

    def _get(self, media_url, width=settings.THUMBNAIL_WIDTH_PX):
        if width is None:  # full size
            proxy_upstream = f'{settings.THUMBNAIL_PROXY_URL}/{media_url}'
        else:
            proxy_upstream = f'{settings.THUMBNAIL_PROXY_URL}/' \
                             f'{settings.THUMBNAIL_WIDTH_PX},fit/' \
                             f'{media_url}'
        try:
            upstream_response = urlopen(proxy_upstream)
            status = upstream_response.status
            content_type = upstream_response.headers.get('Content-Type')
        except HTTPError:
            log.info('Failed to render thumbnail: ', exc_info=True)
            return HttpResponse(status=500)

        response = HttpResponse(
            upstream_response.read(),
            status=status,
            content_type=content_type
        )

        return response
