from fastapi import APIRouter, Query

from app.services.author_vs_btc_view import AuthorVsBtcViewRequest, build_author_vs_btc_view


router = APIRouter(prefix="/views")


@router.get("/author-vs-btc/{username}")
def author_vs_btc_view(
    username: str,
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return build_author_vs_btc_view(
        AuthorVsBtcViewRequest(
            username=username,
            granularity=granularity,
        )
    )
