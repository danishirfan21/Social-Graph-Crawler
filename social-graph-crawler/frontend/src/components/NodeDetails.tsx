import React from 'react';
import { Node } from '../services/api';

interface NodeDetailsProps {
  node: Node | null;
  onClose: () => void;
}

export const NodeDetails: React.FC<NodeDetailsProps> = ({ node, onClose }) => {
  if (!node) return null;

  return (
    <div className="node-details-overlay" onClick={onClose}>
      <div className="node-details-panel" onClick={(e) => e.stopPropagation()}>
        <div className="node-details-header">
          <h3>{node.display_name}</h3>
          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="node-details-body">
          <div className="detail-row">
            <span className="label">Type:</span>
            <span className="value">{node.entity_type}</span>
          </div>

          <div className="detail-row">
            <span className="label">Source:</span>
            <span className="value badge badge-{node.source}">{node.source}</span>
          </div>

          <div className="detail-row">
            <span className="label">Entity ID:</span>
            <span className="value code">{node.entity_id}</span>
          </div>

          <div className="detail-row">
            <span className="label">Created:</span>
            <span className="value">
              {new Date(node.created_at).toLocaleString()}
            </span>
          </div>

          {node.metadata && Object.keys(node.metadata).length > 0 && (
            <>
              <h4>Metadata</h4>
              <div className="metadata">
                {Object.entries(node.metadata).map(([key, value]) => (
                  <div key={key} className="detail-row">
                    <span className="label">{key}:</span>
                    <span className="value">
                      {typeof value === 'object'
                        ? JSON.stringify(value, null, 2)
                        : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="node-details-footer">
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default NodeDetails;
