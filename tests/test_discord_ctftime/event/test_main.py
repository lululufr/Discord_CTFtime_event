from discord_ctftime.event import Event


evt = Event(
    1122334455,
    "Test Event",
    "https://google.com",
    "12 juin",
    "13 juin",
    "Lorem Ipsum adipiscing elit...",
)


def test_add_participant():
    participant = "testuser123"
    evt.add_participants(participant)

    assert participant in evt.participants

