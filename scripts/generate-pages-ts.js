#!/usr/bin/env node

import fs from "fs";
import path from "path";
import { Project, SourceFile } from "ts-morph";
import { fileURLToPath } from "url";

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const CONFIG = {
  specUrl: "http://localhost:8000/openapi.json",
  clientDir: path.join(__dirname, "..", "apps", "frontend", "src", "client"),
  pagesDir: path.join(__dirname, "..", "apps", "frontend", "src", "pages"),
};

// Colors for console output
const colors = {
  reset: "\x1b[0m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

class TypeScriptPageGenerator {
  constructor() {
    this.project = new Project({
      tsConfigFilePath: path.join(
        __dirname,
        "..",
        "apps",
        "frontend",
        "tsconfig.json"
      ),
    });
  }

  async generatePages() {
    log("🔍 Analyzing generated TypeScript client...", colors.cyan);

    // Load the generated SDK and types
    const sdkFile = this.project.addSourceFileAtPath(
      path.join(CONFIG.clientDir, "sdk.gen.ts")
    );
    const typesFile = this.project.addSourceFileAtPath(
      path.join(CONFIG.clientDir, "types.gen.ts")
    );

    // Extract function exports and their types
    const apiFunctions = this.extractApiFunctions(sdkFile);
    const types = this.extractTypes(typesFile);

    // Group functions by domain
    const domains = this.groupFunctionsByDomain(apiFunctions);

    log(
      `📊 Found ${Object.keys(domains).length} domains: ${Object.keys(
        domains
      ).join(", ")}`,
      colors.blue
    );

    // Generate pages for each domain
    for (const [domain, functions] of Object.entries(domains)) {
      await this.generateDomainPage(domain, functions, types);
    }

    // Update index.ts
    await this.updatePageIndex(Object.keys(domains));

    log("✅ TypeScript page generation completed!", colors.green);
  }

  extractApiFunctions(sdkFile) {
    const functions = new Map();

    // Get all exported function declarations
    const exportedDeclarations = sdkFile.getExportedDeclarations();

    for (const [name, declarations] of exportedDeclarations) {
      const declaration = declarations[0];
      if (declaration.getKind() === "VariableDeclaration") {
        const functionSignature = this.parseFunctionSignature(declaration);
        if (functionSignature) {
          functions.set(name, functionSignature);
        }
      }
    }

    return functions;
  }

  extractTypes(typesFile) {
    const types = new Map();

    // Get all exported type declarations
    const exportedDeclarations = typesFile.getExportedDeclarations();

    for (const [name, declarations] of exportedDeclarations) {
      const declaration = declarations[0];
      if (declaration.getKind() === "TypeAliasDeclaration") {
        types.set(name, declaration.getTypeNode().getText());
      }
    }

    return types;
  }

  parseFunctionSignature(declaration) {
    // Parse the function signature to extract method, path, parameters
    const initializer = declaration.getInitializer();
    if (!initializer) return null;

    // This would need to parse the __request call to extract:
    // - HTTP method
    // - URL path
    // - Parameters
    // - Return type

    return {
      name: declaration.getName(),
      method: "GET", // Would extract from __request call
      path: "/api/v1/example", // Would extract from __request call
      parameters: [], // Would extract from data parameter type
      returnType: "unknown", // Would extract from function return type
    };
  }

  groupFunctionsByDomain(functions) {
    const domains = {};

    for (const [name, func] of functions) {
      // Extract domain from function name (e.g., getUsers -> users)
      const match = name.match(/^(get|create|update|delete)(.+?)s?$/);
      if (match) {
        const domain = match[2].toLowerCase();
        if (!domains[domain]) {
          domains[domain] = [];
        }
        domains[domain].push({ name, ...func });
      }
    }

    return domains;
  }

  async generateDomainPage(domain, functions, types) {
    log(`📝 Generating ${domain} page...`, colors.cyan);

    const capitalizedDomain = domain.charAt(0).toUpperCase() + domain.slice(1);
    const fileName = `${capitalizedDomain}Page.tsx`;
    const filePath = path.join(CONFIG.pagesDir, fileName);

    // Create a new source file
    const sourceFile = this.project.createSourceFile(filePath, "", {
      overwrite: true,
    });

    // Add imports
    sourceFile.addImportDeclarations([
      {
        moduleSpecifier: "react",
        namedImports: ["React"],
      },
      {
        moduleSpecifier: "react-router-dom",
        namedImports: ["Link", "useParams"],
      },
      {
        moduleSpecifier: "../client",
        namedImports: functions.map((f) => f.name),
      },
    ]);

    // Add type imports
    const responseType = `${capitalizedDomain}Response`;
    if (types.has(responseType)) {
      sourceFile.addImportDeclaration({
        moduleSpecifier: "../client",
        namedImports: [responseType],
        isTypeOnly: true,
      });
    }

    // Generate the main page component
    sourceFile.addFunction({
      name: `${capitalizedDomain}Page`,
      isExported: true,
      returnType: "React.FC",
      statements: [
        "const { id } = useParams<{ id: string }>();",
        "",
        "if (id) {",
        `  return <${capitalizedDomain}Detail id={id} />;`,
        "}",
        "",
        `return <${capitalizedDomain}List />;`,
      ].join("\n"),
    });

    // Generate list component
    this.generateListComponent(sourceFile, domain, functions, types);

    // Generate detail component
    this.generateDetailComponent(sourceFile, domain, functions, types);

    // Save the file
    await sourceFile.save();

    log(`✅ Generated ${fileName}`, colors.green);
  }

  generateListComponent(sourceFile, domain, functions, types) {
    const capitalizedDomain = domain.charAt(0).toUpperCase() + domain.slice(1);
    const listFunction = functions.find(
      (f) => f.name.startsWith("get") && f.name.includes(domain)
    );

    if (!listFunction) return;

    sourceFile.addFunction({
      name: `${capitalizedDomain}List`,
      returnType: "React.FC",
      statements: `
        // Use the generated API function
        const { data, isLoading, error } = useQuery({
          queryKey: ['${domain}'],
          queryFn: () => ${listFunction.name}()
        });

        return (
          <div className="min-h-screen bg-gray-50">
            {/* Component implementation */}
          </div>
        );
      `,
    });
  }

  generateDetailComponent(sourceFile, domain, functions, types) {
    const capitalizedDomain = domain.charAt(0).toUpperCase() + domain.slice(1);
    const detailFunction = functions.find(
      (f) =>
        f.name.startsWith("get") &&
        f.name.includes(domain) &&
        !f.name.endsWith("s")
    );

    if (!detailFunction) return;

    sourceFile.addFunction({
      name: `${capitalizedDomain}Detail`,
      parameters: [{ name: "id", type: "string" }],
      returnType: "React.FC<{ id: string }>",
      statements: `
        // Use the generated API function with proper typing
        const { data, isLoading, error } = useQuery({
          queryKey: ['${domain}', id],
          queryFn: () => ${detailFunction.name}({ userId: parseInt(id) })
        });

        return (
          <div className="min-h-screen bg-gray-50">
            {/* Component implementation */}
          </div>
        );
      `,
    });
  }

  async updatePageIndex(domains) {
    log("📝 Updating pages index...", colors.cyan);

    const indexPath = path.join(CONFIG.pagesDir, "index.ts");
    const indexFile = this.project.createSourceFile(indexPath, "", {
      overwrite: true,
    });

    // Add exports for all generated pages
    for (const domain of domains) {
      const capitalizedDomain =
        domain.charAt(0).toUpperCase() + domain.slice(1);
      indexFile.addExportDeclaration({
        moduleSpecifier: `./${capitalizedDomain}Page`,
        namedExports: [`${capitalizedDomain}Page`],
      });
    }

    await indexFile.save();
    log("✅ Updated pages index", colors.green);
  }
}

// Main execution
async function main() {
  try {
    const generator = new TypeScriptPageGenerator();
    await generator.generatePages();
  } catch (error) {
    log(`❌ Error: ${error.message}`, colors.red);
    console.error(error);
    process.exit(1);
  }
}

main();
