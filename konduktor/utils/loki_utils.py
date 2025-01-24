import asyncio
import colorama
import json
import kr8s
import time
import urllib.parse
import websocket

from konduktor import logging

logger = logging.get_logger(__name__)

# TODO(asaiacai): make this configurable via ~/.konduktor/config.yaml
LOG_TAIL_TIMEOUT = 60 # seconds

async def tail_loki_logs_ws(job_name: str, worker_id: int = 0, num_logs: int = 100):
    loki_url = "ws://localhost:3100/loki/api/v1/tail"
    params = {
        "query": urllib.parse.quote(f'{{k8s_namespace_name="default"}} | jobset_sigs_k8s_io_jobset_name = `{job_name}` | batch_kubernetes_io_job_completion_index = `{worker_id}`'),
        "limit": num_logs,
        "start": 1735746377, # this is Jan 1, 2025,
    }
    
    query_string = "&".join(f"{key}={value}" for key, value in params.items())
    loki_url += f"?{query_string}"

    loki_svc = kr8s.objects.Service.get("loki", namespace="loki")
    with kr8s.portforward.PortForward(loki_svc, 3100) as port:
        logger.info(f"{colorama.Fore.YELLOW}Tailing logs from Loki. Forwarding to port 3100. Press Ctrl+C to stop.{colorama.Style.RESET_ALL}")
        ws = websocket.create_connection(loki_url)

        try:
            while True:
                # Set timeout to 10 seconds
                message = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, ws.recv),
                    timeout=1,
                )
                payload = json.loads(message)
                for stream in payload['streams']:
                    if stream['values'][0][1] is not None:
                        print(f"{colorama.Fore.CYAN}{colorama.Style.BRIGHT}(job_name={job_name} worker_id={worker_id}) {colorama.Style.RESET_ALL}{stream['values'][0][1]}")
        except KeyboardInterrupt:
            print("Exiting...")
        except asyncio.TimeoutError:
            logger.info(f"Log tail timed out after {LOG_TAIL_TIMEOUT} seconds. Either your job is hanging or there is no job with id {colorama.Fore.CYAN}{colorama.Style.BRIGHT}{job_name}{colorama.Style.RESET_ALL} that produced logs. Double check which jobs were submitted with {colorama.Style.BRIGHT}`konduktor status`{colorama.Style.RESET_ALL}")
        finally:
            ws.close()

# Run the WebSocket log tailing function
if __name__ == "__main__":
    asyncio.run(tail_loki_logs_ws("blue-2266", 0))
