import os
from ..stdio import *
from passlib.context import CryptContext
from PIL import Image
from app.core import config

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return _pwd_context.hash(password)


def save_image_file(img, file_path, file_name):

    if not img:
        return None
    if not os.path.exists(file_path):
        os.makedirs(file_path)
        print("The new directory is created!")
    with img as img:
        if img.format == "PNG":
            print("convert ing to RBG")
            img.convert("RGB")
        img.thumbnail(config.IMAGE_MAX_SIZE)
        print(img)
        try:
            _path_save_file = f"{file_path}/{file_name}.jpg"
            img.save(_path_save_file, "PNG")
            return _path_save_file
        except Exception as e:
            print_error(e)
            return None
