"""Common registry — shared registration utilities for plugins.

This module re-exports registry functions from all plugin types, providing a
unified entry point for plugin discovery.
"""

import importlib


def get_language_registry():
    """Get the LanguageRegistry class."""
    mod = importlib.import_module("plugins.src_01_source.backend")
    return mod.LanguageRegistry


def get_build_registry():
    """Get the BuildRegistry class."""
    mod = importlib.import_module("plugins.cfg_03_config.build")
    return mod.BuildRegistry


def get_config_registry():
    """Get the ConfigRegistry class."""
    mod = importlib.import_module("plugins.cfg_03_config.app_config")
    return mod.ConfigRegistry


def get_template_registry():
    """Get the TemplateRegistry class."""
    mod = importlib.import_module("plugins.tpl_02_template.web_pages")
    return mod.TemplateRegistry
