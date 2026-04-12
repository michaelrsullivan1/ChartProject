export type DatabaseHealthResponse = {
  connected: boolean;
  status: string;
  detail: string;
};

export type HealthResponse = {
  status: string;
  app_name: string;
  environment: string;
  database: DatabaseHealthResponse;
};
