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
  const [source, setSource] = React.useState('wikipedia');
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
            <option value="mastodon">Mastodon</option>
            <option value="github">GitHub</option>
            <option value="wikipedia">Wikipedia</option>
            <option value="fixture">Offline fixture</option>
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
              source === 'mastodon' ? 'handle@instance (e.g., Gargron@mastodon.social)' :
              source === 'github' ? 'username or owner/repo' :
              source === 'wikipedia' ? 'article title' : 'v2-demo or a label'
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
          <li><strong>Mastodon:</strong> Enter a full handle (e.g., <code>Gargron@mastodon.social</code>). Public profiles and visible following relationships work without a key.</li>
          <li><strong>GitHub:</strong> Enter username (e.g., "torvalds") or repo (e.g., "facebook/react")</li>
          <li><strong>Wikipedia:</strong> Enter article title (e.g., "Python_(programming_language)")</li>
          <li><strong>Offline fixture:</strong> Use <code>v2-demo</code> to test retries and failures without a network connection.</li>
        </ul>
      </div>
    </div>
  );
};

export default ControlPanel;
