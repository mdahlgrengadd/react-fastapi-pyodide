import React, { useState } from 'react';

import { PyodideEndpoint } from './index';

interface ActionButtonProps {
  endpoint: PyodideEndpoint;
  onAction: () => Promise<void>;
}

interface ButtonConfig {
  label: string;
  color: string;
  description: string;
}

export const ActionButton: React.FC<ActionButtonProps> = ({
  endpoint,
  onAction,
}) => {
  const [isExecuting, setIsExecuting] = useState(false);

  const handleClick = async () => {
    setIsExecuting(true);
    try {
      await onAction();
    } finally {
      setIsExecuting(false);
    }
  };

  const getButtonConfig = (): ButtonConfig => {
    switch (endpoint.operationId) {
      case "clear_persistence":
        return {
          label: "🗑️ Clear & Reset Database",
          color: "#dc3545",
          description: "Clear all data and reset to defaults",
        };
      case "clear_backup_only":
        return {
          label: "🗄️ Clear Backup Storage",
          color: "#6c757d",
          description: "Clear localStorage backup only",
        };
      case "reset_to_defaults":
        return {
          label: "🔄 Reset to Default Data",
          color: "#ffc107",
          description: "Reset database to sample data",
        };
      case "save_to_persistence":
        return {
          label: "💾 Save to Backup",
          color: "#28a745",
          description: "Save current data to localStorage",
        };
      case "restore_from_persistence":
        return {
          label: "📥 Restore from Backup",
          color: "#17a2b8",
          description: "Restore data from localStorage backup",
        };
      default:
        return {
          label: "Execute Action",
          color: "#007bff",
          description: "Execute this action",
        };
    }
  };

  const config = getButtonConfig();

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
      <h4 style={{ marginTop: 0, color: "#495057" }}>
        {endpoint.summary || config.label}
      </h4>
      <p style={{ color: "#6c757d", marginBottom: "15px" }}>
        {config.description}
      </p>
      <button
        onClick={handleClick}
        disabled={isExecuting}
        style={{
          backgroundColor: config.color,
          color: "white",
          border: "none",
          padding: "12px 24px",
          borderRadius: "4px",
          cursor: isExecuting ? "not-allowed" : "pointer",
          fontSize: "14px",
          fontWeight: "500",
          opacity: isExecuting ? 0.7 : 1,
        }}
      >
        {isExecuting ? "⏳ Processing..." : config.label}
      </button>
    </div>
  );
};
