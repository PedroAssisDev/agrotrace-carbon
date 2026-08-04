"""Calculation-context HTTP routes (7 endpoints)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from provenance_service.application.services.provenance_recorder import (
    ParameterValueInput,
    RecordCalculationExecutionCommand,
    RecordCalculationMethodCommand,
    RecordCalculationMethodVersionCommand,
    RecordCalculationParameterSetCommand,
    RecordCalculationResultSetCommand,
    RecordCalculationReviewCommand,
    RecordResultAggregationLinkCommand,
    RecordResultPublicationCommand,
    ResultItemInput,
)
from provenance_service.application.use_cases import (
    RegisterCalculationExecution,
    RegisterCalculationMethod,
    RegisterCalculationMethodVersion,
    RegisterCalculationParameterSet,
    RegisterCalculationResultSet,
    RegisterCalculationReview,
    RegisterResultAggregationLink,
    RegisterResultPublication,
)
from provenance_service.domain.shared.errors import NotFoundError
from provenance_service.interfaces.api.deps import (
    SessionFactoryDep,
    provide_register_calculation_execution,
    provide_register_calculation_method,
    provide_register_calculation_method_version,
    provide_register_calculation_parameter_set,
    provide_register_calculation_result_set,
    provide_register_calculation_review,
    provide_register_result_aggregation_link,
    provide_register_result_publication,
)
from provenance_service.interfaces.api.schemas.calculation import (
    CalculationExecutionResponse,
    CalculationMethodResponse,
    CalculationMethodVersionResponse,
    CalculationParameterSetResponse,
    CalculationResultAggregationLinkListResponse,
    CalculationResultAggregationLinkResponse,
    CalculationResultItemResponse,
    CalculationResultSetResponse,
    CalculationReviewResponse,
    RegisterCalculationExecutionRequest,
    RegisterCalculationMethodRequest,
    RegisterCalculationMethodVersionRequest,
    RegisterCalculationParameterSetRequest,
    RegisterCalculationResultSetRequest,
    RegisterCalculationReviewRequest,
    RegisterResultAggregationLinkRequest,
    RegisterResultPublicationRequest,
    ResultPublicationExecutionResponse,
)
from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(tags=["calculation"])


@router.post(
    "/calculation-methods",
    response_model=CalculationMethodResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_calculation_method(
    payload: RegisterCalculationMethodRequest,
    use_case: Annotated[
        RegisterCalculationMethod, Depends(provide_register_calculation_method)
    ],
) -> CalculationMethodResponse:
    cmd = RecordCalculationMethodCommand(**payload.model_dump())
    method = use_case.execute(cmd)
    return CalculationMethodResponse.model_validate(method)


@router.post(
    "/calculation-method-versions",
    response_model=CalculationMethodVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_calculation_method_version(
    payload: RegisterCalculationMethodVersionRequest,
    use_case: Annotated[
        RegisterCalculationMethodVersion,
        Depends(provide_register_calculation_method_version),
    ],
) -> CalculationMethodVersionResponse:
    cmd = RecordCalculationMethodVersionCommand(**payload.model_dump())
    version = use_case.execute(cmd)
    return CalculationMethodVersionResponse.model_validate(version)


@router.post(
    "/parameter-sets",
    response_model=CalculationParameterSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_parameter_set(
    payload: RegisterCalculationParameterSetRequest,
    use_case: Annotated[
        RegisterCalculationParameterSet,
        Depends(provide_register_calculation_parameter_set),
    ],
) -> CalculationParameterSetResponse:
    body = payload.model_dump()
    raw_values = body.pop("values", []) or []
    values = [ParameterValueInput(**v) for v in raw_values]
    cmd = RecordCalculationParameterSetCommand(**body, values=values)
    param_set = use_case.execute(cmd)
    return CalculationParameterSetResponse.model_validate(param_set)


@router.post(
    "/calculation-executions",
    response_model=CalculationExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_calculation_execution(
    payload: RegisterCalculationExecutionRequest,
    use_case: Annotated[
        RegisterCalculationExecution, Depends(provide_register_calculation_execution)
    ],
) -> CalculationExecutionResponse:
    cmd = RecordCalculationExecutionCommand(**payload.model_dump())
    execution = use_case.execute(cmd)
    return CalculationExecutionResponse.model_validate(execution)


@router.post(
    "/calculation-result-sets",
    response_model=CalculationResultSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_calculation_result_set(
    payload: RegisterCalculationResultSetRequest,
    use_case: Annotated[
        RegisterCalculationResultSet,
        Depends(provide_register_calculation_result_set),
    ],
    session_factory: SessionFactoryDep,
) -> CalculationResultSetResponse:
    body = payload.model_dump()
    raw_items = body.pop("items", []) or []
    items = [ResultItemInput(**v) for v in raw_items]
    cmd = RecordCalculationResultSetCommand(**body, items=items)
    result_set = use_case.execute(cmd)
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        result_items = uow.calculation_result_sets.list_items(
            result_set.calculation_result_set_id
        )
    response = CalculationResultSetResponse.model_validate(result_set)
    response.items = [
        CalculationResultItemResponse.model_validate(item) for item in result_items
    ]
    return response


@router.get(
    "/calculation-result-sets/{calculation_result_set_id}",
    response_model=CalculationResultSetResponse,
)
def get_calculation_result_set(
    calculation_result_set_id: UUID,
    session_factory: SessionFactoryDep,
) -> CalculationResultSetResponse:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        result_set = uow.calculation_result_sets.get(calculation_result_set_id)
        if result_set is None:
            raise NotFoundError(
                f"CalculationResultSet {calculation_result_set_id} not found"
            )
        items = uow.calculation_result_sets.list_items(calculation_result_set_id)
    response = CalculationResultSetResponse.model_validate(result_set)
    response.items = [
        CalculationResultItemResponse.model_validate(item) for item in items
    ]
    return response


@router.post(
    "/calculation-reviews",
    response_model=CalculationReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_calculation_review(
    payload: RegisterCalculationReviewRequest,
    use_case: Annotated[
        RegisterCalculationReview, Depends(provide_register_calculation_review)
    ],
) -> CalculationReviewResponse:
    cmd = RecordCalculationReviewCommand(**payload.model_dump())
    review = use_case.execute(cmd)
    return CalculationReviewResponse.model_validate(review)


@router.post(
    "/result-publications",
    response_model=ResultPublicationExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_result_publication(
    payload: RegisterResultPublicationRequest,
    use_case: Annotated[
        RegisterResultPublication, Depends(provide_register_result_publication)
    ],
) -> ResultPublicationExecutionResponse:
    cmd = RecordResultPublicationCommand(**payload.model_dump())
    publication = use_case.execute(cmd)
    return ResultPublicationExecutionResponse.model_validate(publication)


@router.post(
    "/result-aggregation-links",
    response_model=CalculationResultAggregationLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_result_aggregation_link(
    payload: RegisterResultAggregationLinkRequest,
    use_case: Annotated[
        RegisterResultAggregationLink,
        Depends(provide_register_result_aggregation_link),
    ],
) -> CalculationResultAggregationLinkResponse:
    cmd = RecordResultAggregationLinkCommand(**payload.model_dump())
    link = use_case.execute(cmd)
    return CalculationResultAggregationLinkResponse.model_validate(link)


@router.get(
    "/calculation-result-sets/{calculation_result_set_id}/aggregation-children",
    response_model=CalculationResultAggregationLinkListResponse,
)
def list_aggregation_children(
    calculation_result_set_id: UUID,
    session_factory: SessionFactoryDep,
) -> CalculationResultAggregationLinkListResponse:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        result_set = uow.calculation_result_sets.get(calculation_result_set_id)
        if result_set is None:
            raise NotFoundError(
                f"CalculationResultSet {calculation_result_set_id} not found"
            )
        links = uow.result_aggregation_links.list_children(calculation_result_set_id)
    return CalculationResultAggregationLinkListResponse(
        items=[
            CalculationResultAggregationLinkResponse.model_validate(link)
            for link in links
        ]
    )


@router.get(
    "/calculation-result-sets/{calculation_result_set_id}/aggregation-parents",
    response_model=CalculationResultAggregationLinkListResponse,
)
def list_aggregation_parents(
    calculation_result_set_id: UUID,
    session_factory: SessionFactoryDep,
) -> CalculationResultAggregationLinkListResponse:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        result_set = uow.calculation_result_sets.get(calculation_result_set_id)
        if result_set is None:
            raise NotFoundError(
                f"CalculationResultSet {calculation_result_set_id} not found"
            )
        links = uow.result_aggregation_links.list_parents(calculation_result_set_id)
    return CalculationResultAggregationLinkListResponse(
        items=[
            CalculationResultAggregationLinkResponse.model_validate(link)
            for link in links
        ]
    )
