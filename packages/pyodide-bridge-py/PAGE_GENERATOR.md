# Page Component Generator

The `pyodide-bridge` package includes a powerful page component generator that can automatically create React page components from your FastAPI OpenAPI schema.

## Overview

The page generator analyzes your FastAPI application's API endpoints and generates modern React components with:

- ✅ **TypeScript interfaces** from Pydantic models
- ✅ **List and detail views** for CRUD operations
- ✅ **Modern UI components** with Tailwind CSS
- ✅ **API integration** using react-router-fastapi hooks
- ✅ **Loading and error states**
- ✅ **Responsive design**
- ✅ **File preservation** - won't overwrite existing pages

## Usage

### Basic Usage

Generate all page components from your FastAPI backend:

```bash
pyodide-bridge generate-pages
```

This will:
1. Load your FastAPI app from `apps/backend/src`
2. Generate OpenAPI schema
3. Create React page components in `apps/frontend/src/pages`
4. Update the index.ts export file

### Options

```bash
# Dry run to see what would be generated
pyodide-bridge generate-pages --dry-run

# Custom paths
pyodide-bridge generate-pages --backend-path custom/backend/path --output-dir custom/pages/dir

# Load from existing OpenAPI JSON file
pyodide-bridge generate-pages --schema-file schema.json

# Enable debug logging
pyodide-bridge generate-pages --debug
```

### Package.json Scripts

Add these convenience scripts to your `package.json`:

```json
{
  "scripts": {
    "gen:pages": "pyodide-bridge generate-pages",
    "gen:pages:dry": "pyodide-bridge generate-pages --dry-run"
  }
}
```

## Generated Components

### Component Structure

Each domain gets a page component with:

- **List View**: Shows all items with pagination support
- **Detail View**: Shows individual item details
- **Error Handling**: Displays API errors gracefully
- **Loading States**: Shows skeleton loading animations

### Example Generated Component

For a `users` API endpoint, the generator creates:

```tsx
// UsersPage.tsx
export const UsersPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  
  if (id) {
    return <UsersDetail id={id} />;
  }
  
  return <UsersList />;
};

const UsersList: React.FC = () => {
  const { data: users, isLoading, error } = useAPIQuery<UserResponse[]>(
    ['users'],
    '/api/v1/users'
  );
  
  // ... UI components
};
```

### Generated Files

The generator creates:

- `{Domain}Page.tsx` - Main page component for each API domain
- `index.ts` - Exports all page components

Example output for a typical FastAPI app:
```
pages/
├── UsersPage.tsx          # /api/v1/users endpoints
├── PostsPage.tsx          # /api/v1/posts endpoints  
├── DashboardPage.tsx      # /api/v1/dashboard endpoints
├── SystemPage.tsx         # /api/v1/system endpoints
├── AnalyticsPage.tsx      # /api/v1/analytics endpoints
└── index.ts               # Exports all components
```

## How It Works

### 1. Domain Detection

The generator analyzes API paths to group endpoints by domain:

- `/api/v1/users` → `users` domain
- `/api/v1/posts/{id}` → `posts` domain
- `/api/v1/dashboard/stats` → `dashboard` domain

### 2. Endpoint Classification

For each domain, it identifies:

- **List endpoints**: `GET /api/v1/users` (no path parameters)
- **Detail endpoints**: `GET /api/v1/users/{id}` (with path parameters)
- **Create endpoints**: `POST /api/v1/users`

### 3. TypeScript Generation

Generates TypeScript interfaces from Pydantic models:

```tsx
interface UserResponse {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  created_at: string;
}
```

### 4. Component Generation

Creates React components with:
- Modern hook-based architecture
- Error boundaries
- Loading states
- Responsive design
- Tailwind CSS styling

## File Preservation

The generator is smart about existing files:

- ✅ **Preserves manual pages** - Won't overwrite `HomePage.tsx`, custom components
- ✅ **Skips existing files** - Shows "Skipping... file already exists" 
- ✅ **Updates index.ts** - Always regenerates exports to include all pages
- ✅ **Clean naming** - Converts `health-async` → `HealthasyncPage.tsx`

## Integration with React Router

Generated components work seamlessly with react-router-fastapi:

```tsx
// In your App.tsx routes
const routes: RouteConfig[] = [
  { path: '/users', element: <UsersPage /> },
  { path: '/users/:id', element: <UsersPage /> }, // Shows detail view
  { path: '/posts', element: <PostsPage /> },
  // ... other routes
];
```

## Customization

### Manual Enhancement

After generation, you can enhance components:

1. **Add custom styling** - Modify Tailwind classes
2. **Add business logic** - Custom hooks, validation
3. **Add actions** - Create, edit, delete functionality
4. **Add charts/widgets** - Data visualization

### Regeneration

Re-running the generator:
- Preserves existing files
- Only creates new pages for new API endpoints
- Updates the index.ts exports

## Best Practices

### 1. Consistent API Design

For best results, follow FastAPI conventions:

```python
# Good - Clear domain separation
@router.get("/users", operation_id="get_users")
@router.get("/users/{user_id}", operation_id="get_user")
@router.post("/users", operation_id="create_user")

# Good - Descriptive operation IDs
@router.get("/dashboard/stats", operation_id="get_dashboard_stats")
```

### 2. Pydantic Models

Use clear Pydantic response models:

```python
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime
```

### 3. Manual Pages First

Create important pages manually, then use the generator for utility pages:

```
Manual:     HomePage, DashboardPage, LoginPage
Generated:  UsersPage, PostsPage, AnalyticsPage, SystemPage
```

## Troubleshooting

### Common Issues

**"No module named 'app'"**
- Ensure backend path is correct
- Check that `app_main.py` exists and has an `app` variable

**"Failed to generate OpenAPI schema"**
- Verify your FastAPI app starts without errors
- Check for import issues in your backend code

**Missing components in index.ts**
- Non-`*Page.tsx` files need manual export
- Re-run generator to update exports

### Debug Mode

Enable debug logging to see detailed information:

```bash
pyodide-bridge generate-pages --debug
```

This shows:
- Python import paths
- Available endpoints
- Generated files
- Error details

## Examples

### E-commerce App

API endpoints:
```
GET    /api/v1/products
GET    /api/v1/products/{id}
POST   /api/v1/products
GET    /api/v1/orders  
GET    /api/v1/orders/{id}
POST   /api/v1/orders
GET    /api/v1/dashboard
```

Generated pages:
- `ProductsPage.tsx` - Product listing and details
- `OrdersPage.tsx` - Order management
- `DashboardPage.tsx` - Admin dashboard

### Blog Platform

API endpoints:
```
GET    /api/v1/posts
GET    /api/v1/posts/{id}
POST   /api/v1/posts
GET    /api/v1/authors
GET    /api/v1/authors/{id}
GET    /api/v1/analytics
```

Generated pages:
- `PostsPage.tsx` - Blog post management
- `AuthorsPage.tsx` - Author profiles
- `AnalyticsPage.tsx` - Blog analytics

## Future Enhancements

Planned features:
- **Form generation** - Auto-generate create/edit forms
- **Table components** - Advanced data tables with sorting/filtering
- **Chart integration** - Auto-detect metrics endpoints
- **Theme support** - Generate with different UI frameworks
- **Custom templates** - User-defined component templates
