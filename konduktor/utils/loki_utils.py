import colorama
import json
import time
import urllib.parse
from websocket import create_connection

from konduktor import logging

logger = logging.get_logger(__name__)

def tail_loki_logs_ws(job_name: str, worker_id: int = 0, num_logs: int = 100):
    loki_url = "ws://localhost:3100/loki/api/v1/tail"
    params = {
        "query": urllib.parse.quote(f'{{k8s_namespace_name="default"}} | jobset_sigs_k8s_io_jobset_name = `{job_name}` | batch_kubernetes_io_job_completion_index = `{worker_id}`'),
        "limit": num_logs,
        "start": 1735746377, # this is Jan 1, 2025,
    }
    
    query_string = "&".join(f"{key}={value}" for key, value in params.items())
    loki_url += f"?{query_string}"

    ws = create_connection(loki_url)
    logger.info(f"{colorama.Fore.YELLOW}Tailing logs from Loki. Press Ctrl+C to stop.{colorama.Style.RESET_ALL}")

    try:
        while True:
            message = ws.recv()
            payload = json.loads(message)
            if len(payload['streams']) == 0:
                logger.info(f"{colorama.Fore.YELLOW}No logs found for {job_name}{colorama.Style.RESET_ALL}")
                break
            for stream in payload['streams']:
                if stream['values'][0][1] is not None:
                    print(f"{colorama.Fore.CYAN}{colorama.Style.BRIGHT}(job_name={job_name} worker_id={worker_id}) {colorama.Style.RESET_ALL}{stream['values'][0][1]}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ws.close()

# Run the WebSocket log tailing function
if __name__ == "__main__":
    tail_loki_logs_ws("tune-2266", 0)
