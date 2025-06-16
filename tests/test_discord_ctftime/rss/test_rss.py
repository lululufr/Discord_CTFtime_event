import pytest

import feedparser
from typing import Optional


class RSSException(RuntimeError):
    """Erreur générique du parseur RSS."""


def fetch_latest(url: str) -> Optional[feedparser.FeedParserDict]:
    """
    Récupère le flux RSS et renvoie la première entrée valide
    ou None s'il n'y a rien de nouveau.

    Lève RSSException si le flux est inaccessible ou mal formé.
    """
    flux = feedparser.parse(url)

    # 1. réseau
    if getattr(flux, "status", 200) != 200:
        raise RSSException(f"HTTP {flux.status} sur {url}")

    # 2. XML mal formé
    if flux.bozo:
        raise RSSException(f"Flux invalide : {flux.bozo_exception}")

    # 3. au moins une entrée
    if not flux.entries:
        return None

    entry = flux.entries[0]

    # 4. champs indispensables
    if not all(hasattr(entry, a) for a in ("title", "link")):
        raise RSSException("Entrée incomplète")

    return entry


def fake_feed(
    status=200,
    bozo=False,
    entries=None,
):
    """Construit un FeedParserDict minimal pour nos doubles de test."""
    return feedparser.FeedParserDict(
        status=status,
        bozo=bozo,
        bozo_exception=Exception("XML cassé") if bozo else None,
        entries=entries or [],
    )


def fake_entry(title="Art #1", link="https://exemple.com/a1"):
    return feedparser.FeedParserDict(title=title, link=link)


# ---------- cas OK ------------------------------------------------------------
def test_fetch_latest_succes(monkeypatch):
    monkeypatch.setattr(
        "feedparser.parse",
        lambda *_: fake_feed(entries=[fake_entry()]),
    )
    entry = fetch_latest("https://dummy")
    assert entry.title == "Art #1"
    assert entry.link == "https://exemple.com/a1"


# ---------- erreurs réseau / XML ---------------------------------------------
@pytest.mark.parametrize("code", [404, 500])
def test_http_error(monkeypatch, code):
    monkeypatch.setattr(
        "feedparser.parse",
        lambda *_: fake_feed(status=code),
    )
    with pytest.raises(RSSException):
        fetch_latest("https://dummy")


def test_xml_bozo(monkeypatch):
    monkeypatch.setattr(
        "feedparser.parse",
        lambda *_: fake_feed(bozo=True),
    )
    with pytest.raises(RSSException):
        fetch_latest("https://dummy")


# ---------- flux vide ---------------------------------------------------------
def test_flux_vide(monkeypatch):
    monkeypatch.setattr(
        "feedparser.parse",
        lambda *_: fake_feed(entries=[]),
    )
    assert fetch_latest("https://dummy") is None
