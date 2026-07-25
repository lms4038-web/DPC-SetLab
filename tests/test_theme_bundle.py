from pathlib import Path


def test_split_theme_bundle_exists():
    root = Path(__file__).resolve().parents[1]
    expected = {
        "theme.css", "base.css", "components.css", "desktop.css",
        "tablet.css", "mobile.css", "safari.css",
    }
    assert expected.issubset({p.name for p in (root / "styles").glob("*.css")})


def test_home_does_not_use_custom_oauth_anchor():
    root = Path(__file__).resolve().parents[1]
    app = (root / "app.py").read_text(encoding="utf-8")
    assert 'class="dpc-oauth-self" href=' not in app
    assert app.count("render_spotify_oauth_link(") >= 3


def test_mobile_theme_covers_high_risk_white_controls():
    root = Path(__file__).resolve().parents[1]
    css = (root / "styles" / "components.css").read_text(encoding="utf-8")
    for selector in ("stFileUploader", "stExpander", "button:disabled", "stLinkButton", "stDataFrame"):
        assert selector in css
