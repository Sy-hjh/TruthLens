import bootstrap
import uvicorn

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="亲安本机服务；手机访问需同一局域网及显式指定host"
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8010)
    a = p.parse_args()
    uvicorn.run("backend.app:app", host=a.host, port=a.port)
