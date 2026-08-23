/** Response payload returned by the backend `GET /health` endpoint. */
export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}
