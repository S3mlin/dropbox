const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (res.status === 204) return null
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

export const api = {
  listNodes: (parentId) =>
    request(parentId != null ? `/nodes?parent_id=${parentId}` : '/nodes'),

  getPath: (nodeId) =>
    request(`/nodes/${nodeId}/path`),

  createFolder: (name, parentId) =>
    request('/nodes/folders', {
      method: 'POST',
      body: JSON.stringify({ name, parent_id: parentId }),
    }),

  createFile: (name, parentId) =>
    request('/nodes/files', {
      method: 'POST',
      body: JSON.stringify({ name, parent_id: parentId }),
    }),

  deleteNode: (nodeId) =>
    request(`/nodes/${nodeId}`, { method: 'DELETE' }),

  searchExact: (name, folderId = null) =>
    request(
      `/search?name=${encodeURIComponent(name)}` +
      (folderId != null ? `&folder_id=${folderId}` : '')
    ),

  autocomplete: (q) =>
    request(`/search/autocomplete?q=${encodeURIComponent(q)}`),
}