from analytics.models import (
    Image, SearchEvent, SearchRatingEvent, ResultClickedEvent, DetailPageEvents,
    AttributionReferrerEvent, DetailPageEvent,
    DailyUsageReport,SourceUsageReport, DailyAttributionRefererReport,
    DailyTopSearches, DailyTopResults
)
from sqlalchemy import func, distinct, Integer
from sqlalchemy.sql.expression import cast


def generate_usage_report(session, start_time, end_time):
    """ Get usage stats between start and end dates """
    results_clicked = session.query(ResultClickedEvent).filter(
        start_time < ResultClickedEvent.timestamp,
        ResultClickedEvent.timestamp < end_time
    ).count()
    attribution_buttonclicks = session.query(DetailPageEvent).filter(
        start_time < DetailPageEvent.timestamp,
        DetailPageEvent.timestamp < end_time,
        DetailPageEvent.event_type == DetailPageEvents.ATTRIBUTION_CLICKED
    ).count()
    survey_responses = session.query(DetailPageEvent).filter(
        DetailPageEvent.timestamp > start_time,
        DetailPageEvent.timestamp < end_time,
        DetailPageEvent.event_type == DetailPageEvents.REUSE_SURVEY
    ).count()
    source_clicked = session.query(DetailPageEvent).filter(
        DetailPageEvent.timestamp > start_time,
        DetailPageEvent.timestamp < end_time,
        DetailPageEvent.event_type == DetailPageEvents.SOURCE_CLICKED
    ).count()
    creator_clicked = session.query(DetailPageEvent).filter(
        DetailPageEvent.timestamp > start_time,
        DetailPageEvent.timestamp < end_time,
        DetailPageEvent.event_type == DetailPageEvents.CREATOR_CLICKED
    ).count()
    shared_social = session.query(DetailPageEvent).filter(
        DetailPageEvent.timestamp > start_time,
        DetailPageEvent.timestamp < end_time,
        DetailPageEvent.event_type == DetailPageEvents.SHARED_SOCIAL
    ).count()
    sessions = session.query(
        func.count(
            distinct(SearchEvent.session_uuid)
        ).filter(
            SearchEvent.timestamp > start_time,
            SearchEvent.timestamp < end_time
        )
    ).scalar()
    searches = session.query(SearchEvent).filter(
        SearchEvent.timestamp > start_time,
        SearchEvent.timestamp < end_time
    ).count()
    attribution_referer_hits = session.query(AttributionReferrerEvent).filter(
        AttributionReferrerEvent.timestamp > start_time,
        AttributionReferrerEvent.timestamp < end_time
    ).count()
    avg_rating = session.query(
        func.avg(
            cast(SearchRatingEvent.relevant, Integer())
        ).filter(
            SearchRatingEvent.timestamp > start_time,
            SearchRatingEvent.timestamp < end_time
        )
    )
    try:
        avg_searches_per_session = searches / sessions
    except ZeroDivisionError:
        avg_searches_per_session = 0
    return {
        'results_clicked': results_clicked,
        'attribution_buttonclicks': attribution_buttonclicks,
        'survey_responses': survey_responses,
        'source_clicked': source_clicked,
        'creator_clicked': creator_clicked,
        'shared_social': shared_social,
        'sessions': sessions,
        'searches': searches,
        'attribution_referer_hits': attribution_referer_hits,
        'avg_rating': avg_rating,
        'avg_searches_per_session': avg_searches_per_session,
        'timestamp': end_time
    }


def generate_source_usage_report(session, start_time, end_time):
    source_usage = session.query(
        Image.source, func.count(ResultClickedEvent.result_uuid)
    ).select_from(Image).join(
        ResultClickedEvent, ResultClickedEvent.result_uuid == Image.identifier
    ).filter(
        ResultClickedEvent.timestamp > start_time,
        ResultClickedEvent.timestamp < end_time
    ).group_by(Image.source).all()
    res_dict = {}
    for res in source_usage:
        source, count = res
        res_dict[source] = count
    return res_dict


def generate_referrer_usage_report(session, start_time, end_time):
    attribution_embeddings = session.query(
        AttributionReferrerEvent.referer_domain,
        func.count(AttributionReferrerEvent.referer_domain)
    ).filter(
        AttributionReferrerEvent.timestamp > start_time,
        AttributionReferrerEvent.timestamp < end_time,
    ).group_by(AttributionReferrerEvent.referer_domain)
    res_dict = {}
    for res in attribution_embeddings:
        domain, count = res
        res_dict[domain] = count
    return res_dict