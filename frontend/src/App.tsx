import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CrawlJob, GraphData, Node, getCrawlJob, listEdges, listNodes, startCrawl } from './services/api';
import { GraphVisualization } from './components/GraphVisualization';
import './App.css';

type View = 'explorer' | 'crawl';
type Source = 'mastodon' | 'github' | 'wikipedia' | 'fixture';

const SOURCE_INFO: Record<Source, { label: string; api: string; description: string; example: string }> = {
  mastodon: { label: 'Mastodon', api: 'Mastodon REST API', description: 'Public profiles and visible following relationships.', example: 'Gargron@mastodon.social' },
  github: { label: 'GitHub', api: 'GitHub REST API', description: 'Public users, repositories, contributors, and followers.', example: 'torvalds' },
  wikipedia: { label: 'Wikipedia', api: 'Wikipedia / MediaWiki API', description: 'Articles, article links, and categories.', example: 'Graph theory' },
  fixture: { label: 'Offline fixture', api: 'Development only', description: 'Deterministic local data for testing the pipeline.', example: 'v2-demo' },
};

const sourceColor = (source: string) => ({ mastodon: '#818cf8', github: '#cbd5e1', wikipedia: '#38bdf8', fixture: '#4ade80' }[source] || '#94a3b8');

function App() {
  const [view, setView] = useState<View>('explorer');
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [], metadata: {} });
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [source, setSource] = useState<Source>('mastodon');
  const [entity, setEntity] = useState('');
  const [depth, setDepth] = useState(2);
  const [maxEntities, setMaxEntities] = useState(100);
  const [filterSource, setFilterSource] = useState<'all' | Source>('all');
  const [filterRelationship, setFilterRelationship] = useState('all');
  const [search, setSearch] = useState('');
  const [hideIsolated, setHideIsolated] = useState(true);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [job, setJob] = useState<CrawlJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<number | null>(null);

  const loadGraphData = async () => {
    try {
      const [nodes, edges] = await Promise.all([listNodes(1, 500), listEdges(1, 500)]);
      setGraphData({ nodes: nodes.items, edges: edges.items, metadata: {} });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Could not load graph data.');
    }
  };

  useEffect(() => {
    loadGraphData();
    return () => { if (timerRef.current) window.clearInterval(timerRef.current); };
  }, []);

  const sourceCounts = useMemo(() => graphData.nodes.reduce<Record<string, number>>((acc, node) => ({ ...acc, [node.source]: (acc[node.source] || 0) + 1 }), {}), [graphData.nodes]);
  const relationshipTypes = useMemo(() => [...new Set(graphData.edges.map((edge) => edge.relationship_type))].sort(), [graphData.edges]);
  const filteredGraph = useMemo(() => {
    const query = search.trim().toLowerCase();
    const nodes = graphData.nodes.filter((node) => (filterSource === 'all' || node.source === filterSource) && (!query || `${node.display_name} ${node.entity_id}`.toLowerCase().includes(query)));
    const ids = new Set(nodes.map((node) => node.id));
    const edges = graphData.edges.filter((edge) => ids.has(edge.source_node_id) && ids.has(edge.target_node_id) && (filterRelationship === 'all' || edge.relationship_type === filterRelationship));
    const connected = new Set(edges.flatMap((edge) => [edge.source_node_id, edge.target_node_id]));
    return { nodes: hideIsolated ? nodes.filter((node) => connected.has(node.id)) : nodes, edges, metadata: {} };
  }, [filterSource, filterRelationship, graphData, hideIsolated, search]);

  const submitCrawl = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!entity.trim()) return;
    setError(null); setLoading(true);
    try {
      const created = await startCrawl({ source, start_entity: entity.trim(), depth, max_entities: maxEntities });
      setJob(created); setView('explorer');
      timerRef.current = window.setInterval(async () => {
        try {
          const latest = await getCrawlJob(created.id);
          setJob(latest);
          if (latest.status === 'completed' || latest.status === 'failed') {
            if (timerRef.current) window.clearInterval(timerRef.current);
            setLoading(false);
            if (latest.status === 'completed') await loadGraphData();
            if (latest.status === 'failed') setError(latest.error_message || 'The crawl failed.');
          }
        } catch { /* Preserve job state through temporary network errors. */ }
      }, 2000);
    } catch (err: any) { setError(err.response?.data?.detail || err.message || 'Could not start crawl.'); setLoading(false); }
  };

  const selectSeed = () => {
    if (!selectedNode) return;
    const metadata = selectedNode.metadata || {};
    setSource(selectedNode.source as Source);
    setEntity(String(metadata.handle || selectedNode.display_name).replace(/^@/, ''));
    setView('crawl');
  };

  const metadata = selectedNode?.metadata || {};
  return <div className="app-shell">
    <header className="topbar"><button className="brand" onClick={() => setView('explorer')}><b>✦</b> Social Graph Crawler <small>v1.4.2</small></button><div className="workspace-label">⌘ workspace / default</div><label className="global-search">⌕<input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search entities, jobs, handles…" /></label><div className="health-dot"><i /> API connected</div></header>
    <aside className="app-nav"><button className="primary-button nav-new" onClick={() => setView('crawl')}>＋ New Crawl</button><p>EXPLORATION</p><button className={view === 'explorer' ? 'nav-item active' : 'nav-item'} onClick={() => setView('explorer')}>⌘ Explore Graph</button><button className="nav-item" disabled>♧ Saved Views</button><p>OPERATIONS</p><button className="nav-item" onClick={() => setView('explorer')}>◷ Crawl History {job && <em>{job.status}</em>}</button><p>CONFIGURATION</p><button className="nav-item" disabled>⚿ Sources & Credentials</button><button className="nav-item" disabled>⚙ Workspace Settings</button><div className="nav-footer"><strong>Social Graph Crawler</strong><span>Public-data graph explorer</span><a href="/docs" target="_blank" rel="noreferrer">API documentation ↗</a></div></aside>
    <main className="workspace">
      {error && <div className="notice error"><b>!</b><span>{error}</span><button onClick={() => setError(null)}>×</button></div>}
      {job && <div className={`notice job-${job.status}`}><i /><span><strong>{job.source} crawl {job.status}</strong> · {job.start_entity} · {job.entity_count} entities · {job.edge_count} edges</span>{job.status === 'completed' && <button onClick={loadGraphData}>Refresh graph</button>}</div>}
      {view === 'explorer' ? <section className="explorer-view">
        <div className="graph-toolbar"><div className="source-filters"><button className={filterSource === 'all' ? 'selected' : ''} onClick={() => setFilterSource('all')}>All sources <b>{graphData.nodes.length}</b></button>{(['mastodon', 'github', 'wikipedia'] as Source[]).map((item) => <button key={item} className={filterSource === item ? 'selected' : ''} onClick={() => setFilterSource(item)}><i style={{ background: sourceColor(item) }} />{SOURCE_INFO[item].label}<b>{sourceCounts[item] || 0}</b></button>)}</div><label>Relationship <select value={filterRelationship} onChange={(e) => setFilterRelationship(e.target.value)}><option value="all">All relationships</option>{relationshipTypes.map((item) => <option key={item}>{item}</option>)}</select></label><label className="isolate-toggle"><input type="checkbox" checked={hideIsolated} onChange={(e) => setHideIsolated(e.target.checked)} /> Hide isolated accounts</label><button className="icon-button" onClick={loadGraphData}>↻</button></div>
        <div className="explorer-grid"><div className="graph-stage"><div className="graph-stage-header"><span>{filteredGraph.nodes.length ? `${filteredGraph.nodes.length} entities · ${filteredGraph.edges.length} relationships` : 'No graph results yet'}</span><button onClick={() => setView('crawl')}>＋ New crawl</button></div>{filteredGraph.nodes.length ? <GraphVisualization data={filteredGraph} onNodeClick={setSelectedNode} /> : <div className="graph-empty"><b>✦</b><h2>Explore a public network</h2><p>Start a Mastodon, GitHub, or Wikipedia crawl to build your graph.</p><button className="primary-button" onClick={() => setView('crawl')}>Start a crawl</button></div>}<div className="graph-legend"><span><i style={{ background: '#818cf8' }} /> Mastodon</span><span><i style={{ background: '#cbd5e1' }} /> GitHub</span><span><i style={{ background: '#38bdf8' }} /> Wikipedia</span></div></div>
        <aside className="details-panel">{selectedNode ? <><div className="entity-heading"><b style={{ borderColor: sourceColor(selectedNode.source), color: sourceColor(selectedNode.source) }}>{selectedNode.display_name.slice(0, 2).toUpperCase()}</b><div><h2>{selectedNode.display_name}</h2><p>{metadata.handle || selectedNode.entity_id}</p></div><button className="icon-button" onClick={() => setSelectedNode(null)}>×</button></div><div className="source-line"><i style={{ background: sourceColor(selectedNode.source) }} /> {SOURCE_INFO[selectedNode.source as Source]?.api || selectedNode.source} · {selectedNode.entity_type}</div><div className="detail-actions"><button className="primary-button" onClick={selectSeed}>Expand connections</button>{metadata.url && <a href={String(metadata.url)} target="_blank" rel="noreferrer">Open source ↗</a>}</div><h3>Node attributes</h3><dl className="attributes"><div><dt>Source</dt><dd>{selectedNode.source}</dd></div><div><dt>Entity type</dt><dd>{selectedNode.entity_type}</dd></div>{Object.entries(metadata).filter(([key]) => !['url', 'note', 'description', 'bio'].includes(key)).slice(0, 6).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : String(value)}</dd></div>)}</dl>{(metadata.note || metadata.description || metadata.bio) && <><h3>Bio / description</h3><p className="bio">{String(metadata.note || metadata.description || metadata.bio)}</p></>}</> : <div className="details-empty"><b>◎</b><h2>Select an entity</h2><p>Click any node to inspect its public metadata and relationships.</p></div>}</aside></div>
      </section> : <section className="crawl-view"><div className="page-heading"><div><p>workspace / jobs / new-crawl</p><h1>New Network Crawl</h1></div><span>Public-data crawl</span></div><div className="wizard-steps"><div className="done"><b>✓</b> Select source</div><div className="current"><b>2</b> Configure crawl</div><div><b>3</b> Review & start</div></div><form onSubmit={submitCrawl} className="crawl-form"><div className="crawl-main"><h2>1. Select target protocol & source</h2><div className="source-cards">{(['mastodon', 'github', 'wikipedia'] as Source[]).map((item) => <button type="button" key={item} className={source === item ? 'chosen' : ''} onClick={() => setSource(item)}><b style={{ color: sourceColor(item) }}>{item === 'mastodon' ? '@' : item === 'github' ? '◈' : '▤'}</b><strong>{SOURCE_INFO[item].label}</strong><small>{SOURCE_INFO[item].api}</small><p>{SOURCE_INFO[item].description}</p><em>Example: {SOURCE_INFO[item].example}</em></button>)}</div><button type="button" className="advanced-toggle" onClick={() => setAdvancedOpen(!advancedOpen)}>⌘ Advanced developer tools <span>{advancedOpen ? '⌃' : '⌄'}</span></button>{advancedOpen && <button type="button" className={source === 'fixture' ? 'fixture-option chosen' : 'fixture-option'} onClick={() => setSource('fixture')}>Use Offline Fixture — deterministic local crawl data</button>}<div className="settings-card"><div className="settings-heading"><h2>2. Crawl settings</h2><span>Format looks valid</span></div><label>Starting {source === 'mastodon' ? 'account handle' : source === 'github' ? 'entity' : source === 'wikipedia' ? 'article title' : 'fixture label'}<input required value={entity} onChange={(e) => setEntity(e.target.value)} placeholder={SOURCE_INFO[source].example} /><small>{source === 'mastodon' ? 'Use a full handle, such as Gargron@mastodon.social. Public visibility varies by instance.' : SOURCE_INFO[source].description}</small></label><div className="settings-row"><h3>Crawl depth</h3><span>Traversal radius</span></div><div className="depth-cards">{[1, 2, 3].map((item) => <button type="button" key={item} className={depth === item ? 'chosen' : ''} onClick={() => setDepth(item)}><strong>{item} Hop{item > 1 ? 's' : ''}</strong><small>{item === 1 ? 'Starting entity only.' : item === 2 ? 'Direct visible relationships.' : 'Expanded public network; may be larger.'}</small></button>)}</div><div className="settings-row"><h3>Entity limit</h3><span>Maximum nodes stored in this crawl</span></div><div className="limit-options">{[25, 100, 250].map((item) => <button type="button" key={item} className={maxEntities === item ? 'chosen' : ''} onClick={() => setMaxEntities(item)}>{item}{item === 100 ? ' (default)' : ''}</button>)}</div><div className="capability-notice"><b>Source capability notice</b><p>{source === 'mastodon' ? 'Mastodon collects public account data and visible following relationships. Hidden followers and non-public relationships are not collected.' : SOURCE_INFO[source].description}</p></div><div className="privacy-notice"><b>◉ Public data notice</b><p>This crawl uses public endpoints. Results depend on source availability, public visibility, and rate limits.</p></div></div></div><aside className="scope-card"><h2>Estimated crawl scope</h2><span>Approximate until crawl starts</span><p>Crawl size depends on public visibility, source limits, selected depth, and the entity limit.</p><dl><div><dt>Target source</dt><dd>{SOURCE_INFO[source].api}</dd></div><div><dt>Selected depth</dt><dd>{depth} hop{depth > 1 ? 's' : ''}</dd></div><div><dt>Entity limit</dt><dd>{maxEntities} nodes</dd></div><div><dt>Relationship mode</dt><dd>{source === 'mastodon' ? 'Visible following' : 'Source-aware'}</dd></div></dl><div className="scope-seed"><small>SEED TARGET</small><strong>{entity || SOURCE_INFO[source].example}</strong></div></aside><div className="wizard-footer"><button type="button" className="secondary-button" onClick={() => setView('explorer')}>Cancel</button><span>Review your settings, then begin the crawl.</span><button className="primary-button" disabled={loading || !entity.trim()}>{loading ? 'Starting…' : 'Review & Start Crawl →'}</button></div></form></section>}
    </main>
  </div>;
}

export default App;
