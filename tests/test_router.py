from clawless.router import route_message


def test_route_message_with_track() -> None:
    routed = route_message("hello #track:work")
    assert routed.track_name == "work"
    assert routed.text == "hello"


def test_route_message_without_track() -> None:
    routed = route_message("hello world")
    assert routed.track_name is None
