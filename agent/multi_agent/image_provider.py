"""
Image Generation Provider Abstraction & Thematic Artwork Engine.
Supports real Google Imagen/Gemini when configured, with a deterministic
hybrid SVG/Vector background generation engine for exact, non-hallucinated layouts.
"""
from __future__ import annotations

import abc
import base64
import hashlib
import logging
from pathlib import Path
from typing import Optional

from config.settings import (
    ASSETS_DIR,
    GEMINI_API_KEY,
    IMAGE_GENERATION_API_KEY,
    IMAGE_GENERATION_MODEL,
    IMAGE_GENERATION_PROVIDER,
)

logger = logging.getLogger(__name__)


class ImageGenerationProvider(abc.ABC):
    """Abstract base class for visual asset generators."""

    @abc.abstractmethod
    def generate_menu_background(
        self,
        style: str,
        restaurant_name: str,
        cuisine: str,
        palette: list[str],
        output_path: Path,
    ) -> dict:
        """
        Generate a visual artwork background suitable for menu rendering.
        Returns a dictionary containing 'url', 'file_path', 'provider', and 'metadata'.
        """
        pass


class GoogleImagenProvider(ImageGenerationProvider):
    """Google Gemini / Imagen API visual generator."""

    def __init__(self, api_key: str, model_name: str = IMAGE_GENERATION_MODEL):
        self.api_key = api_key
        self.model_name = model_name

    def generate_menu_background(
        self,
        style: str,
        restaurant_name: str,
        cuisine: str,
        palette: list[str],
        output_path: Path,
    ) -> dict:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            prompt = (
                f"A high-end, elegant restaurant menu background design in {style} aesthetic for {restaurant_name} ({cuisine}). "
                f"Palette tones: {', '.join(palette)}. Luxurious subtle borders, textured parchment, organic watercolor elements. "
                "CLEAN BLANK CENTER with no words, no text, no letters, no typography, purely decorative margins and border filigree."
            )

            # Try imagen generation if available in SDK
            result = client.models.generate_images(
                model=self.model_name,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="3:4",
                ),
            )
            if result.generated_images:
                img_bytes = result.generated_images[0].image.image_bytes
                output_path.write_bytes(img_bytes)
                return {
                    "url": f"/api/assets/{output_path.name}",
                    "file_path": str(output_path),
                    "provider": "google_imagen",
                    "metadata": {"prompt": prompt, "model": self.model_name},
                }
        except Exception as exc:
            logger.warning("Google Imagen generation unavailable or failed: %s. Falling back to Thematic Vector Artwork.", exc)

        # Fallback to SVG engine
        fallback = ThematicSVGArtworkProvider()
        return fallback.generate_menu_background(style, restaurant_name, cuisine, palette, output_path)


class ThematicSVGArtworkProvider(ImageGenerationProvider):
    """
    Deterministic Thematic Vector Artwork Engine.
    Generates tailored, high-resolution aesthetic vector backgrounds
    customized to the restaurant's cuisine, style, and brand palette.
    """

    def generate_menu_background(
        self,
        style: str,
        restaurant_name: str,
        cuisine: str,
        palette: list[str],
        output_path: Path,
    ) -> dict:
        c_primary = palette[0] if len(palette) > 0 else "#183B32"
        c_bg = palette[1] if len(palette) > 1 else "#F7F5EF"
        c_accent = palette[2] if len(palette) > 2 else "#D97757"
        c_gold = palette[3] if len(palette) > 3 else "#D6A64F"

        style_lower = style.lower()

        if "traditional indian" in style_lower or "dhaba" in style_lower:
            # Regal Indian arches, paisley filigree, and mandala motifs
            svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1130" width="800" height="1130">
  <defs>
    <radialGradient id="bgGrad" cx="50%" cy="50%" r="75%">
      <stop offset="0%" stop-color="#FCFAF5"/>
      <stop offset="100%" stop-color="{c_bg}"/>
    </radialGradient>
    <pattern id="mandala" width="100" height="100" patternUnits="userSpaceOnUse">
      <circle cx="50" cy="50" r="35" fill="none" stroke="{c_gold}" stroke-width="0.8" stroke-dasharray="2,3" opacity="0.35"/>
      <path d="M50 15 L50 85 M15 50 L85 50 M25 25 L75 75 M25 75 L75 25" stroke="{c_primary}" stroke-width="0.5" opacity="0.15"/>
    </pattern>
  </defs>
  <rect width="800" height="1130" fill="url(#bgGrad)"/>
  <rect width="760" height="1090" x="20" y="20" fill="none" stroke="{c_primary}" stroke-width="2.5" rx="12"/>
  <rect width="744" height="1074" x="28" y="28" fill="none" stroke="{c_gold}" stroke-width="1.2" rx="8"/>
  <rect width="736" height="1066" x="32" y="32" fill="url(#mandala)" opacity="0.12"/>
  <!-- Decorative Indian Arch in Header -->
  <path d="M40 70 Q 200 70 300 45 Q 400 20 500 45 Q 600 70 760 70" fill="none" stroke="{c_gold}" stroke-width="2" opacity="0.7"/>
  <!-- Corner Ornaments -->
  <g fill="{c_accent}" opacity="0.65">
    <circle cx="45" cy="45" r="4"/><circle cx="755" cy="45" r="4"/><circle cx="45" cy="1085" r="4"/><circle cx="755" cy="1085" r="4"/>
  </g>
</svg>"""

        elif "cafe" in style_lower or "bakery" in style_lower:
            # Warm artisan craft paper texture, coffee botanical leaves
            svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1130" width="800" height="1130">
  <defs>
    <linearGradient id="warmGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FBF9F5"/>
      <stop offset="100%" stop-color="{c_bg}"/>
    </linearGradient>
  </defs>
  <rect width="800" height="1130" fill="url(#warmGrad)"/>
  <!-- Minimalist Coffee Branch & Botanical Accents -->
  <rect width="750" height="1080" x="25" y="25" fill="none" stroke="{c_primary}" stroke-width="1.5" stroke-dasharray="6,4" rx="6"/>
  <g stroke="{c_primary}" fill="none" stroke-width="1.2" opacity="0.25">
    <path d="M40 90 Q 70 60 120 70 T 180 65"/>
    <circle cx="70" cy="62" r="3" fill="{c_accent}"/>
    <circle cx="120" cy="70" r="3" fill="{c_accent}"/>
    <circle cx="160" cy="67" r="3" fill="{c_accent}"/>
  </g>
  <g stroke="{c_primary}" fill="none" stroke-width="1.2" opacity="0.25" transform="rotate(180 400 565)">
    <path d="M40 90 Q 70 60 120 70 T 180 65"/>
    <circle cx="70" cy="62" r="3" fill="{c_accent}"/>
    <circle cx="120" cy="70" r="3" fill="{c_accent}"/>
  </g>
</svg>"""

        elif "luxury" in style_lower or "black and gold" in style_lower:
            # Deep obsidian backdrop with refined gold geometric frames
            svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1130" width="800" height="1130">
  <rect width="800" height="1130" fill="#141816"/>
  <rect width="756" height="1086" x="22" y="22" fill="none" stroke="{c_gold}" stroke-width="1.8"/>
  <rect width="740" height="1070" x="30" y="30" fill="none" stroke="{c_gold}" stroke-width="0.7" opacity="0.5"/>
  <!-- Art Deco Corner Diamonds -->
  <polygon points="30,30 50,30 30,50" fill="{c_gold}" opacity="0.8"/>
  <polygon points="770,30 750,30 770,50" fill="{c_gold}" opacity="0.8"/>
  <polygon points="30,1100 50,1100 30,1080" fill="{c_gold}" opacity="0.8"/>
  <polygon points="770,1100 750,1100 770,1080" fill="{c_gold}" opacity="0.8"/>
</svg>"""

        else:
            # Modern Minimalist & Contemporary Fusion
            svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1130" width="800" height="1130">
  <defs>
    <linearGradient id="cleanGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="{c_bg}"/>
    </linearGradient>
  </defs>
  <rect width="800" height="1130" fill="url(#cleanGrad)"/>
  <rect width="750" height="1080" x="25" y="25" fill="none" stroke="{c_primary}" stroke-width="1.2" rx="4"/>
  <line x1="25" y1="120" x2="775" y2="120" stroke="{c_accent}" stroke-width="1" opacity="0.4"/>
  <line x1="25" y1="1025" x2="775" y2="1025" stroke="{c_gold}" stroke-width="1" opacity="0.4"/>
</svg>"""

        # Save SVG file
        svg_filename = output_path.with_suffix(".svg")
        svg_filename.write_text(svg_content, encoding="utf-8")

        return {
            "url": f"/api/assets/{svg_filename.name}",
            "file_path": str(svg_filename),
            "svg_content": svg_content,
            "provider": "thematic_vector_engine",
            "metadata": {"style": style, "restaurant": restaurant_name},
        }


def get_image_provider() -> ImageGenerationProvider:
    """Factory selecting the appropriate visual generation provider."""
    provider_type = IMAGE_GENERATION_PROVIDER.lower()
    api_key = IMAGE_GENERATION_API_KEY or GEMINI_API_KEY

    if provider_type in {"google", "imagen", "gemini", "auto"} and api_key:
        return GoogleImagenProvider(api_key=api_key)
    return ThematicSVGArtworkProvider()
