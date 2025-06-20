import { APIEndpoint, RouteConfig } from "../router/types";

interface OpenAPIEndpoint {
  operationId?: string;
  summary?: string;
  tags?: string[];
  parameters?: unknown[];
  requestBody?: unknown;
  responses?: unknown;
}

interface OpenAPISchema {
  paths?: Record<string, Record<string, OpenAPIEndpoint>>;
  components?: {
    schemas?: Record<string, OpenAPISchemaObject>;
  };
}

interface OpenAPISchemaObject {
  type?: string;
  properties?: Record<string, OpenAPISchemaObject>;
  required?: string[];
  items?: OpenAPISchemaObject;
  $ref?: string;
}

export const generateRoutesFromSchema = async (
  schemaURL: string
): Promise<RouteConfig[]> => {
  try {
    const response = await fetch(schemaURL);
    const schema: OpenAPISchema = await response.json();

    const routes: RouteConfig[] = [];

    // Parse OpenAPI schema and generate routes
    for (const [path, methods] of Object.entries(schema.paths || {})) {
      for (const [method, endpoint] of Object.entries(methods)) {
        if (endpoint && endpoint.operationId) {
          const apiEndpoint: APIEndpoint = {
            path,
            method: method.toUpperCase() as
              | "GET"
              | "POST"
              | "PUT"
              | "DELETE"
              | "PATCH",
            operationId: endpoint.operationId,
            summary: endpoint.summary,
            tags: endpoint.tags,
            parameters: endpoint.parameters as
              | Array<{
                  name: string;
                  in: "path" | "query" | "header";
                  required?: boolean;
                  schema: unknown;
                }>
              | undefined,
            requestBody: endpoint.requestBody as
              | {
                  content: Record<string, unknown>;
                }
              | undefined,
            responses: (endpoint.responses as Record<string, unknown>) || {},
          }; // Create route based on endpoint
          const route: RouteConfig = {
            path: convertOpenAPIPathToReactRouter(path),
            apiEndpoint,
            element: null, // Will be replaced with actual component
          };

          routes.push(route);
        }
      }
    }

    return routes;
  } catch (error) {
    console.error("Failed to generate routes from schema:", error);
    return [];
  }
};

const convertOpenAPIPathToReactRouter = (openAPIPath: string): string => {
  // Convert {param} to :param for React Router
  return openAPIPath.replace(/{([^}]+)}/g, ":$1");
};

export const generateTypeScript = (schema: OpenAPISchema): string => {
  // Generate TypeScript interfaces from OpenAPI schema
  let typescript = "// Auto-generated types from FastAPI OpenAPI schema\n\n";

  if (schema.components?.schemas) {
    for (const [name, schemaObj] of Object.entries(schema.components.schemas)) {
      typescript += generateInterface(name, schemaObj);
    }
  }

  return typescript;
};

const generateInterface = (
  name: string,
  schema: OpenAPISchemaObject
): string => {
  let interfaceStr = `export interface ${name} {\n`;

  if (schema.properties) {
    for (const [propName, propSchema] of Object.entries(schema.properties)) {
      const optional = !schema.required?.includes(propName) ? "?" : "";
      const type = mapOpenAPITypeToTypeScript(propSchema);
      interfaceStr += `  ${propName}${optional}: ${type};\n`;
    }
  }

  interfaceStr += "}\n\n";
  return interfaceStr;
};

const mapOpenAPITypeToTypeScript = (schema: OpenAPISchemaObject): string => {
  switch (schema.type) {
    case "string":
      return "string";
    case "number":
    case "integer":
      return "number";
    case "boolean":
      return "boolean";
    case "array":
      return schema.items
        ? `${mapOpenAPITypeToTypeScript(schema.items)}[]`
        : "unknown[]";
    case "object":
      return "Record<string, unknown>";
    default:
      if (schema.$ref) {
        return schema.$ref.split("/").pop() || "unknown";
      }
      return "unknown";
  }
};
