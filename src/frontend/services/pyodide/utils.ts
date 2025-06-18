import { PYODIDE_CONFIG } from './constants';

/**
 * Cryptographically-strong hash for caching user code (hex-encoded SHA-256)
 */
export async function computeHash(str: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(str);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Check if an HTTP method typically modifies data (and thus requires persistence sync)
 */
export function isMutatingMethod(method: string): boolean {
  const upperMethod = method.toUpperCase();
  return (PYODIDE_CONFIG.MUTATING_METHODS as readonly string[]).includes(
    upperMethod
  );
}

/**
 * Analyze Python code to determine required packages
 */
export function analyzePythonDependencies(code: string): string[] {
  const packages: string[] = [];

  // Smart dependency detection based on imports
  const importLines = code
    .split("\n")
    .filter(
      (line) =>
        line.trim().startsWith("import ") || line.trim().startsWith("from ")
    )
    .map((line) => line.trim());

  for (const line of importLines) {
    if (line.includes("fastapi") && !packages.includes("fastapi")) {
      packages.push("fastapi");
    }
    if (line.includes("sqlalchemy") && !packages.includes("sqlalchemy")) {
      packages.push("sqlalchemy");
    }
    if (line.includes("pydantic") && !packages.includes("pydantic")) {
      packages.push("pydantic");
    }
    if (line.includes("uvicorn") && !packages.includes("uvicorn")) {
      packages.push("uvicorn");
    }
  }

  return packages;
}

/**
 * Load a script dynamically and return a promise
 */
export function loadScript(src: string): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.crossOrigin = "anonymous";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.head.appendChild(script);
  });
}
