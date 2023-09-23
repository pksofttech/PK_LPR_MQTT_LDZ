from logging import exception
import os
from ..stdio import *

# from dotenv import load_dotenv

# load_dotenv("./.env")

# ?--------------------INI Variable------------------------------#
"""Load configuration from .ini file."""

APP_TITLE = "PKS_LPR"
DIR_PATH = os.getcwd()
# Auth configs.
API_SECRET_KEY = "pksofttech@gmail.com"
API_ALGORITHM = "HS256"
API_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

app_configurations_allow_not_register_member = False
IMAGE_MAX_SIZE = (200, 200)
