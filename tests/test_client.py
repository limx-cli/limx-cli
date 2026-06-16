import importlib
import json
import unittest

client_module = importlib.import_module("limx-cli.client")
RobotLockIdentity = client_module.RobotLockIdentity
SignalingClient = client_module.SignalingClient


class FakeWebSocketApp:
    def __init__(self, url, on_open=None, on_message=None, on_error=None, on_close=None):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.sent = []
        self.closed = False
        self.sock_opt = []

    def run_forever(self, **_kwargs):
        if self.on_open:
            self.on_open(self)
        if self.on_message:
            self.on_message(self, json.dumps({"accid": "ROBOT001"}))

    def send(self, payload):
        self.sent.append(json.loads(payload))
        request = self.sent[-1]
        response = {
            "title": request["title"].replace("request_", "response_", 1),
            "guid": request["guid"],
            "timestamp": request["timestamp"],
            "data": {"result": "success", "echo": request["data"]},
        }
        self.on_message(self, json.dumps(response))

    def close(self):
        self.closed = True
        if self.on_close:
            self.on_close(self, 1000, "closed")


class SignalingClientTest(unittest.TestCase):
    def test_request_uses_accid_and_guid_response_matching(self):
        client = SignalingClient(
            host="127.0.0.1",
            connect_timeout=1,
            app_factory=FakeWebSocketApp,
        )

        client.connect()
        result = client.request("request_get_joint_state", {})

        self.assertEqual("ROBOT001", client.accid)
        self.assertEqual("success", result["result"])
        self.assertEqual({}, result["echo"])
        self.assertEqual("ROBOT001", client._app.sent[0]["accid"])

    def test_lock_payload_shape(self):
        identity = RobotLockIdentity(user_name="agent", user_id="u1", device_id="d1")

        self.assertEqual(
            {"user_name": "agent", "user_id": "u1", "device_id": "d1"},
            identity.as_request_data(),
        )


if __name__ == "__main__":
    unittest.main()
