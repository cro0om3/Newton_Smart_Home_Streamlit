"""
Settings Management for Newton Smart Home Application
Handles system configuration stored in data/settings.json
"""

import os
import json
from typing import Dict, Any


DEFAULT_SETTINGS = {
    "company_name": "Newton Smart Home",
    "default_prepared_by": "Sales Team",
    "default_approved_by": "Manager",
    "contact_email": "info@newtonsmarthome.com",
    "contact_phone": "+971 52 779 0975",
    "currency": "AED",
    "ui_product_image_width_px": 350,
    "ui_product_image_height_px": 195,
    "quote_product_image_width_cm": 3.49,
    "quote_product_image_height_cm": 1.5,
    "openai_api_key": "",
    "ui_accent": "none"
}


def ensure_settings_file():
    """Create settings.json if it doesn't exist with default values."""
    os.makedirs("data", exist_ok=True)
    path = "data/settings.json"
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2, ensure_ascii=False)


def load_settings() -> Dict[str, Any]:
    """
    Load settings from data/settings.json.
    Returns dict with all configuration values.
    """
    ensure_settings_file()
    try:
        with open("data/settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
        # Ensure all default keys exist
        for key, value in DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = value
        return settings
    except Exception as e:
        print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]):
    """
    Save settings to data/settings.json.
    """
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving settings: {e}")


def get_setting(key: str, default: Any = None) -> Any:
    """Get a specific setting value."""
    settings = load_settings()
    return settings.get(key, default)


def update_setting(key: str, value: Any):
    """Update a single setting."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
