"""核心模块"""
from .fetcher import BaseFetcher
from .registry import ProviderRegistry

__all__ = ["BaseFetcher", "ProviderRegistry"]
