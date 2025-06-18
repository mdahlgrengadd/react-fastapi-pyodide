import React, { useState } from 'react';

import { PyodideEndpoint } from './index';

interface DeleteConfirmationProps {
  endpoint: PyodideEndpoint;
  onConfirm: () => Promise<void>;
  userId?: string;
}

const DeleteConfirmation: React.FunctionComponent<DeleteConfirmationProps> = ({
  endpoint,
  onConfirm,
  userId,
}) => {
  const [showConfirm, setShowConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  if (endpoint.method !== "DELETE") return null;

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onConfirm();
    } finally {
      setIsDeleting(false);
      setShowConfirm(false);
    }
  };

  return (
    <div
      style={{
        marginBottom: "20px",
        padding: "20px",
        backgroundColor: "#fff3cd",
        borderRadius: "8px",
        border: "1px solid #ffeaa7",
      }}
    >
      <h4 style={{ marginTop: 0, color: "#856404" }}>🗑️ Delete User</h4>
      {!showConfirm ? (
        <div>
          <p style={{ color: "#856404", marginBottom: "15px" }}>
            {userId ? `Delete user with ID: ${userId}` : "Delete this user"}
          </p>
          <button
            onClick={() => setShowConfirm(true)}
            style={{
              backgroundColor: "#dc3545",
              color: "white",
              border: "none",
              padding: "10px 20px",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: "500",
            }}
          >
            🗑️ Delete User
          </button>
        </div>
      ) : (
        <div>
          <p
            style={{
              color: "#721c24",
              marginBottom: "15px",
              fontWeight: "500",
            }}
          >
            ⚠️ Are you sure you want to delete this user? This action cannot be
            undone.
          </p>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              style={{
                backgroundColor: "#dc3545",
                color: "white",
                border: "none",
                padding: "8px 16px",
                borderRadius: "4px",
                cursor: isDeleting ? "not-allowed" : "pointer",
                fontSize: "14px",
              }}
            >
              {isDeleting ? "⏳ Deleting..." : "✅ Yes, Delete"}
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              disabled={isDeleting}
              style={{
                backgroundColor: "#6c757d",
                color: "white",
                border: "none",
                padding: "8px 16px",
                borderRadius: "4px",
                cursor: "pointer",
                fontSize: "14px",
              }}
            >
              ❌ Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeleteConfirmation;
