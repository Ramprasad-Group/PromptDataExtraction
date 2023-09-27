from backend import postgres, sett
import pytest
import pylogg

sett.load_settings()
postgres.load_settings()
pylogg.setLevel(pylogg.Level.DEBUG)
