import json
import time
from websocket import create_connection

def tail_loki_logs_ws():
    loki_url = "ws://localhost:3100/loki/api/v1/tail"
    params = {
        "query": '{k8s_namespace_name="default"}',
        "limit": 10,
    }
    query_string = "&".join(f"{key}={value}" for key, value in params.items())
    loki_url += f"?{query_string}"

    ws = create_connection(loki_url)
    print("Connected to Loki WebSocket")

    try:
        while True:
            message = ws.recv()
            payload = json.loads(message)
            for stream in payload['streams']:
                if stream['values'][0][1] is not None:
                    print(stream['values'][0][1])
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ws.close()

# Run the WebSocket log tailing function
if __name__ == "__main__":
    tail_loki_logs_ws()
