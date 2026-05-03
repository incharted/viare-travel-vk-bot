from services.tours import _apply_destination_filter


def test_destination_filter_is_applied_only_for_domestic_tours():
    params: list[object] = []

    query = _apply_destination_filter("SELECT * FROM tours WHERE 1 = 1", params, "domestic", "Sochi")

    assert "destination" in query
    assert params == ["Sochi"]


def test_destination_filter_is_not_applied_for_abroad_tours():
    params: list[object] = []

    query = _apply_destination_filter("SELECT * FROM tours WHERE 1 = 1", params, "abroad", "Kemer")

    assert query == "SELECT * FROM tours WHERE 1 = 1"
    assert params == []
