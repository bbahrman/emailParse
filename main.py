import logfire
from fastapi import FastAPI

app = FastAPI()

logfire.configure()
logfire.instrument_fastapi(app)


@app.get("/hello")
async def hello(name: str):
    return {"message": f"hello {name}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
