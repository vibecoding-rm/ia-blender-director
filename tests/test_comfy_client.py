import json
import urllib.request
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ai_blender_director.comfy.client import ComfyClient


class TestComfyClient(TestCase):
    def setUp(self):
        self.client = ComfyClient("http://localhost:8188")
        self.test_dir = Path("test_comfy_outputs")
        self.test_dir.mkdir(exist_ok=True)
        self.dummy_image = self.test_dir / "dummy.png"
        self.dummy_image.write_bytes(b"fake image content")

    def tearDown(self):
        if self.dummy_image.exists():
            self.dummy_image.unlink()
        try:
            self.test_dir.rmdir()
        except OSError:
            pass

    @patch("urllib.request.urlopen")
    def test_upload_image(self, mock_urlopen):
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"name": "dummy.png"}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = self.client.upload_image(self.dummy_image)
        
        self.assertEqual(result, {"name": "dummy.png"})
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://localhost:8188/upload/image")
        self.assertTrue(req.has_header("Content-type"))
        self.assertIn("multipart/form-data", req.get_header("Content-type"))

    @patch("urllib.request.urlopen")
    def test_queue_prompt(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"prompt_id": "12345"}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        workflow = {"1": {"class_type": "LoadImage"}}
        result = self.client.queue_prompt(workflow)
        
        self.assertEqual(result, {"prompt_id": "12345"})
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://localhost:8188/prompt")
        self.assertEqual(json.loads(req.data.decode("utf-8")), {"prompt": workflow})

    @patch("urllib.request.urlopen")
    def test_wait_for_completion(self, mock_urlopen):
        mock_response = MagicMock()
        # Mock /history to return the prompt id
        mock_response.read.return_value = json.dumps({
            "12345": {"outputs": {"9": {"images": [{"filename": "out.png"}]}}}
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = self.client.wait_for_completion("12345", timeout_sec=1)
        self.assertIn("outputs", result)
