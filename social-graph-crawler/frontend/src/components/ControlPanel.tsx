import React from 'react';

interface ControlPanelProps {
  onCrawlStart: (source: string, entity: string, depth: number) => void;
  onRefresh: () => void;
  loading: boolean;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  onCrawlStart,
  onRefresh,
  loading
}) => {
  const [source, setSource] = React.useState('reddit');
  const [entity, setEntity] = React.useState('');
  const [depth, setDepth] = React.useState(2);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (entity.trim()) {
      onCrawlStart(source, entity.trim(), depth);
    }
  };

  return (
    <div className="control-panel">
      <h2>Social Graph Crawler</h2>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="source">Data Source:</label>
          <select
            id="source"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            disabled={loading}
          >
            <option value="reddit">Reddit</option>
            <option value="github">GitHub</option>
            <option value="wikipedia">Wikipedia</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="entity">Starting Entity:</label>
          <input
            id="entity"
            type="text"
            value={entity}
            onChange={(e) => setEntity(e.target.value)}
            placeholder={
              source === 'reddit' ? 'subreddit name' :
              source === 'github' ? 'username or owner/repo' :
              'article title'
            }
            disabled={loading}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="depth">Crawl Depth:</label>
          <input
            id="depth"
            type="number"
            value={depth}
            onChange={(e) => setDepth(parseInt(e.target.value) || 1)}
            min="1"
            max="5"
            disabled={loading}
          />
        </div>

        <div className="button-group">
          <button type="submit" disabled={loading || !entity.trim()}>
            {loading ? 'Crawling...' : 'Start Crawl'}
          </button>
          <button type="button" onClick={onRefresh} disabled={loading}>
            Refresh Graph
          </button>
        </div>
      </form>

      <div className="help-text">
        <h3>Instructions:</h3>
        <ul>
          <li><strong>Reddit:</strong> Enter a subreddit name (e.g., "python")</li>
          <li><strong>GitHub:</strong> Enter username (e.g., "torvalds") or repo (e.g., "facebook/react")</li>
          <li><strong>Wikipedia:</strong> Enter article title (e.g., "Python_(programming_language)")</li>
        </ul>
      </div>
    </div>
  );
};

export default ControlPanel;
