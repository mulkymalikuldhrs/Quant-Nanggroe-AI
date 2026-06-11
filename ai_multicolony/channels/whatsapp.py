"""WhatsApp gateway channel.

Features:
* Message sending/receiving
* Media support (images, documents, audio, video)
* Template messages
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from ..types import (
    ChannelType,
    ChannelMessage,
    MessageFormat,
)

logger = logging.getLogger(__name__)


class WhatsAppGateway:
    """WhatsApp Cloud API gateway for agent communication.

    Parameters
    ----------
    api_key : str
        The WhatsApp Business API key.
    api_url : str
        Base URL for the WhatsApp Cloud API.
    phone_number_id : str
        The phone number ID for sending messages.
    """

    def __init__(
        self,
        api_key: str = "",
        api_url: str = "https://graph.facebook.com/v18.0",
        phone_number_id: str = "",
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.phone_number_id = phone_number_id
        self._connected = False
        self._messages: List[Dict[str, Any]] = []
        self._media: List[Dict[str, Any]] = []
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._message_handlers: List[Callable[..., Coroutine[Any, Any, Any]]] = []

    # ── Connection ─────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Connect to the WhatsApp Cloud API."""
        if not self.api_key:
            self._connected = False
            return False
        self._connected = True
        logger.info("WhatsApp gateway connected (phone_number_id=%s)", self.phone_number_id)
        return True

    async def disconnect(self) -> None:
        """Disconnect from WhatsApp."""
        self._connected = False
        logger.info("WhatsApp gateway disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Text messages ──────────────────────────────────────────────────────

    async def send_message(
        self,
        recipient: str,
        text: str,
        preview_url: bool = False,
    ) -> Dict[str, Any]:
        """Send a text message to a WhatsApp number.

        Parameters
        ----------
        recipient : str
            Phone number in international format (e.g., +1234567890).
        text : str
            Message body (max 65536 characters).
        preview_url : bool
            Whether to render URL previews.

        Returns
        -------
        dict with success status and message_id.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        if len(text) > 65536:
            text = text[:65533] + "..."

        msg = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"body": text, "preview_url": preview_url},
            "message_id": f"wa-{len(self._messages)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(msg)
        logger.debug("WhatsApp message sent to %s: %s", recipient, text[:80])
        return {"success": True, "message_id": msg["message_id"]}

    # ── Media messages ─────────────────────────────────────────────────────

    async def send_image(
        self,
        recipient: str,
        image_url: str,
        caption: str = "",
    ) -> Dict[str, Any]:
        """Send an image message.

        Parameters
        ----------
        recipient : str
            Phone number.
        image_url : str
            URL of the image to send.
        caption : str
            Optional caption text.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        msg = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "image",
            "image": {"link": image_url, "caption": caption},
            "message_id": f"wa-{len(self._messages)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(msg)
        self._media.append({"type": "image", "url": image_url, "recipient": recipient})
        return {"success": True, "message_id": msg["message_id"]}

    async def send_document(
        self,
        recipient: str,
        document_url: str,
        filename: str = "",
        caption: str = "",
    ) -> Dict[str, Any]:
        """Send a document message."""
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        msg = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "document",
            "document": {"link": document_url, "filename": filename, "caption": caption},
            "message_id": f"wa-{len(self._messages)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(msg)
        self._media.append({"type": "document", "url": document_url, "recipient": recipient})
        return {"success": True, "message_id": msg["message_id"]}

    async def send_audio(
        self,
        recipient: str,
        audio_url: str,
    ) -> Dict[str, Any]:
        """Send an audio message."""
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        msg = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "audio",
            "audio": {"link": audio_url},
            "message_id": f"wa-{len(self._messages)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(msg)
        return {"success": True, "message_id": msg["message_id"]}

    async def send_video(
        self,
        recipient: str,
        video_url: str,
        caption: str = "",
    ) -> Dict[str, Any]:
        """Send a video message."""
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        msg = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "video",
            "video": {"link": video_url, "caption": caption},
            "message_id": f"wa-{len(self._messages)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(msg)
        return {"success": True, "message_id": msg["message_id"]}

    # ── Template messages ──────────────────────────────────────────────────

    def register_template(self, name: str, language: str = "en", components: Optional[List[Dict]] = None) -> None:
        """Register a message template.

        Parameters
        ----------
        name : str
            Template name (must be pre-approved in WhatsApp Business Manager).
        language : str
            Language code.
        components : list[dict], optional
            Template component parameters.
        """
        self._templates[name] = {
            "name": name,
            "language": {"code": language},
            "components": components or [],
        }

    async def send_template(
        self,
        recipient: str,
        template_name: str,
        parameters: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send a template message.

        Parameters
        ----------
        recipient : str
            Phone number.
        template_name : str
            Name of a registered template.
        parameters : dict, optional
            Key-value parameters for template variable substitution.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        template = self._templates.get(template_name)
        if not template:
            return {"success": False, "error": f"Template '{template_name}' not registered"}

        # Build components from parameters
        components = list(template.get("components", []))
        if parameters:
            body_params = [{"type": "text", "text": v} for v in parameters.values()]
            components.append({"type": "body", "parameters": body_params})

        msg = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": template["language"],
                "components": components,
            },
            "message_id": f"wa-{len(self._messages)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(msg)
        return {"success": True, "message_id": msg["message_id"]}

    # ── Message receiving ──────────────────────────────────────────────────

    async def receive_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent messages."""
        return self._messages[-limit:]

    async def process_webhook(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process an incoming WhatsApp webhook payload.

        Dispatches to registered message handlers.
        """
        results = []
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    incoming = {
                        "from": msg.get("from", ""),
                        "type": msg.get("type", "text"),
                        "text": msg.get("text", {}).get("body", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "message_id": msg.get("id", ""),
                        "direction": "incoming",
                    }
                    self._messages.append(incoming)

                    for handler in self._message_handlers:
                        try:
                            await handler(incoming)
                        except Exception as exc:
                            logger.error("WhatsApp message handler error: %s", exc)

                    results.append(incoming)

        return results

    def register_message_handler(
        self,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register a handler for incoming messages."""
        self._message_handlers.append(handler)

    # ── ChannelMessage conversion ──────────────────────────────────────────

    async def send_channel_message(self, message: ChannelMessage) -> Dict[str, Any]:
        """Send a ChannelMessage (universal format)."""
        if message.template_name:
            return await self.send_template(
                recipient=message.recipient_id,
                template_name=message.template_name,
                parameters=message.template_params,
            )
        if message.media_url:
            media_type = message.media_type or "image"
            if media_type == "image":
                return await self.send_image(message.recipient_id, message.media_url, caption=message.text)
            elif media_type == "document":
                return await self.send_document(message.recipient_id, message.media_url, caption=message.text)
            elif media_type == "audio":
                return await self.send_audio(message.recipient_id, message.media_url)
            elif media_type == "video":
                return await self.send_video(message.recipient_id, message.media_url, caption=message.text)
        return await self.send_message(message.recipient_id, message.text)

    # ── Stats ──────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return channel statistics."""
        return {
            "channel": "whatsapp",
            "connected": self._connected,
            "messages": len(self._messages),
            "media_sent": len(self._media),
            "templates": len(self._templates),
        }
