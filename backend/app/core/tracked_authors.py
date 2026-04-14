from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackedAuthorSeed:
    slug: str
    username: str
    sort_order: int


TRACKED_AUTHOR_SEEDS: tuple[TrackedAuthorSeed, ...] = (
    TrackedAuthorSeed(slug="michael-saylor", username="saylor", sort_order=1),
    TrackedAuthorSeed(slug="walker-america", username="WalkerAmerica", sort_order=2),
    TrackedAuthorSeed(slug="chris-millas", username="ChrisMMillas", sort_order=3),
    TrackedAuthorSeed(slug="richard-byworth", username="RichardByworth", sort_order=4),
    TrackedAuthorSeed(slug="andrew-webley", username="asjwebley", sort_order=5),
    TrackedAuthorSeed(slug="ray", username="artificialsub", sort_order=6),
    TrackedAuthorSeed(slug="stack-hodler", username="stackhodler", sort_order=7),
    TrackedAuthorSeed(slug="isabella", username="isabellasg3", sort_order=8),
    TrackedAuthorSeed(slug="oliver-velez", username="olvelez007", sort_order=9),
    TrackedAuthorSeed(slug="ben-werkman", username="Werkman", sort_order=10),
    TrackedAuthorSeed(slug="brian-brookshire", username="btc_overflow", sort_order=11),
    TrackedAuthorSeed(slug="brian-armstrong", username="brian_armstrong", sort_order=12),
    TrackedAuthorSeed(slug="cz-bnb", username="cz_binance", sort_order=13),
    TrackedAuthorSeed(slug="arthur-hayes", username="CryptoHayes", sort_order=14),
    TrackedAuthorSeed(slug="jesse-powell", username="jespow", sort_order=15),
    TrackedAuthorSeed(slug="jack-mallers", username="jackmallers", sort_order=16),
    TrackedAuthorSeed(slug="zynx", username="ZynxBTC", sort_order=17),
    TrackedAuthorSeed(slug="jesse-myers", username="Croesus_BTC", sort_order=18),
    TrackedAuthorSeed(slug="willy-woo", username="willywoo", sort_order=19),
    TrackedAuthorSeed(slug="andy-edstrom", username="edstromandrew", sort_order=20),
    TrackedAuthorSeed(slug="dan-hillery", username="hillery_dan", sort_order=21),
    TrackedAuthorSeed(slug="adrian-morris", username="_Adrian", sort_order=22),
    TrackedAuthorSeed(slug="jeff-walton", username="PunterJeff", sort_order=23),
    TrackedAuthorSeed(slug="nithu-sezni", username="nithusezni", sort_order=24),
    TrackedAuthorSeed(slug="mason", username="MasonFoard", sort_order=25),
    TrackedAuthorSeed(slug="british-hodl", username="BritishHodl", sort_order=26),
    TrackedAuthorSeed(slug="lyn-alden", username="LynAldenContact", sort_order=27),
    TrackedAuthorSeed(slug="professor-b21", username="ProfessorB21", sort_order=28),
    TrackedAuthorSeed(slug="btc-gus", username="Scavacini777", sort_order=29),
    TrackedAuthorSeed(slug="bit-paine", username="BitPaine", sort_order=30),
    TrackedAuthorSeed(slug="matt-cole", username="ColeMacro", sort_order=31),
    TrackedAuthorSeed(slug="parker-lewis", username="parkeralewis", sort_order=32),
    TrackedAuthorSeed(slug="kristen", username="2dogs1chic", sort_order=33),
    TrackedAuthorSeed(slug="dana-in-hawaii", username="Danainhawaii", sort_order=34),
    TrackedAuthorSeed(slug="parabolic-code", username="ParabolicCode", sort_order=35),
    TrackedAuthorSeed(slug="bitquant", username="BitQua", sort_order=36),
    TrackedAuthorSeed(slug="ed-juline", username="ejuline", sort_order=37),
    TrackedAuthorSeed(slug="alex-thorn", username="intangiblecoins", sort_order=38),
    TrackedAuthorSeed(slug="btc-teacher", username="BitcoinTeacher_", sort_order=39),
    TrackedAuthorSeed(slug="roaring-ragnar", username="RoaringRagnar", sort_order=40),
    TrackedAuthorSeed(slug="michael-sullivan", username="SullyMichaelvan", sort_order=41),
    TrackedAuthorSeed(slug="peter-schiff", username="PeterSchiff", sort_order=42),
)
