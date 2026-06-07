from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI(title="API Gateway")

SERVICES = {
    "identity": "http://localhost:8001",
    "schedule": "http://localhost:8002",
    "reservations": "http://localhost:8003",
    "availability": "http://localhost:8004",
}

async def forward_request(url: str, request: Request):
    async with httpx.AsyncClient() as client:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None) # Remove host header to avoid routing issues
        
        try:
            req = client.build_request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            response = await client.send(req)
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Bad Gateway: {exc}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_auth(path: str, request: Request):
    return await forward_request(f"{SERVICES['identity']}/auth/{path}", request)

@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_users(path: str, request: Request):
    return await forward_request(f"{SERVICES['identity']}/users/{path}", request)

@app.api_route("/specialists/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_specialists(path: str, request: Request):
    return await forward_request(f"{SERVICES['schedule']}/specialists/{path}", request)

@app.api_route("/reservations", methods=["GET", "POST"])
async def route_reservations(request: Request):
    return await forward_request(f"{SERVICES['reservations']}/reservations", request)
    
@app.api_route("/reservations/{path:path}", methods=["GET", "PUT", "DELETE"])
async def route_reservations_path(path: str, request: Request):
    return await forward_request(f"{SERVICES['reservations']}/reservations/{path}", request)

@app.api_route("/available-appointments", methods=["GET"])
async def route_availability(request: Request):
    return await forward_request(f"{SERVICES['availability']}/available-appointments", request)
