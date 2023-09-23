FROM python:latest

# RUN apt-get update -y && \
#     apt-get install build-essential cmake pkg-config -y

# RUN pip install dlib==19.9.0
LABEL version="For FastApi Server"

EXPOSE 8000

WORKDIR /usr/app

COPY ./requirements.txt ./
RUN pip install --upgrade pip

# RUN pip install --no-cache-dir -r requirements.txt

RUN pip install fastapi
RUN pip install sqlmodel
RUN pip install passlib
RUN pip install PrintDebug
RUN pip install pydantic
RUN pip install PyJWT
RUN pip install requests
RUN pip install SQLAlchemy<2
RUN pip install starlette
RUN pip install uvicorn[standard]
RUN pip install Jinja2
RUN pip install python-multipart
RUN pip install sse_starlette
RUN pip install aiosqlite
RUN pip install Pillow
# RUN pip install fastapi

# COPY ./FAST_API_ServerBase_pk /usr/src/app

CMD [ "python3", "./start_server.py" ]
