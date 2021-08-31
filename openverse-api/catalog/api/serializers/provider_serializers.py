from rest_framework import serializers

from catalog.api.models import ContentProvider, SourceLogo


class ProviderSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(
        source='provider_identifier',
        help_text='The source of the media.',
    )
    display_name = serializers.CharField(
        source='provider_name',
        help_text='The name of content provider.',
    )
    source_url = serializers.URLField(
        source='domain_name',
        help_text='The URL of the source.',
    )
    logo_url = serializers.SerializerMethodField(
        help_text='The URL to a logo of the source.',
    )
    media_count = serializers.SerializerMethodField(
        help_text='The number of media items indexed from the source.',
    )

    class Meta:
        model = ContentProvider
        fields = [
            'source_name',
            'display_name',
            'source_url',
            'logo_url',
            'media_count',
        ]

    def get_logo_url(self, obj):
        try:
            source_logo = obj.sourcelogo
        except SourceLogo.DoesNotExist:
            return None
        logo_path = source_logo.image.url
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(logo_path)

    def get_media_count(self, obj):
        source_counts = self.context.get('source_counts')
        return source_counts.get(obj.provider_identifier)