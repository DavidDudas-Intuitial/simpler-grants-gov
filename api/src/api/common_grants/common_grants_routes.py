"""CommonGrants Protocol routes."""

import logging

from common_grants_sdk.schemas.marshmallow import (
    OpportunitiesListResponse as OpportunitiesListResponseSchema,
)
from common_grants_sdk.schemas.marshmallow import (
    OpportunitiesSearchResponse as OpportunitiesSearchResponseSchema,
)
from common_grants_sdk.schemas.marshmallow import OpportunityResponse as OpportunityResponseSchema
from common_grants_sdk.schemas.marshmallow import (
    OpportunitySearchRequest as OpportunitySearchRequestSchema,
)
from common_grants_sdk.schemas.marshmallow import PaginatedQueryParams as PaginatedQueryParamsSchema
from common_grants_sdk.schemas.pydantic.requests.opportunity import OpportunitySearchRequest

import src.adapters.db as db
import src.adapters.db.flask_db as flask_db
import src.adapters.search as search
import src.adapters.search.flask_opensearch as flask_opensearch
from src.api.common_grants.common_grants_blueprint import common_grants_blueprint
from src.api.route_utils import raise_flask_error
from src.auth.multi_auth import api_key_multi_auth, api_key_multi_auth_security_schemes
from src.logging.flask_logger import add_extra_data_to_current_request_logs
from src.services.common_grants.opportunity_service import CommonGrantsOpportunityService

logger = logging.getLogger(__name__)


@common_grants_blueprint.get("/opportunities")
@common_grants_blueprint.input(PaginatedQueryParamsSchema, location="query")
@common_grants_blueprint.output(OpportunitiesListResponseSchema)
@api_key_multi_auth.login_required
@common_grants_blueprint.doc(
    summary="List opportunities",
    description="Get a paginated list of opportunities, sorted by `lastModifiedAt` with most recent first.",
    security=api_key_multi_auth_security_schemes,
    responses=[200],
)
@flask_opensearch.with_search_client()
def list_opportunities(search_client: search.SearchClient, query_data: dict) -> tuple[dict, int]:
    """Get a paginated list of opportunities."""
    add_extra_data_to_current_request_logs(query_data)
    logger.info("GET /common-grants/opportunities/")

    # Fetch data from service
    response_object = CommonGrantsOpportunityService.list_opportunities(
        search_client=search_client,
        page=int(query_data.get("page", 1)),
        page_size=int(query_data.get("pageSize", 10)),
    )

    return response_object, 200


@common_grants_blueprint.get("/opportunities/<oppId>")
@common_grants_blueprint.output(OpportunityResponseSchema)
@api_key_multi_auth.login_required
@common_grants_blueprint.doc(
    summary="View opportunity details",
    description="View details about an opportunity",
    security=api_key_multi_auth_security_schemes,
    responses=[200, 404],
)
@flask_db.with_db_session()
def get_opportunity(db_session: db.Session, oppId: str) -> tuple[dict, int]:
    """Get a specific opportunity by ID."""
    add_extra_data_to_current_request_logs({"oppId": oppId})
    logger.info("GET /common-grants/opportunities/{oppId}")

    # Fetch data from service
    with db_session.begin():
        response_object = CommonGrantsOpportunityService.get_opportunity(db_session, oppId)

    # Check for not found condition
    if not response_object:
        raise_flask_error(404, "The server cannot find the requested resource")

    return response_object, 200


@common_grants_blueprint.post("/opportunities/search")
@common_grants_blueprint.input(OpportunitySearchRequestSchema)
@common_grants_blueprint.output(OpportunitiesSearchResponseSchema)
@api_key_multi_auth.login_required
@common_grants_blueprint.doc(
    summary="Search opportunities",
    description="Search for opportunities based on the provided filters",
    security=api_key_multi_auth_security_schemes,
    responses=[200],
)
@flask_opensearch.with_search_client()
def search_opportunities(search_client: search.SearchClient, json_data: dict) -> tuple[dict, int]:
    """Search for opportunities based on the provided filters."""
    add_extra_data_to_current_request_logs(json_data)
    logger.info("POST /common-grants/opportunities/search")

    # Validate input
    request_schema = OpportunitySearchRequestSchema()
    try:
        validated_input = request_schema.load(json_data)
        search_request = OpportunitySearchRequest(**validated_input)
    except Exception:
        raise_flask_error(422, "Unable to validate search request schema")

    # Perform search
    response_object = CommonGrantsOpportunityService.search_opportunities(
        search_client,
        search_request.filters,
        search_request.sorting,
        search_request.pagination,
        search_request.search,
    )

    return response_object, 200
