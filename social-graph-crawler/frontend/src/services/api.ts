import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Node {
  id: string;
  entity_type: string;
  entity_id: string;
  source: string;
  display_name: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Edge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  relationship_type: string;
  weight: number;
  metadata: Record<string, any>;
  created_at: string;
}

export interface GraphData {
  nodes: Node[];
  edges: Edge[];
  metadata: Record<string, any>;
}

export interface CrawlRequest {
  source: string;
  start_entity: string;
  depth: number;
  max_entities: number;
}

export interface CrawlJob {
  id: string;
  source: string;
  status: string;
  entity_count: number;
  edge_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

// Graph API
export const queryGraph = async (
  startNodeId: string,
  depth: number = 2,
  maxNodes: number = 100
): Promise<GraphData> => {
  const response = await api.post('/graph/query', {
    start_node_id: startNodeId,
    depth,
    max_nodes: maxNodes,
    direction: 'both',
  });
  return response.data;
};

export const getGraphStats = async () => {
  const response = await api.get('/graph/stats');
  return response.data;
};

// Node API
export const listNodes = async (
  page: number = 1,
  pageSize: number = 50,
  filters?: {
    entity_type?: string;
    source?: string;
    search?: string;
  }
): Promise<any> => {
  const response = await api.get('/nodes/', {
    params: {
      page,
      page_size: pageSize,
      ...filters,
    },
  });
  return response.data;
};

export const getNode = async (nodeId: string): Promise<Node> => {
  const response = await api.get(`/nodes/${nodeId}`);
  return response.data;
};

export const searchNodes = async (query: string, limit: number = 20): Promise<Node[]> => {
  const response = await api.get('/nodes/search/', {
    params: { q: query, limit },
  });
  return response.data;
};

// Crawler API
export const startCrawl = async (request: CrawlRequest): Promise<CrawlJob> => {
  const response = await api.post('/crawl/start', request);
  return response.data;
};

export const getCrawlJob = async (jobId: string): Promise<CrawlJob> => {
  const response = await api.get(`/crawl/jobs/${jobId}`);
  return response.data;
};

export const listCrawlJobs = async (
  page: number = 1,
  pageSize: number = 20
): Promise<CrawlJob[]> => {
  const response = await api.get('/crawl/jobs', {
    params: { page, page_size: pageSize },
  });
  return response.data;
};

// Health check
export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
