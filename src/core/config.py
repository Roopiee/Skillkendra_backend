"""Configuration for verification system"""
import os


class Config:
    CSV_PATH = os.getenv("CSV_PATH", "data/trusted_sources.csv")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


config = Config()
