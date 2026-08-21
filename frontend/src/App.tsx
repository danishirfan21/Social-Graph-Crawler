import React, { useState, useEffect } from 'react';
import { GraphVisualization } from './components/GraphVisualization';
import { NodeDetails } from './components/NodeDetails';
import { ControlPanel } from './components/ControlPanel';
import { GraphData, Node, startCrawl, listNodes, getCrawlJob } from './services/api';
import './App.css';

function App() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [crawlStatus, setCrawlStatus] = useState<string>('');

  const handleCrawlStart = async (source: string, entity: string, depth: number) => {
    setLoading(true);
    setError(null);
    setCrawlStatus('Starting crawl...');

    try {
      const job = await startCrawl({
        source,
        start_entity: entity,
        depth,
        max_entities: 100,
      });

      setCrawlStatus(`Crawl job created: ${job.id}`);

      // Poll for job completion
      const pollInterval = setInterval(async () => {
        try {
          const jobStatus = await getCrawlJob(job.id);
          setCrawlStatus(`Status: ${jobStatus.status} | Nodes: ${jobStatus.entity_count} | Edges: ${jobStatus.edge_count}`);

          if (jobStatus.status === 'completed') {
            clearInterval(pollInterval);
            setCrawlStatus('Crawl completed! Loading graph...');
            await loadGraphData();
            setLoading(false);
          } else if (jobStatus.status === 'failed') {
            clearInterval(pollInterval);
            setError(jobStatus.error_message || 'Crawl failed');
            setLoading(false);
          }
        } catch (err) {
          console.error('Error polling job:', err);
        }
      }, 2000);

      // Timeout after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        if (loading) {
          setLoading(false);
          setCrawlStatus('Crawl timeout - check jobs manually');
        }
      }, 300000);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start crawl');
      setLoading(false);
    }
  };

  const loadGraphData = async () => {
    try {
      const response = await listNodes(1, 100);
      
      // Transform to graph format
      const nodes = response.items;
      const edges: any[] = [];
      
      // You might want to fetch actual edges here
      // For now, we're just showing nodes
      
      setGraphData({
        nodes,
        edges,
        metadata: {},
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load graph data');
    }
  };

  const handleRefresh = () => {
    loadGraphData();
  };

  useEffect(() => {
    loadGraphData();
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Social Graph Crawler & Visualizer</h1>
        {error && <div className="error-message">{error}</div>}
        {crawlStatus && <div className="status-message">{crawlStatus}</div>}
      </header>

      <div className="App-body">
        <aside className="sidebar">
          <ControlPanel
            onCrawlStart={handleCrawlStart}
            onRefresh={handleRefresh}
            loading={loading}
          />
        </aside>

        <main className="main-content">
          {graphData ? (
            <GraphVisualization
              data={graphData}
              onNodeClick={setSelectedNode}
            />
          ) : (
            <div className="empty-state">
              <p>No graph data available. Start a crawl to begin!</p>
            </div>
          )}
        </main>
      </div>

      <NodeDetails
        node={selectedNode}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}

export default App;
