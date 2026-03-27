from fastapi import APIRouter, Query

from app.services.author_vs_btc_view import AuthorVsBtcViewRequest, build_author_vs_btc_view


router = APIRouter(prefix="/views")


@router.get("/michael-saylor-vs-btc")
def michael_saylor_vs_btc_view(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return build_author_vs_btc_view(
        AuthorVsBtcViewRequest(
            username="saylor",
            granularity=granularity,
            view_name="michael-saylor-vs-btc",
        )
    )
