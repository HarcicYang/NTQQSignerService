#!/usr/bin/env python3

import binascii
import json
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn
from contextlib import asynccontextmanager

try:
    # noinspection PyUnresolvedReferences
    import cSigner

    C_EXTENSION_AVAILABLE = True
    print("✓ C extension loaded successfully")
except ImportError as e:
    print(f"✗ Failed to load C extension: {e}")
    print("Please compile the C extension first: python setup.py build_ext --inplace")
    C_EXTENSION_AVAILABLE = False
    import sys

    sys.exit(1)

try:
    with open("./signer.json", "r") as f:
        CONFIG = json.loads(f.read())
        CONFIG["offset"] = eval(CONFIG["offset"])
except FileNotFoundError:
    print("✗ Configuration file signer.json not found, trying to create default configuration...")
    with open("./signer.json", "w") as f:
        cfg = {
            "host": "127.0.0.1",
            "port": 8080,
            "libs": ["libgnutls.so.30", "./libsymbols.so"],
            "offset": ""
        }
        f.write(json.dumps(cfg, indent=2))
    print(
        "✓ Default configuration file created. Please set the correct 'offset' value in signer.json and restart the service.")
    sys.exit(1)


class SignRequest(BaseModel):
    cmd: str = Field(..., description="cmd")
    src: str = Field(..., description="src")
    seq: int = Field(..., description="seq")


class ValueResponse(BaseModel):
    token: str = Field(..., description="token")
    extra: str = Field(..., description="extra")
    sign: str = Field(..., description="sign")


class SignResponse(BaseModel):
    value: ValueResponse


class ErrorResponse(BaseModel):
    error: str = Field(..., description="err")


class OffsetSignService:
    def __init__(self):
        self.initialized = False

    def initialize(self) -> bool:
        try:
            cSigner.set_libs(CONFIG['libs'])
            cSigner.set_offset(CONFIG['offset'])
            cSigner.load_module()

            self.initialized = True
            return True

        except Exception as e:
            print(f"✗ Failed to initialize sign service: {e}")
            return False

    def sign(self, cmd: str, src_hex: str, seq: int) -> List[bytes]:
        if not self.initialized:
            raise RuntimeError("Service not initialized")
        try:
            src_bytes = binascii.unhexlify(src_hex.upper())
        except Exception as e:
            raise ValueError(f"Invalid hex data: {e}")

        token, extra, sign_data = cSigner.sign(cmd, src_bytes, seq)

        return [token, extra, sign_data]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not C_EXTENSION_AVAILABLE:
        raise RuntimeError("C extension not available")

    print("Initializing Sign Service...")

    if not sign_service.initialize():
        raise RuntimeError("Failed to initialize sign service")

    print(f"✓ Service initialized successfully on {CONFIG['host']}:{CONFIG['port']}")

    yield

    if C_EXTENSION_AVAILABLE:
        try:
            cSigner.unload_module()
            print("✓ Sign module unloaded")
        except Exception as e:
            print(f"✗ Error unloading sign module: {e}")


app = FastAPI(
    title="Sign Service",
    description="Sign Service",
    version="1.0.0",
    lifespan=lifespan
)

sign_service = OffsetSignService()


@app.post(
    "/sign",
    response_model=SignResponse,
    responses={
        400: {"model": ErrorResponse, "description": "ValueError"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="sign",
    description="sign"
)
async def sign_service_endpoint(request: SignRequest) -> SignResponse:
    print(f"Signing for: Request({request})")
    try:
        token, extra, sign_data = sign_service.sign(request.cmd, request.src, request.seq)
        response = SignResponse(
            value=ValueResponse(
                token=binascii.hexlify(token).decode().upper(),
                extra=binascii.hexlify(extra).decode().upper(),
                sign=binascii.hexlify(sign_data).decode().upper()
            )
        )
        print("Done: ", response.value)

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request parameters: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign service error: {str(e)}"
        )

@app.get("/sign/appinfo")
def appinfo():
    with open("./appinfo.json") as f_:
        return json.loads(f_.read())


def main():
    if not C_EXTENSION_AVAILABLE:
        print("✗ C extension not available. Please compile it first.")
        return

    print(f"Starting Sign Service on {CONFIG['host']}:{CONFIG['port']}")
    uvicorn.run(
        app,
        host=CONFIG['host'],
        port=CONFIG['port'],
        log_level="info"
    )


if __name__ == "__main__":
    main()
