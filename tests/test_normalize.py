"""Network-free tests for googleflights_mcp.flights.normalize()."""

from fast_flights.parser import (
    Airline,
    Airport,
    CarbonEmission,
    Flights,
    JsMetadata,
    ResultList,
    SimpleDatetime,
    SingleFlight,
)

from googleflights_mcp.flights import normalize


def _leg(from_code, to_code, dep, arr, duration, plane_type="A320"):
    return SingleFlight(
        from_airport=Airport(name=f"{from_code} Airport", code=from_code),
        to_airport=Airport(name=f"{to_code} Airport", code=to_code),
        departure=SimpleDatetime(date=dep[0], time=dep[1]),
        arrival=SimpleDatetime(date=arr[0], time=arr[1]),
        duration=duration,
        plane_type=plane_type,
    )


def _make_result() -> ResultList:
    direct = Flights(
        type="Nonstop",
        price=2715,
        airlines=["TK"],
        flights=[
            _leg(
                "IST",
                "AYT",
                ((2026, 9, 14), (21, 15)),
                ((2026, 9, 14), (22, 40)),
                85,
            )
        ],
        carbon=CarbonEmission(typical_on_route=130000, emission=123000),
    )
    one_stop = Flights(
        type="1 stop",
        price=1999,
        airlines=["PC"],
        flights=[
            _leg(
                "IST",
                "ESB",
                ((2026, 9, 14), (10, 0)),
                ((2026, 9, 14), (11, 10)),
                70,
            ),
            _leg(
                "ESB",
                "AYT",
                ((2026, 9, 14), (12, 30)),
                ((2026, 9, 14), (13, 45)),
                75,
            ),
        ],
        carbon=CarbonEmission(typical_on_route=150000, emission=160000),
    )

    result = ResultList([direct, one_stop])
    result.metadata = JsMetadata(
        airlines=[
            Airline(code="TK", name="Turkish Airlines"),
            Airline(code="PC", name="Pegasus"),
        ],
        alliances=[],
    )
    return result


def test_normalize_sorts_by_price_ascending():
    options = normalize(_make_result(), currency="TRY")
    assert [o["price"] for o in options] == [1999, 2715]


def test_normalize_schema_and_labels():
    options = normalize(_make_result(), currency="TRY")
    cheapest, direct = options[0], options[1]

    assert cheapest["airlines"] == ["Pegasus"]
    assert cheapest["stops"] == 1
    assert cheapest["stops_label"] == "1 aktarma"
    assert cheapest["duration_minutes"] == 145
    assert cheapest["duration_label"] == "2h 25m"
    assert len(cheapest["legs"]) == 2
    assert cheapest["legs"][0] == {
        "from": "IST",
        "to": "ESB",
        "departure": "2026-09-14 10:00",
        "arrival": "2026-09-14 11:10",
        "duration_minutes": 70,
        "plane_type": "A320",
    }

    assert direct["airlines"] == ["Turkish Airlines"]
    assert direct["stops"] == 0
    assert direct["stops_label"] == "direkt"
    assert direct["duration_minutes"] == 85
    assert direct["duration_label"] == "1h 25m"
    assert direct["currency"] == "TRY"
    assert direct["carbon_grams"] == 123000
    assert direct["carbon_vs_typical_grams"] == 130000


def test_normalize_falls_back_to_airline_code_when_name_unknown():
    result = _make_result()
    result.metadata = JsMetadata(airlines=[], alliances=[])
    options = normalize(result, currency="USD")
    assert options[0]["airlines"] == ["PC"]
    assert options[1]["airlines"] == ["TK"]
