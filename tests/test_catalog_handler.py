from aiogram.types import FSInputFile

from app.bot.handlers.catalog import _photo_source, _place_text


def test_place_text_is_escaped_and_contains_human_readable_fields():
    text = _place_text(
        {
            "name": "A <Great> Place",
            "country": "France",
            "city": "Paris",
            "category": "Museums",
            "address": "1 <Main> St",
            "description": "Safe & interesting",
        }
    )

    assert "<b>A &lt;Great&gt; Place</b>" in text
    assert "<b>Country:</b> France" in text
    assert "<b>Address:</b> 1 &lt;Main&gt; St" in text
    assert "Safe &amp; interesting" in text


def test_place_text_truncates_long_description():
    text = _place_text(
        {
            "name": "Long Place",
            "country": "France",
            "city": "Paris",
            "category": "Museums",
            "description": "x" * 1900,
        }
    )

    assert len(text) < 2100
    assert text.endswith("...")


def test_photo_source_uses_local_file_or_external_url(tmp_path):
    image = tmp_path / "place.jpg"
    image.write_bytes(b"image")

    local = _photo_source({"image_url": "media/place.jpg", "image_path": str(image)})
    external = _photo_source({"image_url": "https://example.com/place.jpg"})

    assert isinstance(local, FSInputFile)
    assert local.path == str(image)
    assert external == "https://example.com/place.jpg"
