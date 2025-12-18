import React, { useState } from 'react';

import { PyodideEndpoint } from './index';
import { FormData, FormField } from './types';

interface InteractiveFormProps {
  endpoint: PyodideEndpoint;
  onSubmit: (data: FormData) => Promise<void>;
  initialData?: FormData;
}

export const InteractiveForm: React.FC<InteractiveFormProps> = ({
  endpoint,
  onSubmit,
  initialData,
}) => {
  const [formData, setFormData] = useState<FormData>(initialData || {});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(formData);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    field: string,
    value: string | number | boolean | undefined
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const getFormFields = (): FormField[] => {
    switch (endpoint.operationId) {
      case "create_todo":
        return [
          { name: "title", type: "text", label: "Title", required: true },
          { name: "description", type: "textarea", label: "Description" },
          { name: "priority", type: "text", label: "Priority (low/normal/high)" },
          { name: "completed", type: "checkbox", label: "Completed" },
        ];
      case "update_todo":
        return [
          { name: "title", type: "text", label: "Title" },
          { name: "description", type: "textarea", label: "Description" },
          { name: "priority", type: "text", label: "Priority" },
          { name: "completed", type: "checkbox", label: "Completed" },
        ];
      case "list_todos":
        return [
          { name: "search", type: "text", label: "Search title/description" },
          { name: "completed", type: "text", label: "Completed (true/false)" },
          { name: "skip", type: "number", label: "Skip", min: 0 },
          { name: "limit", type: "number", label: "Limit", min: 1, max: 100 },
        ];
      default:
        return [];
    }
  };

  const fields = getFormFields();
  if (fields.length === 0) return null;

  const getFormTitle = (): string => {
    switch (endpoint.operationId) {
      case "create_todo":
        return "Create Todo";
      case "update_todo":
        return "Update Todo";
      case "list_todos":
        return "Filter Todos";
      default:
        return endpoint.summary || "Execute Action";
    }
  };

  const getSubmitButtonText = (): string => {
    if (isSubmitting) return "Processing...";

    switch (endpoint.operationId) {
      case "create_todo":
        return "Create Todo";
      case "update_todo":
        return "Update Todo";
      case "list_todos":
        return "Search";
      default:
        return "Execute";
    }
  };

  return (
    <div
      style={{
        marginBottom: "20px",
        padding: "20px",
        backgroundColor: "#f8f9fa",
        borderRadius: "8px",
        border: "1px solid #dee2e6",
      }}
    >
      <h4 style={{ marginTop: 0, color: "#495057" }}>{getFormTitle()}</h4>
      <form onSubmit={handleSubmit}>
        {fields.map((field) => (
          <div key={field.name} style={{ marginBottom: "15px" }}>
            <label
              style={{
                display: "block",
                marginBottom: "5px",
                fontWeight: "500",
                color: "#495057",
              }}
            >
              {field.label}
              {field.required && <span style={{ color: "#dc3545" }}>*</span>}
            </label>
            {field.type === "checkbox" ? (
              <input
                type="checkbox"
                checked={Boolean(formData[field.name])}
                onChange={(e) => handleChange(field.name, e.target.checked)}
                style={{ transform: "scale(1.2)" }}
              />
            ) : field.type === "action" ? null : field.type === "textarea" ? (
              <textarea
                value={formData[field.name] ? String(formData[field.name]) : ""}
                onChange={(e) => handleChange(field.name, e.target.value)}
                required={field.required}
                placeholder={`Enter ${field.label.toLowerCase()}`}
                rows={4}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  border: "1px solid " + "#ced4da",
                  borderRadius: "4px",
                  fontSize: "14px",
                  resize: "vertical",
                }}
              />
            ) : (
              <input
                type={field.type}
                value={formData[field.name] ? String(formData[field.name]) : ""}
                onChange={(e) =>
                  handleChange(
                    field.name,
                    field.type === "number"
                      ? e.target.value
                        ? Number(e.target.value)
                        : undefined
                      : e.target.value
                  )
                }
                required={field.required}
                min={field.min}
                max={field.max}
                placeholder={`Enter ${field.label.toLowerCase()}`}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  border: "1px solid " + "#ced4da",
                  borderRadius: "4px",
                  fontSize: "14px",
                }}
              />
            )}
          </div>
        ))}
        <button
          type="submit"
          disabled={isSubmitting}
          style={{
            backgroundColor:
              endpoint.method === "POST"
                ? "#28a745"
                : endpoint.method === "PUT"
                ? "#ffc107"
                : "#17a2b8",
            color: endpoint.method === "PUT" ? "#212529" : "white",
            border: "none",
            padding: "10px 20px",
            borderRadius: "4px",
            cursor: isSubmitting ? "not-allowed" : "pointer",
            fontSize: "14px",
            fontWeight: "500",
          }}
        >
          {getSubmitButtonText()}
        </button>
      </form>
    </div>
  );
};
