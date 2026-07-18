from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FormattingProfile:
    key: str
    name: str
    output_family: str
    page_size: str = "letter"
    base_font: str = "Liberation Serif"
    font_size: int = 12
    line_spacing: float = 1.5
    paragraph_indent_inches: float = 0.3
    paragraph_spacing_points: int = 0
    scene_break_marker: str = "* * *"
    chapter_page_break: bool = True
    page_numbers: bool = True
    artwork_handling: str = "fit"
    version: str = "publishing-profile-v1"


PROFILES = {
    profile.key: profile
    for profile in (
        FormattingProfile("clean_manuscript", "Clean manuscript", "prose"),
        FormattingProfile(
            "web_serial",
            "Web-serial reading copy",
            "web",
            line_spacing=1.3,
            chapter_page_break=False,
        ),
        FormattingProfile("novella", "Novella", "prose", font_size=11),
        FormattingProfile("standard_novel", "Standard novel", "prose", font_size=11),
        FormattingProfile(
            "screenplay",
            "Screenplay foundation",
            "script",
            base_font="Liberation Mono",
            paragraph_indent_inches=0,
        ),
        FormattingProfile(
            "comic_script",
            "Comic script foundation",
            "script",
            base_font="Liberation Mono",
            paragraph_indent_inches=0,
        ),
        FormattingProfile(
            "simple_archive",
            "Simple archive",
            "archive",
            line_spacing=1.0,
            paragraph_indent_inches=0,
        ),
        FormattingProfile("custom", "Custom", "custom"),
    )
}


def profile_for(project):
    return PROFILES.get(project.formatting_profile, PROFILES["clean_manuscript"])
