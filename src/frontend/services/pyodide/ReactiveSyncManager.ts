/**
 * ReactiveSyncManager - SSE subscription manager for reactive sync
 *
 * Manages Server-Sent Events connection for poke notifications.
 * When a poke is received, triggers a pull operation in Python.
 */

import { PyodideInterface } from "./types";

export class ReactiveSyncManager {
  private eventSource: EventSource | null = null;
  private subscribedTopics: Set<string> = new Set();
  private pyodide: PyodideInterface;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000; // 30 seconds

  constructor(
    pyodide: PyodideInterface,
    private serverBaseUrl: string,
    private getAccessToken: () => string
  ) {
    this.pyodide = pyodide;
  }

  /**
   * Subscribe to additional topics
   *
   * @param topics - Array of topic strings to subscribe to
   */
  subscribe(topics: string[]): void {
    const hadTopics = this.subscribedTopics.size > 0;

    topics.forEach(t => this.subscribedTopics.add(t));

    // Reconnect with updated topic list
    if (hadTopics || topics.length > 0) {
      this.reconnect();
    }
  }

  /**
   * Unsubscribe from topics
   *
   * @param topics - Array of topic strings to unsubscribe from
   */
  unsubscribe(topics: string[]): void {
    topics.forEach(t => this.subscribedTopics.delete(t));

    // Reconnect with updated topic list
    this.reconnect();
  }

  /**
   * Get currently subscribed topics
   */
  getSubscribedTopics(): string[] {
    return Array.from(this.subscribedTopics);
  }

  /**
   * Reconnect SSE stream with current topic list
   */
  private reconnect(): void {
    // Close existing connection
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    if (this.subscribedTopics.size === 0) {
      return;
    }

    // Build SSE URL with topics
    const topicsParam = Array.from(this.subscribedTopics).join(",");
    const url = `${this.serverBaseUrl}/_sync/events?topics=${encodeURIComponent(topicsParam)}`;

    console.log(`🔗 Connecting to SSE stream: ${topicsParam}`);

    // Create EventSource
    // Note: EventSource doesn't support custom headers, so auth token
    // would need to be passed in URL or use a polyfill like fetch-event-source
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      console.log("✅ SSE connection established");
      this.reconnectAttempts = 0; // Reset on successful connection
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "poke") {
          console.log(`📬 Poke received: ${data.topic} @ ${data.checkpoint}`);
          this.handlePoke(data.topic);
        } else if (data.type === "connected") {
          console.log(`🎉 SSE connected to topics:`, data.topics);
        }
      } catch (error) {
        console.error("❌ Error parsing SSE message:", error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error("❌ SSE connection error:", error);

      // Close the connection
      if (this.eventSource) {
        this.eventSource.close();
        this.eventSource = null;
      }

      // Implement exponential backoff reconnection
      const delay = Math.min(
        1000 * Math.pow(2, this.reconnectAttempts),
        this.maxReconnectDelay
      );

      this.reconnectAttempts++;

      console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);

      setTimeout(() => {
        if (this.subscribedTopics.size > 0) {
          this.reconnect();
        }
      }, delay);
    };
  }

  /**
   * Handle poke notification by triggering pull in Python
   *
   * @param topic - Topic that has new changes
   */
  private handlePoke(topic: string): void {
    try {
      // Call Python's handle_poke via Pyodide
      this.pyodide.runPython(`
try:
    from app.app_main import app
    if hasattr(app.state, 'handle_poke'):
        app.state.handle_poke(${JSON.stringify(topic)})
    else:
        print("Warning: app.state.handle_poke not found (client sync not mounted)")
except Exception as e:
    print(f"Error handling poke for ${topic}: {e}")
      `);

      // Dispatch custom event for UI to listen to
      window.dispatchEvent(
        new CustomEvent("reactive-sync", {
          detail: { topic, timestamp: Date.now() },
        })
      );
    } catch (error) {
      console.error(`❌ Error handling poke for ${topic}:`, error);
    }
  }

  /**
   * Disconnect and cleanup
   */
  disconnect(): void {
    if (this.eventSource) {
      console.log("🔌 Disconnecting SSE stream");
      this.eventSource.close();
      this.eventSource = null;
    }

    this.subscribedTopics.clear();
    this.reconnectAttempts = 0;
  }
}
