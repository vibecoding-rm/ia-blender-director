import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class ComfyClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base_url = base_url.rstrip("/")

    def upload_image(self, file_path: Path, subfolder: str = "", overwrite: bool = True) -> dict:
        """Upload an image to ComfyUI. Returns the JSON response from the server."""
        if not file_path.exists():
            raise FileNotFoundError(f"Image not found: {file_path}")

        url = f"{self.base_url}/upload/image"
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        filename = file_path.name
        mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        
        body = []
        # Add overwrite field
        body.append(f"--{boundary}\r\n")
        body.append(f'Content-Disposition: form-data; name="overwrite"\r\n\r\n')
        body.append(f"{str(overwrite).lower()}\r\n")
        
        # Add subfolder field
        if subfolder:
            body.append(f"--{boundary}\r\n")
            body.append(f'Content-Disposition: form-data; name="subfolder"\r\n\r\n')
            body.append(f"{subfolder}\r\n")
            
        # Add image data
        body.append(f"--{boundary}\r\n")
        body.append(f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n')
        body.append(f"Content-Type: {mimetype}\r\n\r\n")
        
        body_bytes = "".join(body).encode("utf-8")
        with open(file_path, "rb") as f:
            body_bytes += f.read()
            
        body_bytes += f"\r\n--{boundary}--\r\n".encode("utf-8")
        
        req = urllib.request.Request(url, data=body_bytes)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(body_bytes)))
        
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))

    def queue_prompt(self, workflow: dict) -> dict:
        """Queue a prompt (workflow) in ComfyUI."""
        url = f"{self.base_url}/prompt"
        data = json.dumps({"prompt": workflow}).encode("utf-8")
        
        req = urllib.request.Request(url, data=data)
        req.add_header("Content-Type", "application/json")
        req.add_header("Content-Length", str(len(data)))
        
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_history(self, prompt_id: str) -> dict:
        """Get the history (result) of a specific prompt ID."""
        url = f"{self.base_url}/history/{prompt_id}"
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def wait_for_completion(self, prompt_id: str, timeout_sec: int = 300, poll_interval: int = 2) -> dict:
        """Wait until a prompt is completed and return its history data."""
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout_sec} seconds")

    def download_image(self, filename: str, subfolder: str, type: str, output_path: Path) -> None:
        """Download a generated image from ComfyUI."""
        params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": type})
        url = f"{self.base_url}/view?{params}"
        
        with urllib.request.urlopen(url) as response:
            with open(output_path, "wb") as f:
                f.write(response.read())

    def process_and_download(self, prompt_id: str, output_dir: Path) -> list[Path]:
        """Wait for completion and download all generated images."""
        history = self.wait_for_completion(prompt_id)
        
        outputs = history.get("outputs", {})
        downloaded_files = []
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for image_info in node_output["images"]:
                    filename = image_info.get("filename")
                    subfolder = image_info.get("subfolder", "")
                    img_type = image_info.get("type", "output")
                    
                    if filename:
                        out_path = output_dir / filename
                        self.download_image(filename, subfolder, img_type, out_path)
                        downloaded_files.append(out_path)
                        
        return downloaded_files
