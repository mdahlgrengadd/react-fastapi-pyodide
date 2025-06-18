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

  // Determine form fields based on endpoint
  const getFormFields = (): FormField[] => {
    if (endpoint.operationId === "create_user") {
      return [
        { name: "name", type: "text", label: "Name", required: true },
        { name: "email", type: "email", label: "Email", required: true },
        { name: "age", type: "number", label: "Age", min: 0, max: 150 },
      ];
    } else if (endpoint.operationId === "update_user") {
      return [
        { name: "name", type: "text", label: "Name" },
        { name: "email", type: "email", label: "Email" },
        { name: "age", type: "number", label: "Age", min: 0, max: 150 },
        { name: "is_active", type: "checkbox", label: "Active" },
      ];
    } else if (endpoint.operationId === "search_users") {
      return [
        { name: "name", type: "text", label: "Name (contains)" },
        { name: "email", type: "text", label: "Email (contains)" },
        { name: "min_age", type: "number", label: "Min Age", min: 0 },
        { name: "max_age", type: "number", label: "Max Age", max: 150 },
      ];
    } else if (endpoint.operationId === "clear_persistence") {
      return [
        { name: "confirm", type: "action", label: "Clear & Reset Database" },
      ];
    } else if (endpoint.operationId === "clear_backup_only") {
      return [
        { name: "confirm", type: "action", label: "Clear Backup Storage" },
      ];
    } else if (endpoint.operationId === "reset_to_defaults") {
      return [
        { name: "confirm", type: "action", label: "Reset to Default Data" },
      ];
    } else if (endpoint.operationId === "save_to_persistence") {
      return [{ name: "confirm", type: "action", label: "Save to Backup" }];
    } else if (endpoint.operationId === "restore_from_persistence") {
      return [
        { name: "confirm", type: "action", label: "Restore from Backup" },
      ];
    }
    return [];
  };

  const fields = getFormFields();

  if (fields.length === 0) return null;

  const getFormTitle = (): string => {
    switch (endpoint.operationId) {
      case "create_user":
        return "✨ Create New User";
      case "update_user":
        return "✏️ Update User";
      case "search_users":
        return "🔍 Search Users";
      case "clear_persistence":
        return "🗑️ Clear & Reset Database";
      case "clear_backup_only":
        return "🗄️ Clear Backup Storage";
      case "reset_to_defaults":
        return "🔄 Reset to Default Data";
      case "save_to_persistence":
        return "💾 Save to Backup";
      case "restore_from_persistence":
        return "📥 Restore from Backup";
      default:
        return endpoint.summary || "Execute Action";
    }
  };

  const getSubmitButtonText = (): string => {
    if (isSubmitting) return "⏳ Processing...";

    switch (endpoint.operationId) {
      case "create_user":
        return "✨ Create User";
      case "update_user":
        return "✏️ Update User";
      case "search_users":
        return "🔍 Search";
      case "clear_persistence":
        return "🗑️ Clear & Reset";
      case "clear_backup_only":
        return "🗄️ Clear Backup";
      case "reset_to_defaults":
        return "🔄 Reset to Defaults";
      case "save_to_persistence":
        return "💾 Save Backup";
      case "restore_from_persistence":
        return "📥 Restore";
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
            ) : field.type === "action" ? null : ( // For action buttons, don't render an input field
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
                  border: "1px solid #ced4da",
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
