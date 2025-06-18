export interface FormField {
  name: string;
  type: string;
  label: string;
  required?: boolean;
  min?: number;
  max?: number;
}

export interface FormData {
  [key: string]: string | number | boolean | undefined;
}

export interface ApiResponse {
  status_code?: number;
  content?: unknown;
  [key: string]: unknown;
}

export interface EndpointComponentProps {
  onError?: (error: Error) => void;
}
