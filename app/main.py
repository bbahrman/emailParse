import logfire
from fastapi import FastAPI

app = FastAPI()

logfire.configure()
logfire.instrument_fastapi(app)


# root
@app.get("/")
async def root():
    return {"message": "Hello World"}


# params
@app.get("/hello")
async def hello(name: str):
    return {"message": f"hello {name}"}


# path
@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
