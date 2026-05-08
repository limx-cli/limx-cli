import json
import socket
import ssl
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


class SignalingError(RuntimeError):
    """Base error for signaling client failures."""


class SignalingTimeout(SignalingError):
    """Raised when a WebSocket request times out."""


@dataclass
class RobotLockIdentity:
    user_name: str = "agent"
    user_id: str = "agent"
    device_id: str = "limx-agent-harness"

    def as_request_data(self) -> Dict[str, str]:
        return {
            "user_name": self.user_name,
            "user_id": self.user_id,
            "device_id": self.device_id,
        }


class SignalingClient:
    """Small RPC client for the signaling request_*/response_* WebSocket protocol."""

    def __init__(
        self,
        host: str,
        port: int = 5000,
        secure: bool = False,
        connect_timeout: float = 10.0,
        default_timeout: float = 30.0,
        app_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.secure = secure
        self.connect_timeout = connect_timeout
        self.default_timeout = default_timeout
        self.app_factory = app_factory

        self.accid: Optional[str] = None
        self._app: Any = None
        self._thread: Optional[threading.Thread] = None
        self._open_event = threading.Event()
        self._accid_event = threading.Event()
        self._pending: Dict[str, Tuple[threading.Event, Dict[str, Any]]] = {}
        self._pending_lock = threading.Lock()
        self._closed = False

    @property
    def url(self) -> str:
        scheme = "wss" if self.secure else "ws"
        return f"{scheme}://{self.host}:{self.port}"

    def connect(self, wait_accid: bool = True) -> "SignalingClient":
        if self._app is not None:
            return self

        factory = self.app_factory or self._load_websocket_app()
        self._app = factory(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._app.sock_opt = [
            (socket.SOL_SOCKET, socket.SO_SNDBUF, 8 * 1024 * 1024),
            (socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024),
        ]

        run_kwargs: Dict[str, Any] = {}
        if self.secure:
            run_kwargs["sslopt"] = {"cert_reqs": ssl.CERT_NONE}

        self._thread = threading.Thread(
            target=lambda: self._app.run_forever(**run_kwargs),
            name="limx-signaling-ws",
            daemon=True,
        )
        self._thread.start()

        if not self._open_event.wait(self.connect_timeout):
            raise SignalingTimeout(f"WebSocket connection timeout: {self.url}")
        if wait_accid and not self._accid_event.wait(self.connect_timeout):
            raise SignalingTimeout("ACCID not received from signaling server")
        return self

    def close(self) -> None:
        self._closed = True
        if self._app is not None:
            self._app.close()
        self._app = None

    def request(
        self,
        title: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not title.startswith("request_"):
            title = f"request_{title}"
        if self._app is None:
            self.connect()

        guid = str(uuid.uuid4())
        event = threading.Event()
        holder: Dict[str, Any] = {}
        with self._pending_lock:
            self._pending[guid] = (event, holder)

        msg = {
            "accid": self.accid or "",
            "title": title,
            "timestamp": int(time.time() * 1000),
            "guid": guid,
            "data": data or {},
        }
        self._app.send(json.dumps(msg, ensure_ascii=False))

        wait_timeout = self.default_timeout if timeout is None else timeout
        if not event.wait(wait_timeout):
            with self._pending_lock:
                self._pending.pop(guid, None)
            raise SignalingTimeout(f"{title} timed out after {wait_timeout}s")

        with self._pending_lock:
            self._pending.pop(guid, None)
        return holder.get("data", {})

    def lock(self, identity: RobotLockIdentity) -> Dict[str, Any]:
        return self.request("request_lock_robot_control", identity.as_request_data())

    def unlock(self) -> Dict[str, Any]:
        return self.request("request_unlock_robot_control", {})

    def locker_info(self) -> Dict[str, Any]:
        return self.request("request_get_locker_info", {})

    def _on_open(self, _ws: Any) -> None:
        self._open_event.set()

    def _on_error(self, _ws: Any, error: Any) -> None:
        if self._closed:
            return
        for event, holder in self._pending.values():
            holder["data"] = {"result": "fail_websocket_error", "message": str(error)}
            event.set()

    def _on_close(self, _ws: Any, _code: Any, _message: Any) -> None:
        self._closed = True

    def _on_message(self, _ws: Any, message: str) -> None:
        try:
            root = json.loads(message)
        except json.JSONDecodeError:
            return

        accid = root.get("accid")
        if accid:
            self.accid = accid
            self._accid_event.set()

        title = root.get("title", "")
        if not title.startswith("response_"):
            return

        guid = root.get("guid", "")
        with self._pending_lock:
            pending = self._pending.get(guid)
        if pending:
            event, holder = pending
            holder["data"] = root.get("data", {})
            holder["root"] = root
            event.set()

    @staticmethod
    def _load_websocket_app() -> Callable[..., Any]:
        try:
            from websocket import WebSocketApp
        except ImportError as exc:
            raise SignalingError(
                "Missing dependency: install with `pip install websocket-client`"
            ) from exc
        return WebSocketApp
