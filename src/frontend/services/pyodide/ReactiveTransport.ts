/**
 * ReactiveTransport - HTTP transport for reactive sync
 *
 * Implements the Transport interface for making HTTP requests to the server.
 */

export class ReactiveTransport {
  constructor(
    private serverBaseUrl: string,
    private getAccessToken: () => string
  ) {}

  /**
   * Make a POST request with JSON payload
   *
   * @param path - API endpoint path (e.g., "/_sync/pull")
   * @param payload - Request body as object
   * @returns Response body as object
   */
  async post_json(path: string, payload: any): Promise<any> {
    const url = this.serverBaseUrl + path;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.getAccessToken()}`,
      },
      body: JSON.stringify(payload),
      credentials: "include",
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return await response.json();
  }
}
