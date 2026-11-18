from services.asset_stats import COMBINATIONS


def test_four_complete_combinations_are_always_defined() -> None:
    assert len(COMBINATIONS) == 4
    assert ("photo", "visible") in COMBINATIONS
    assert ("photo", "infrared") in COMBINATIONS
    assert ("hand_drawn", "visible") in COMBINATIONS
    assert ("hand_drawn", "infrared") in COMBINATIONS
