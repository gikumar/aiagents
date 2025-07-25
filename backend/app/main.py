from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",  # React dev server URL
    # add your production frontend URL here when deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # allow React frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI backend!"}
