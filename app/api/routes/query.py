from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException

from app.core.schemas.query import QueryRequest, QueryResponse
from app.query.service import QueryServiceError, run_query

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def query_endpoint(payload: QueryRequest) -> QueryResponse:
    start_time = time.time()

    try:
        print("=== /query REQUEST ===")
        print(payload.model_dump())

        result = run_query(payload)

        duration = time.time() - start_time
        print("=== /query PARSED INPUT ===")
        print(result.parsed_input.model_dump())
        print("=== /query FINAL OUTPUT ===")
        print(result.output.model_dump())
        print(f"=== /query TOTAL TIME: {duration:.3f}s ===")

        return result

    except QueryServiceError as e:
        print(f"QUERY ERROR (400): {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        print(f"QUERY ERROR (500): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing query",
        )