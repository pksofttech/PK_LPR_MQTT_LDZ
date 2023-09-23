import uvicorn

print("*" * 150)
print("\n\nStarting Server...")
if __name__ == "__main__":
    _host = "0.0.0.0"
    _port = 8000
    print(f"Start App Service at IP>>{_host}:{_port}")
    uvicorn.run(
        "app.main:app",
        # workers=2,
        host=_host,
        port=_port,
        reload_includes=["*.html"],
        reload_dirs=[
            "./app",
            "./templates",
        ],
        reload=True,
        # debug=True,
    )
