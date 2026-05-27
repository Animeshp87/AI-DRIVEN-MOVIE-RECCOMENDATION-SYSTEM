import base64
import html as html_module
import pickle
import random
import urllib.parse
from datetime import datetime
from pathlib import Path
import io
import os
import textwrap

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(
    page_title="AI Driven Movie Recommendation with Streaming",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

_APP_DIR = Path(__file__).resolve().parent
for dir_name in ("movie_posters", "assets"):
    p = _APP_DIR / dir_name
    p.mkdir(parents=True, exist_ok=True)

_DUMMY_STREAM_PATH = _APP_DIR / "assets" / "dummy.mp4"
DUMMY_STREAM_URL = (
    str(_DUMMY_STREAM_PATH)
    if _DUMMY_STREAM_PATH.exists()
    else "https://samplelib.com/lib/preview/mp4/sample-5s.mp4"
)

# ============================================================
# 4-LOGON KI DIVISION (Code comments mein hi “who does what”)
#
# Person 1: DATABASE MANAGER
# - `main.py` mein `movies_list.pkl` + `similarity.pkl` banaye jaate hain.
# - Is `app.py` mein unko load kiya jaata hai: `load_movie_data()` + `load_movie_meta()`.
#
# Person 2: POSTER / ASSET WORKER
# - `create_sample_poster()` generate karta hai (local posters) agar real posters available na hon.
# - Posters ko base64 mein convert karke UI mein embed kiya jaata hai (`poster_b64`).
# - Streaming button pe dummy video play hota hai (demo for streaming model).
# - Dummy streaming video (`assets/dummy.mp4`) create/serve hota hai.
#
# Person 3: RECOMMENDER BACKEND
# - `recommend()` cosine-similarity se similar movies pick karta hai.
# - Trailer/stream searching URLs banata hai.
#
# Person 4: FRONTEND / UI
# - Streamlit + HTML/CSS (unsafe_allow_html) se cards, layout, theme, animations render karta hai.

# ============================================================

# Predefined color schemes for posters
COLOR_SCHEMES = [
    [(41, 128, 185), (52, 152, 219)],
    [(155, 89, 182), (142, 68, 173)],
    [(46, 204, 113), (39, 174, 96)],
    [(241, 196, 15), (243, 156, 18)],
    [(231, 76, 60), (192, 57, 43)],
]


# --------------------- Person 2: POSTER / ASSET WORKER ---------------------
# These functions generate local poster images (no external poster source required).
# `create_sample_poster()` is also used as a safe fallback if real assets are missing.
def create_gradient_background(width, height):
    color1, color2 = random.choice(COLOR_SCHEMES)
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    X, Y = np.meshgrid(x, y)
    gradient = (X + Y) / 2
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(3):
        img[:, :, i] = np.interp(gradient, [0, 1], [color1[i], color2[i]])
    return Image.fromarray(img)


def create_sample_poster(movie_title, movie_id):
    try:
        poster_path = str(_APP_DIR / "movie_posters" / f"movie_{movie_id}.png")
        if os.path.exists(poster_path):
            try:
                with Image.open(poster_path) as img:
                    img.verify()
                return poster_path
            except OSError:
                os.remove(poster_path)

        width, height = 500, 750
        img = create_gradient_background(width, height)
        draw = ImageDraw.Draw(img)
        font_size = 60
        font = None
        wrapped_text = movie_title

        while font_size > 20:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
                wrapped_text = textwrap.fill(movie_title, width=int(20 * 40 / font_size))
                text_bbox = draw.textbbox((0, 0), wrapped_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                if text_width < width - 60:
                    break
            except OSError:
                pass
            font_size -= 5

        if font is None:
            font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), wrapped_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        draw.rectangle([0, 0, width, 100], fill=(0, 0, 0, 128))
        draw.rectangle([0, height - 100, width, height], fill=(0, 0, 0, 128))
        shadow_offset = 3
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            wrapped_text,
            fill=(0, 0, 0, 128),
            font=font,
        )
        draw.text((x, y), wrapped_text, fill="white", font=font)
        line_color = "white"
        line_width = 3
        draw.line([(30, 30), (width - 30, 30)], fill=line_color, width=line_width)
        draw.line([(30, 40), (width - 30, 40)], fill=line_color, width=line_width)
        draw.line([(30, height - 30), (width - 30, height - 30)], fill=line_color, width=line_width)
        draw.line([(30, height - 40), (width - 30, height - 40)], fill=line_color, width=line_width)

        small_font_size = 30
        try:
            small_font = ImageFont.truetype("arial.ttf", small_font_size)
        except OSError:
            small_font = ImageFont.load_default()

        id_text = f"MOVIE ID: {movie_id}"
        id_bbox = draw.textbbox((0, 0), id_text, font=small_font)
        id_width = id_bbox[2] - id_bbox[0]
        draw.text(((width - id_width) // 2, 35), id_text, fill="white", font=small_font)

        year_text = f"© {datetime.now().year}"
        year_bbox = draw.textbbox((0, 0), year_text, font=small_font)
        year_width = year_bbox[2] - year_bbox[0]
        draw.text(((width - year_width) // 2, height - 60), year_text, fill="white", font=small_font)

        img.save(poster_path, format="PNG", quality=95, optimize=True)
        return poster_path
    except Exception as e:
        st.error(f"Error creating poster: {str(e)}")
        error_img = Image.new("RGB", (500, 750), (47, 53, 66))
        error_draw = ImageDraw.Draw(error_img)
        error_draw.text((100, 375), "Error creating poster", fill="white")
        error_img.save(poster_path)
        return poster_path


# --------------------- Person 1: DATABASE MANAGER ---------------------
# Pickle files read (fast) + CSV meta read (genres + vote_average).
@st.cache_data
def _load_movie_data_from_disk():
    """Load pickles from the app folder. Only successful reads are cached."""
    mpath = _APP_DIR / "movies_list.pkl"
    spath = _APP_DIR / "similarity.pkl"
    with open(mpath, "rb") as f:
        movies = pickle.load(f)
    with open(spath, "rb") as f:
        similarity = pickle.load(f)
    if "title" not in getattr(movies, "columns", []):
        raise ValueError("movies data must include a 'title' column.")
    return movies, similarity


def load_movie_data():
    try:
        return _load_movie_data_from_disk()
    except Exception as e:
        st.error(
            "Failed to load movie data. Put **movies_list.pkl** and **similarity.pkl** in the same "
            f"folder as **app.py**, or run **main.py** to generate them. Details: {e}"
        )
        return None, None


# --------------------- Person 1: DATABASE MANAGER ---------------------
@st.cache_data
def load_movie_meta():
    path = _APP_DIR / "dataset.csv"
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path)
        meta = {}
        for _, r in df.iterrows():
            try:
                mid = int(r["id"])
            except (ValueError, TypeError, KeyError):
                continue
            g = r.get("genre", "")
            va = r.get("vote_average", 0)
            try:
                va = float(va) if pd.notna(va) else 0.0
            except (TypeError, ValueError):
                va = 0.0
            meta[mid] = {
                "genre": str(g) if pd.notna(g) else "",
                "vote_average": va,
            }
        return meta
    except Exception:
        return {}


def rating_stars_html(vote_average):
    if vote_average is None or vote_average <= 0:
        return '<div class="star-row"><span class="star-muted">No rating</span></div>'
    stars_5 = min(5.0, max(0.0, float(vote_average) / 2.0))
    full = int(stars_5)
    half = 1 if (stars_5 - full) >= 0.45 else 0
    empty = 5 - full - half
    parts = ['<span class="star full">★</span>' for _ in range(full)]
    if half:
        parts.append('<span class="star half">★</span>')
    parts.extend(['<span class="star empty">☆</span>' for _ in range(empty)])
    return (
        f'<div class="star-row" title="{vote_average:.1f}/10">'
        f'{"".join(parts)}'
        f'<span class="star-score">{vote_average:.1f}/10</span></div>'
    )


def genre_badges_html(genre_str):
    if not genre_str or str(genre_str).lower() == "nan":
        return ""
    parts = [p.strip() for p in str(genre_str).split(",") if p.strip()]
    if not parts:
        return ""
    badges = "".join(
        f'<span class="genre-badge">{html_module.escape(p)}</span>' for p in parts[:8]
    )
    return f'<div class="genre-row">{badges}</div>'


def trailer_search_url(title):
    q = urllib.parse.quote_plus(f"{title} official trailer")
    return f"https://www.youtube.com/results?search_query={q}"


def poster_b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def build_theme_css(dark: bool) -> str:
    if dark:
        bg = "linear-gradient(145deg, #0a1628 0%, #1a3a52 40%, #0d2137 100%)"
        fg = "#e8f1f8"
        muted = "rgba(255,255,255,0.72)"
        glass_bg = "rgba(255, 255, 255, 0.09)"
        glass_border = "rgba(255, 255, 255, 0.16)"
        accent = "#7ee8fa"
        accent2 = "#38ef7d"
    else:
        bg = "linear-gradient(145deg, #e0f2fe 0%, #fae8ff 45%, #fef3c7 100%)"
        fg = "#0f172a"
        muted = "rgba(15,23,42,0.75)"
        glass_bg = "rgba(255, 255, 255, 0.55)"
        glass_border = "rgba(15, 23, 42, 0.12)"
        accent = "#0369a1"
        accent2 = "#059669"

    light_extra = ""
    if not dark:
        light_extra = """
    .movie-title { color: #0369a1 !important; background: rgba(255,255,255,0.55) !important; }
    .genre-badge { border-color: rgba(15,23,42,0.15) !important; }
    .match-score { background: rgba(255,255,255,0.65) !important; color: #0369a1 !important; }
    """

    return f"""
    <style>
    .stApp {{
        background: {bg};
        color: {fg};
        font-family: 'Segoe UI', system-ui, sans-serif;
    }}
    .stApp header {{ background: transparent; }}
    [data-testid="stSidebar"] {{
        background: {glass_bg};
        border-right: 1px solid {glass_border};
        backdrop-filter: blur(14px);
    }}
    .top-loader {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        z-index: 99999;
        background: linear-gradient(90deg, {accent}, {accent2}, {accent});
        background-size: 200% 100%;
        animation: loader-slide 1.2s ease infinite;
    }}
    @keyframes loader-slide {{
        0% {{ background-position: 0% 50%; }}
        100% {{ background-position: 200% 50%; }}
    }}
    @keyframes btn-pulse {{
        0%, 100% {{ box-shadow: 0 4px 20px rgba(56, 239, 125, 0.25); }}
        50% {{ box-shadow: 0 6px 28px rgba(126, 232, 250, 0.45); }}
    }}
    .glass-nav {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 1rem 1.25rem;
        margin-bottom: 1.25rem;
        border-radius: 20px;
        background: {glass_bg};
        border: 1px solid {glass_border};
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    }}
    .glass-nav a {{
        color: {fg};
        text-decoration: none;
        font-weight: 600;
        padding: 0.45rem 0.9rem;
        border-radius: 999px;
        transition: background 0.25s ease, transform 0.2s ease;
    }}
    .glass-nav a:hover {{
        background: rgba(126, 232, 250, 0.2);
        transform: translateY(-1px);
    }}
    .glass-nav .brand {{
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: 0.02em;
        background: linear-gradient(90deg, {accent}, {accent2});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .glass-nav .links {{ display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }}
    .search-shell {{
        border-radius: 16px;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0 1.25rem;
        background: {glass_bg};
        border: 1px solid {glass_border};
        backdrop-filter: blur(14px);
    }}
    .search-shell h3 {{
        margin: 0 0 0.75rem 0;
        color: {accent2};
        font-size: 1.05rem;
    }}
    .selected-preview {{
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.8rem;
        margin: 0 0 1rem;
        border-radius: 16px;
        background: {glass_bg};
        border: 1px solid {glass_border};
    }}
    .selected-preview .selected-title {{
        font-size: 1rem;
        font-weight: 700;
        color: {accent};
        margin: 0;
    }}
    .selected-preview .selected-sub {{
        margin: 0.25rem 0 0;
        color: {muted};
        font-size: 0.9rem;
    }}
    .movie-card-glass {{
        background: {glass_bg};
        padding: 1.5rem;
        border-radius: 22px;
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        margin-bottom: 2rem;
        transition: transform 0.35s ease, box-shadow 0.35s ease;
        border: 1px solid {glass_border};
    }}
    .movie-card-glass:hover {{
        transform: translateY(-6px);
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
    }}
    .movie-title {{
        font-size: 1.35rem;
        margin: 0 0 0.75rem 0;
        color: {accent};
        text-align: center;
        padding: 0.85rem;
        background: rgba(0, 0, 0, 0.18);
        border-radius: 14px;
        font-weight: 700;
    }}
    {light_extra}
    .poster-frame {{
        border-radius: 16px;
        overflow: hidden;
        margin: 1rem 0;
        box-shadow: 0 12px 28px rgba(0,0,0,0.35);
    }}
    .poster-frame img {{
        display: block;
        width: 100%;
        transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}
    .poster-frame:hover img {{
        transform: scale(1.08);
    }}
    .genre-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        justify-content: center;
        margin: 0.6rem 0 0.4rem;
    }}
    .genre-badge {{
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        background: linear-gradient(45deg, rgba(17, 153, 142, 0.35), rgba(56, 239, 125, 0.35));
        border: 1px solid rgba(255,255,255,0.25);
        color: {fg};
    }}
    .star-row {{
        text-align: center;
        margin: 0.5rem 0;
        font-size: 1.15rem;
        letter-spacing: 2px;
    }}
    .star.full {{ color: #fbbf24; text-shadow: 0 0 12px rgba(251, 191, 36, 0.5); }}
    .star.half {{
        background: linear-gradient(90deg, #fbbf24 50%, {muted} 50%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .star.empty {{ color: {muted}; }}
    .star-muted {{ color: {muted}; font-size: 0.95rem; }}
    .star-score {{
        margin-left: 0.5rem;
        font-size: 0.9rem;
        color: {muted};
        letter-spacing: normal;
    }}
    .match-score {{
        text-align: center;
        color: {accent};
        font-size: 1.1rem;
        margin-top: 0.5rem;
        padding: 0.5rem 1rem;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 999px;
        display: inline-block;
        position: relative;
        left: 50%;
        transform: translateX(-50%);
    }}
    .action-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        justify-content: center;
        margin-top: 1rem;
    }}
    .btn-trailer, .btn-stream {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.65rem 1.5rem;
        border-radius: 999px;
        font-weight: 600;
        text-decoration: none;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        animation: btn-pulse 3s ease-in-out infinite;
    }}
    .btn-trailer {{
        background: linear-gradient(45deg, #6366f1, #a855f7);
        color: white !important;
        box-shadow: 0 4px 18px rgba(99, 102, 241, 0.4);
    }}
    .btn-stream {{
        background: linear-gradient(45deg, #ff416c, #ff4b2b);
        color: white !important;
        box-shadow: 0 4px 18px rgba(255, 65, 108, 0.35);
    }}
    .btn-trailer:hover, .btn-stream:hover {{
        transform: translateY(-3px) scale(1.02);
    }}
    .streaming-note {{
        margin-top: 0.85rem;
        border-radius: 12px;
        padding: 0.55rem 0.75rem;
        background: rgba(56, 239, 125, 0.14);
        border: 1px solid rgba(56, 239, 125, 0.35);
        color: {fg};
        text-align: center;
    }}
    .site-footer {{
        text-align: center;
        padding: 2.5rem 1rem 2rem;
        margin-top: 2rem;
        border-top: 1px solid {glass_border};
        color: {muted};
        font-size: 0.95rem;
    }}
    .site-footer a {{
        color: {accent2};
        text-decoration: none;
        margin: 0 0.65rem;
        font-weight: 600;
    }}
    .site-footer a:hover {{ text-decoration: underline; }}
    .hero-block {{
        text-align: center;
        padding: 1.5rem 0 0.5rem;
    }}
    .hero-block h1 {{
        font-size: clamp(1.6rem, 4vw, 2.75rem);
        font-weight: 800;
        margin-bottom: 0.75rem;
        background: linear-gradient(90deg, {accent}, {accent2});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .hero-block p {{ color: {muted}; font-size: 1.1rem; max-width: 640px; margin: 0 auto; line-height: 1.6; }}
    .stButton > button {{
        border-radius: 999px !important;
        border: none !important;
        padding: 0.75rem 2rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        background: linear-gradient(45deg, #11998e, #38ef7d) !important;
        color: white !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease !important;
        box-shadow: 0 6px 22px rgba(17, 153, 142, 0.35) !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 28px rgba(56, 239, 125, 0.45) !important;
    }}
    .stButton > button:active {{
        transform: translateY(0) scale(0.98) !important;
    }}
    div[data-baseweb="select"] > div {{
        border-radius: 14px !important;
        background: {glass_bg} !important;
        border: 1px solid {glass_border} !important;
    }}
    @media (max-width: 768px) {{
        .glass-nav {{ flex-direction: column; align-items: stretch; }}
        .glass-nav .links {{ justify-content: center; }}
        .hero-block h1 {{ font-size: 1.5rem; }}
        .action-row {{ flex-direction: column; align-items: stretch; }}
        .btn-trailer, .btn-stream {{ width: 100%; }}
    }}
    </style>
    """


if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

# --------------------- Person 4: FRONTEND / UI ---------------------
# Everything below is Streamlit UI + styling:
# - HTML/CSS injected via `st.markdown(..., unsafe_allow_html=True)`
# - Buttons/inputs control Streamlit session state (dummy streaming + recommendations)
with st.sidebar:
    st.markdown("### Settings")
    st.session_state.dark_mode = st.toggle(
        "Dark mode",
        value=st.session_state.dark_mode,
        help="Switch between dark and light theme",
    )
    st.caption("Tip: Use **About** and **Contact** in the sidebar or the top links.")

st.markdown(build_theme_css(st.session_state.dark_mode), unsafe_allow_html=True)
st.markdown('<div class="top-loader" aria-hidden="true"></div>', unsafe_allow_html=True)

st.markdown(
    """
    <nav class="glass-nav">
        <span class="brand">🎬 CineMind</span>
        <div class="links">
            <a href="/" target="_self">Home</a>
            <a href="/About" target="_self">About</a>
            <a href="/Contact" target="_self">Contact</a>
        </div>
    </nav>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-block">
        <h1>AI Driven Movie Recommendation with Streaming</h1>
        <p>Discover what to watch next with AI-powered picks, ratings, genres, trailers, and streaming links.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

movies, similarity = load_movie_data()
if movies is None or similarity is None:
    st.stop()

movie_meta = load_movie_meta()
movies_list = list(movies["title"].values)

st.markdown(
    '<div class="search-shell"><h3>Search & pick a movie</h3></div>',
    unsafe_allow_html=True,
)
search_q = st.text_input(
    "Search movies",
    placeholder="Type to filter titles…",
    label_visibility="collapsed",
)
q = (search_q or "").strip().lower()
if q:
    filtered_titles = [t for t in movies_list if q in str(t).lower()]
    if not filtered_titles:
        st.warning("No titles match that search — showing the full list below.")
        filtered_titles = movies_list
else:
    filtered_titles = movies_list

selected_movie = st.selectbox(
    "Select a movie",
    filtered_titles,
    label_visibility="collapsed",
)

platform_choices = [
    "Auto (Search all platforms)",
    "Netflix",
    "Amazon Prime Video",
    "Disney+ Hotstar",
    "JioCinema",
    "YouTube",
    "Other / Any platform",
]
selected_platform = st.selectbox("Preferred streaming platform", platform_choices)


# --------------------- Person 3: RECOMMENDER BACKEND ---------------------
# Core logic:
# - `recommend()` uses cosine-similarity pickled from `main.py` to find similar movies.
# - `trailer_search_url()` builds a YouTube search link for trailers.
# - `build_streaming_link()` builds a Google search link for streaming availability.
# Note: Actual streaming is mocked with a dummy local video (`st.video()`), not real playback.
def get_movie_platform(movie_row):
    possible_cols = ["platform", "platforms", "streaming_platform", "streaming_platforms"]
    for col in possible_cols:
        if col in movie_row.index:
            value = str(movie_row[col]).strip()
            if value and value.lower() not in ["nan", "none", "unknown"]:
                return value
    return "Unknown"


def build_streaming_link(movie_title, platform_preference):
    base_url = "https://www.google.com/search?q="
    query = f"{movie_title} full movie"
    if platform_preference and platform_preference != "Auto (Search all platforms)":
        query += f" watch on {platform_preference}"
    encoded_query = urllib.parse.quote_plus(query)
    return base_url + encoded_query


def recommend(movie):
    try:
        index = movies[movies["title"] == movie].index[0]
        distance = sorted(
            list(enumerate(similarity[index])),
            reverse=True,
            key=lambda vector: vector[1],
        )
        recommend_movie = []
        recommend_posters = []
        similarity_scores = []
        recommend_platforms = []
        recommend_ids = []

        for i in distance[1:6]:
            movie_row = movies.iloc[i[0]]
            movie_id = movie_row.id
            movie_title = movie_row.title

            recommend_movie.append(movie_title)
            poster_path = create_sample_poster(movie_title, movie_id)
            recommend_posters.append(poster_path)
            similarity_scores.append(round(i[1] * 100, 1))
            recommend_platforms.append(get_movie_platform(movie_row))
            recommend_ids.append(int(movie_id))

        return (
            recommend_movie,
            recommend_posters,
            similarity_scores,
            recommend_platforms,
            recommend_ids,
        )
    except Exception as e:
        st.error(f"Error generating recommendations: {str(e)}")
        return [], [], [], [], []

if "active_stream_movie" not in st.session_state:
    st.session_state.active_stream_movie = None

if selected_movie:
    selected_match = movies[movies["title"] == selected_movie]
    if not selected_match.empty:
        selected_id = int(selected_match.iloc[0].id)
        selected_poster = create_sample_poster(selected_movie, selected_id)
        try:
            with open(selected_poster, "rb") as f:
                selected_b64 = poster_b64(f.read())
        except Exception:
            selected_b64 = ""
        st.markdown(
            f"""
            <div class="selected-preview">
                <img src="data:image/png;base64,{html_module.escape(selected_b64)}" alt="{html_module.escape(selected_movie)}" width="82" style="border-radius:12px; box-shadow: 0 6px 20px rgba(0,0,0,0.25);" />
                <div>
                    <p class="selected-title">Selected: {html_module.escape(selected_movie)}</p>
                    <p class="selected-sub">Showing a generated placeholder poster.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# --------------------- Person 4: FRONTEND / UI (Workflow) ---------------------
# 1) Dropdown/selectbox se movie + platform select hota hai.
# 2) "Get Recommendations" dabate hi `recommend()` call hota hai aur cards data `st.session_state` mein store hota hai.
# 3) "Stream" button dabate hi `st.session_state.active_stream_movie` set hota hai, aur top par dummy video player render hota hai.
# 4) Posters `create_sample_poster()` se local base64 mein convert karke UI mein embed hote hain.

# Persistent state logic to handle dropdown selections and inputs
if "last_selected_movie" not in st.session_state:
    st.session_state.last_selected_movie = selected_movie
if "last_selected_platform" not in st.session_state:
    st.session_state.last_selected_platform = selected_platform

if (selected_movie != st.session_state.last_selected_movie) or (selected_platform != st.session_state.last_selected_platform):
    # Selection changed, reset recommendations and active streaming
    st.session_state.recommendations = None
    st.session_state.active_stream_movie = None
    st.session_state.last_selected_movie = selected_movie
    st.session_state.last_selected_platform = selected_platform

if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🎯 Get Recommendations", key="recommend_btn", use_container_width=True):
        with st.spinner("🎬 Finding perfect movies for you…"):
            (
                movie_names,
                movie_posters,
                similarity_scores,
                movie_platforms,
                movie_ids,
            ) = recommend(selected_movie)
            
            # Store in session state for persistence
            recs = []
            for name, poster, score, platform, mid in zip(movie_names, movie_posters, similarity_scores, movie_platforms, movie_ids):
                recs.append({
                    "name": name,
                    "poster": poster,
                    "score": score,
                    "platform": platform,
                    "id": mid
                })
            st.session_state.recommendations = recs
            st.session_state.active_stream_movie = None

# CineMind Theatre widescreen video streaming player (Renders at the top if streaming is active)
if st.session_state.active_stream_movie:
    active_movie = st.session_state.active_stream_movie
    muted = "#999" if st.session_state.dark_mode else "#666"
    st.markdown(
        f"""
        <div class="movie-card-glass" style="margin: 2rem 0; padding: 2rem; border: 2px solid rgba(56, 239, 125, 0.45); border-radius: 24px; box-shadow: 0 15px 35px rgba(56, 239, 125, 0.15);">
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
                <div>
                    <h3 style="margin: 0; color: #38ef7d; font-size: 1.6rem; font-weight: 800; letter-spacing: 0.02em; display: flex; align-items: center; gap: 0.5rem;">
                        <span>📺</span> CineMind Theatre
                    </h3>
                    <p style="margin: 0.35rem 0 0 0; color: {muted}; font-size: 1rem;">
                        Now streaming: <strong style="color: #7ee8fa;">{html_module.escape(active_movie)}</strong>
                    </p>
                </div>
                <div class="genre-badge" style="background: rgba(56, 239, 125, 0.15); color: #38ef7d; border: 1px solid rgba(56, 239, 125, 0.45); padding: 0.45rem 1rem; font-size: 0.8rem; letter-spacing: 0.08em; font-weight: 700;">
                    🟢 LIVE MOCK STREAM
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.video(DUMMY_STREAM_URL)
    
    st.markdown(
        """
            <div class="streaming-note" style="margin-top: 1rem; margin-bottom: 1.5rem;">
                🍿 Grab your popcorn! You are watching a high-fidelity test video simulating active media streaming.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    col_stop_l, col_stop_m, col_stop_r = st.columns([2, 1, 2])
    with col_stop_m:
        if st.button("✕ Close Stream", key="stop_stream_btn", use_container_width=True):
            st.session_state.active_stream_movie = None
            st.rerun()

# Render recommendations in a grid layout (3 columns) if they exist
if st.session_state.recommendations:
    st.markdown(
        "<h3 style='text-align: center; margin-top: 2rem; margin-bottom: 2rem;'>Your Personalized Movie Recommendations</h3>",
        unsafe_allow_html=True,
    )
    
    recs = st.session_state.recommendations
    chunk_size = 3
    for i in range(0, len(recs), chunk_size):
        row_items = recs[i : i + chunk_size]
        cols = st.columns(chunk_size)  # Keep 3 columns to maintain equal widths
        for col_idx, item in enumerate(row_items):
            with cols[col_idx]:
                name = item["name"]
                poster = item["poster"]
                score = item["score"]
                platform_info = item["platform"]
                mid = item["id"]
                
                try:
                    meta = movie_meta.get(mid, {})
                    genre_str = meta.get("genre", "")
                    vote_avg = meta.get("vote_average", 0.0)
                    stars_html = rating_stars_html(vote_avg)
                    genres_html = genre_badges_html(genre_str)
                    t_url = trailer_search_url(name)
                    stream_url = build_streaming_link(name, selected_platform)
                    
                    st.markdown(
                        f"""
                        <div class="movie-card-glass" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 1.5rem;">
                            <div>
                                <div class="movie-title" style="min-height: 70px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
                                    {i + col_idx + 1}. {html_module.escape(name)}
                                </div>
                                {genres_html}
                                {stars_html}
                        """,
                        unsafe_allow_html=True,
                    )
                    
                    if poster and os.path.exists(poster):
                        with open(poster, "rb") as f:
                            poster_bytes = f.read()
                        b64 = poster_b64(poster_bytes)
                        st.markdown(
                            f'<div class="poster-frame" style="aspect-ratio: 2/3; overflow: hidden; border-radius: 12px;">'
                            f'<img src="data:image/png;base64,{b64}" alt="{html_module.escape(name)}" '
                            f'style="width: 100%; height: 100%; object-fit: cover;" /></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error(f"Poster not found for {name}")
                        
                    st.markdown(
                        f"""
                                <p class="match-score">Match Score: {score}%</p>
                            </div>
                            <div>
                        """,
                        unsafe_allow_html=True,
                    )
                    
                    if platform_info != "Unknown":
                        st.markdown(
                            f"<p style='text-align: center; opacity: 0.9; margin-top: 0.35rem; font-size: 0.9rem;'>Streaming on: <strong>{html_module.escape(platform_info)}</strong></p>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            "<p style='text-align: center; opacity: 0.75; margin-top: 0.35rem; font-size: 0.9rem;'>Platform not specified — search will find options.</p>",
                            unsafe_allow_html=True,
                        )
                        
                    st.markdown(
                        f"""
                                <div class="action-row" style="margin-top: 0.5rem; margin-bottom: 0.75rem;">
                                    <a class="btn-trailer" href="{t_url}" target="_blank" rel="noopener">▶ Trailer</a>
                                    <a class="btn-stream" href="{html_module.escape(stream_url)}" target="_blank" rel="noopener">🔎 Find</a>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    
                    stream_key = f"stream_btn_{i + col_idx + 1}_{mid}"
                    if st.button(
                        f"📺 Stream: {name}",
                        key=stream_key,
                        use_container_width=True,
                    ):
                        st.session_state.active_stream_movie = name
                        st.rerun()
                except Exception as e:
                    st.error(f"Error displaying poster for {name}: {str(e)}")


st.markdown(
    """
    <footer class="site-footer">
        <div>
            <a href="/">Home</a>
            <a href="/About">About</a>
            <a href="/Contact">Contact</a>
        </div>
        <p style="margin-top: 0.75rem;">Built with Streamlit, HTML &amp; CSS · Posters &amp; UI are locally styled</p>
    </footer>
    """,
    unsafe_allow_html=True,
)
