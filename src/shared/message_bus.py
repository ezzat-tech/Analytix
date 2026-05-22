"""Message bus for inter-agent communication."""

import asyncio
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """Message passed on the message bus."""

    topic: str
    payload: Dict[str, Any]
    sender: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MessageBus:
    """
    Async pub/sub message bus for agent communication.

    Allows agents to:
    - Subscribe to topics
    - Publish messages
    - Request/response patterns
    """

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_history: List[Message] = []
        self.lock = asyncio.Lock()

    def subscribe(self, topic: str, handler: Callable) -> str:
        """
        Subscribe to a topic.

        Args:
            topic: Topic name to subscribe to
            handler: Async callback function to handle messages

        Returns:
            Subscription ID (handler name)
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(handler)
        return handler.__name__

    def unsubscribe(self, topic: str, handler: Callable) -> bool:
        """Remove a subscription."""
        if topic in self.subscribers:
            try:
                self.subscribers[topic].remove(handler)
                return True
            except ValueError:
                pass
        return False

    async def publish(self, message: Message) -> int:
        """
        Publish a message to all subscribers.

        Args:
            message: Message to publish

        Returns:
            Number of subscribers notified
        """
        self.message_history.append(message)

        if message.topic not in self.subscribers:
            return 0

        # Fire and forget - don't wait for handlers
        tasks = [handler(message) for handler in self.subscribers[message.topic]]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return len(tasks)

    async def request_response(
        self,
        topic: str,
        payload: dict,
        sender: str = "unknown",
        timeout: float = 30.0
    ) -> Optional[dict]:
        """
        Send a request and wait for a response.

        Args:
            topic: Topic to publish request to
            payload: Request payload
            sender: Sender identifier
            timeout: Timeout in seconds

        Returns:
            Response payload or None on timeout
        """
        response_queue: asyncio.Queue = asyncio.Queue()
        response_topic = f"response.{topic}"

        async def responder(msg: Message):
            await response_queue.put(msg.payload)

        self.subscribe(response_topic, responder)

        # Publish request
        await self.publish(Message(topic=topic, payload=payload, sender=sender))

        try:
            response = await asyncio.wait_for(response_queue.get(), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return {"error": f"Request timeout after {timeout}s"}
        finally:
            self.unsubscribe(response_topic, responder)

    def get_topics(self) -> List[str]:
        """List all active topics."""
        return list(self.subscribers.keys())

    def get_subscriber_count(self, topic: str) -> int:
        """Get number of subscribers for a topic."""
        return len(self.subscribers.get(topic, []))

    def get_history(self, topic: Optional[str] = None, limit: int = 100) -> List[Message]:
        """Get recent message history."""
        if topic:
            filtered = [m for m in self.message_history if m.topic == topic]
            return filtered[-limit:]
        return self.message_history[-limit:]

    def clear_history(self):
        """Clear message history."""
        self.message_history.clear()
