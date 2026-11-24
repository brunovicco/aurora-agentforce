"""Regression checks for the reduced Aurora customer interface."""

import json
import unicodedata

from scripts import portal_prepare as portal


def test_home_surface_is_reduced() -> None:
    home = json.loads((portal.ROOT / portal.BUNDLE / "views/início.json").read_text())
    components = [
        component for region in home["regions"] for component in region.get("components", [])
    ]
    assert {component["componentName"] for component in components} == {
        "forceCommunity:headline",
        "forceCommunity:seoAssistant",
    }
    headline = next(c for c in components if c["componentName"] == "forceCommunity:headline")
    assert headline["componentAttributes"]["showSubTopics"] is False
    assert "Aurora" in headline["componentAttributes"]["title"]
    assert "ainda não está disponível" in headline["componentAttributes"]["bannerText"]


def test_shared_theme_shortcuts_are_reduced() -> None:
    theme = json.loads(
        (portal.ROOT / portal.BUNDLE / "themes/atendimentoAoCliente.json").read_text()
    )
    inner = next(view for view in theme["views"] if view["id"] == theme["layouts"]["Inner"])
    regions = {region["regionName"]: region for region in inner["regions"]}
    assert not regions["search"].get("components")
    profile = regions["profileMenu"]["components"][0]["componentAttributes"]
    assert profile["includeContactSupport"] is False
    assert profile["includeMessages"] is False
    navigation = regions["navBar"]["components"][0]["componentAttributes"]
    assert navigation["hideAppLauncher"] is True


def test_route_inventory_matches_metadata() -> None:
    inventory = json.loads((portal.ROOT.parent / "portal-route-inventory.json").read_text())
    actual = [
        unicodedata.normalize("NFC", path.name)
        for path in (portal.ROOT / portal.BUNDLE / "routes").glob("*.json")
    ]
    assert len(actual) == len(set(actual)) == 55
    assert sorted(inventory) == sorted(actual)
