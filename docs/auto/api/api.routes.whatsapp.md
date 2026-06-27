# api.routes.whatsapp

## Class: 

WhatsApp message types.

*Line: 49*

---

## Class: 

Message direction.

*Line: 61*

---

## Class: 

Supported WhatsApp commands.

*Line: 67*

---

## Class: 

Incoming WhatsApp message.

*Line: 86*

---

## Class: 

Parsed command from a WhatsApp message.

*Line: 98*

---

## Class: 

Outbound WhatsApp message.

*Line: 106*

---

## Class: 

Notification subscription configuration.

*Line: 115*

---

## Class: 

Notification message for push.

*Line: 126*

---

## Function: 

Parse a WhatsApp message for bot commands.

Args:
    message: Message text to parse.
    chat_id: Source chat ID.

Returns:
    ParsedCommand if the message is a command, None otherwise.

*Line: 172*

---

## Class: 

WhatsApp gateway for message routing and notification push.

Provides message routing to agents, command parsing, and
notification push for trade alerts and risk warnings.

Usage::

    gateway = WhatsAppGateway()
    await gateway.handle_inbound(message)
    await gateway.push_notification(notification)

**Methods:** __init__, _subscribe, _unsubscribe, _get_recipients, _format_help, _format_notification

*Line: 215*

---

## Function: 

*Line: 534*

---

## Function: 

*Line: 228*

---

## Function: 

Subscribe a chat to notifications.

*Line: 441*

---

## Function: 

Unsubscribe a chat from notifications.

*Line: 446*

---

## Function: 

Get list of chat IDs that should receive a notification.

*Line: 450*

---

## Function: 

Format help message.

*Line: 470*

---

## Function: 

Format a notification for WhatsApp.

*Line: 488*

---

