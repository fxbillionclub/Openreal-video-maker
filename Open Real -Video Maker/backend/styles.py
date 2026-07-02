"""
Style presets for the video engine.
Each style defines a color palette, particle motif, mood, voice tuning,
and the story-template used to break a one-line prompt into scenes
when the user doesn't already provide multiple sentences.
"""

STYLES = {
    "anime": {
        "name": "Anime Story",
        "emoji": "🌸",
        "gradient": [(255, 214, 224), (168, 168, 255), (120, 90, 200)],
        "particle": "petal",
        "particle_color": (255, 255, 255),
        "accent": (255, 105, 180),
        "text_color": (255, 255, 255),
        "vignette": (40, 10, 60),
        "voice_speed": 165,
        "voice_pitch": 55,
        "music_root": 261.6,  # C4, warm pad
        "music_scale": [0, 4, 7, 12],
        "templates": [
            "{topic}",
            "In a quiet town touched by magic, everything was about to change.",
            "Courage rose as the moment pushed them to their limit.",
            "In the end, it taught them what truly matters.",
        ],
    },
    "horror": {
        "name": "Suspense Horror",
        "emoji": "🕯️",
        "gradient": [(10, 8, 12), (60, 10, 15), (20, 5, 10)],
        "particle": "spark",
        "particle_color": (180, 30, 30),
        "accent": (200, 20, 20),
        "text_color": (230, 220, 220),
        "vignette": (0, 0, 0),
        "voice_speed": 130,
        "voice_pitch": 25,
        "music_root": 110.0,  # A2, low drone
        "music_scale": [0, 1, 6, 7],
        "templates": [
            "{topic}",
            "It was a dark, silent night, and strange whispers began.",
            "Fear spread as the presence grew closer, closer than ever.",
            "By morning, nothing was ever the same again.",
        ],
    },
    "comedy": {
        "name": "Absurd Comedy",
        "emoji": "🤪",
        "gradient": [(255, 221, 87), (255, 138, 61), (255, 87, 128)],
        "particle": "star",
        "particle_color": (255, 255, 255),
        "accent": (255, 235, 59),
        "text_color": (40, 20, 0),
        "vignette": (255, 200, 120),
        "voice_speed": 190,
        "voice_pitch": 70,
        "music_root": 392.0,  # G4, bouncy
        "music_scale": [0, 2, 4, 7],
        "templates": [
            "{topic}",
            "So this one time, it happened completely out of nowhere.",
            "Naturally, things got ridiculous from there on.",
            "And that's the chaotic true story of how it all went down.",
        ],
    },
    "scifi": {
        "name": "Sci-Fi Adventure",
        "emoji": "🚀",
        "gradient": [(5, 8, 30), (10, 30, 70), (30, 60, 120)],
        "particle": "star",
        "particle_color": (150, 220, 255),
        "accent": (0, 220, 255),
        "text_color": (220, 245, 255),
        "vignette": (0, 5, 20),
        "voice_speed": 155,
        "voice_pitch": 40,
        "music_root": 220.0,
        "music_scale": [0, 5, 7, 10],
        "templates": [
            "{topic}",
            "Far beyond known space, this was only the beginning.",
            "Against all odds, they pressed on into the unknown.",
            "A new future opened up, forever changed by what came next.",
        ],
    },
    "nature": {
        "name": "Nature & Pets",
        "emoji": "🐾",
        "gradient": [(200, 240, 210), (120, 200, 160), (60, 140, 120)],
        "particle": "leaf",
        "particle_color": (255, 255, 255),
        "accent": (76, 175, 80),
        "text_color": (20, 40, 20),
        "vignette": (30, 60, 40),
        "voice_speed": 160,
        "voice_pitch": 60,
        "music_root": 293.7,
        "music_scale": [0, 4, 7, 9],
        "templates": [
            "{topic}",
            "Out in the wild, curiosity took over pretty quickly.",
            "A funny, unexpected moment happened right after that.",
            "It was the perfect happy ending to a wonderful day.",
        ],
    },
    "history": {
        "name": "Ancient History",
        "emoji": "🏛️",
        "gradient": [(235, 210, 160), (180, 130, 80), (90, 60, 40)],
        "particle": "spark",
        "particle_color": (255, 215, 140),
        "accent": (200, 150, 60),
        "text_color": (255, 245, 225),
        "vignette": (40, 25, 10),
        "voice_speed": 145,
        "voice_pitch": 45,
        "music_root": 174.6,
        "music_scale": [0, 3, 5, 7],
        "templates": [
            "{topic}",
            "Long ago, in an age forgotten by time, empires rose and fell.",
            "Legends still speak of the moment everything changed.",
            "Even today, the story is remembered by all who hear it.",
        ],
    },
}

DEFAULT_STYLE = "anime"


def get_style(style_id: str) -> dict:
    return STYLES.get(style_id, STYLES[DEFAULT_STYLE])


def list_styles():
    return [
        {"id": k, "name": v["name"], "emoji": v["emoji"]} for k, v in STYLES.items()
    ]
