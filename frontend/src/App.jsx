import { useState, useEffect, useRef, useCallback, Fragment } from 'react'
import { api } from './api.js'


function Card({ node, onOpen, onDelete }) {
  const isFolder = node.type === 'folder'
  return (
    <div
      className={`card ${isFolder ? 'folder' : ''}`}
      onClick={() => isFolder && onOpen(node.id)}
    >
      <span className="card-icon">{isFolder ? '📁' : '📄'}</span>
      <span className="card-name" title={node.name}>{node.name}</span>
      <button
        className="card-del"
        title={`Delete ${node.name}`}
        onClick={(e) => {
          e.stopPropagation()
          onDelete(node)
        }}
      >
        ✕
      </button>
    </div>
  )
}

function Modal({ title, onClose, onConfirm }) {
  const [name,    setName]    = useState('')
  const [error,   setError]   = useState('')
  const [loading, setLoading] = useState(false)
  const inputRef = useRef(null)


  useEffect(() => { inputRef.current?.focus() }, [])

  async function submit() {
    const trimmed = name.trim()
    if (!trimmed) { setError('Name is required'); return }
    setError('')
    setLoading(true)
    try {
      await onConfirm(trimmed)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div
      className="overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="modal">
        <h3>{title}</h3>
        <div className="modal-body">
          <input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter')  submit()
              if (e.key === 'Escape') onClose()
            }}
            placeholder="Enter name…"
            disabled={loading}
          />
          <p className="field-error">{error}</p>
        </div>
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={onClose}  disabled={loading}>Cancel</button>
          <button className="btn btn-primary" onClick={submit}   disabled={loading}>
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [folderId, setFolderId] = useState(null)
  const [nodes,    setNodes]    = useState([])
  const [crumbs,   setCrumbs]   = useState([])
  const [loading,  setLoading]  = useState(false)

  const [searchMode,  setSearchMode]  = useState(null)
  const [query,       setQuery]       = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showDrop,    setShowDrop]    = useState(false)

  const [modal, setModal] = useState(null)

  const debounce = useRef(null)

  const loadFolder = useCallback(async (id) => {
    setLoading(true)
    setSearchMode(null)
    setQuery('')
    setSuggestions([])
    setShowDrop(false)
    try {
      const [newNodes, path] = await Promise.all([
        api.listNodes(id),
        id != null ? api.getPath(id) : Promise.resolve([]),
      ])
      setFolderId(id)
      setNodes(newNodes)
      setCrumbs(path)
    } catch (err) {
      alert(`Failed to load: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadFolder(null) }, [loadFolder])

  function handleQueryChange(e) {
    const q = e.target.value
    setQuery(q)
    clearTimeout(debounce.current)
    if (!q.trim()) { setSuggestions([]); setShowDrop(false); return }

    debounce.current = setTimeout(async () => {
      try {
        const results = await api.autocomplete(q.trim())
        setSuggestions(results)
        setShowDrop(results.length > 0 || q.trim().length > 0)
      } catch { /* autocomplete failure is non-critical — fail silently */ }
    }, 220)
  }

  async function runExactSearch(q = query) {
    if (!q.trim()) return
    clearTimeout(debounce.current)
    setShowDrop(false)
    try {
      const results = await api.searchExact(q.trim())
      setSearchMode({ query: q.trim(), results })
    } catch (err) {
      alert(`Search failed: ${err.message}`)
    }
  }


  async function handleDelete(node) {
    const msg = node.type === 'folder'
      ? `Delete folder "${node.name}" and all its contents?`
      : `Delete "${node.name}"?`
    if (!window.confirm(msg)) return

    try {
      await api.deleteNode(node.id)
      if (searchMode) {
        setSearchMode((prev) => ({
          ...prev,
          results: prev.results.filter((n) => n.id !== node.id),
        }))
      } else {
        await loadFolder(folderId)
      }
    } catch (err) {
      alert(`Delete failed: ${err.message}`)
    }
  }


  async function handleCreate(name) {
    await modal.action(name)
    setModal(null)
    await loadFolder(folderId)
  }

  const inSearch     = searchMode !== null
  const visibleNodes = inSearch ? searchMode.results : nodes
  const isAtRoot     = crumbs.length === 0 && !inSearch

  return (
    <>
      {/* ── Header ── */}
      <header className="header">
        <span className="logo">🗂 FileSystem</span>

        <div className="search-wrap">
          <input
            type="search"
            className="search-input"
            placeholder="Search files…"
            value={query}
            onChange={handleQueryChange}
            onKeyDown={(e) => {
              if (e.key === 'Enter')  runExactSearch()
              if (e.key === 'Escape') setShowDrop(false)
            }}
            onBlur={() => setTimeout(() => setShowDrop(false), 150)}
            autoComplete="off"
          />

          {showDrop && (
            <div className="dropdown">
              {suggestions.length === 0
                ? <div className="dd-empty">No files starting with "{query}"</div>
                : suggestions.map((node) => (
                    <button
                      key={node.id}
                      className="dd-row"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        setShowDrop(false)
                        setQuery('')
                        loadFolder(node.parent_id)
                      }}
                    >
                      📄
                      <span>
                        {/* Bold the matched prefix, plain text for the rest */}
                        <strong>{node.name.slice(0, query.length)}</strong>
                        {node.name.slice(query.length)}
                      </span>
                    </button>
                  ))
              }
              <div className="dd-divider" />
              <button
                className="dd-all"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => runExactSearch()}
              >
                🔍 Search all for "<strong>{query}</strong>"
              </button>
            </div>
          )}
        </div>
      </header>

      {/* ── Toolbar ── */}
      <div className="toolbar">
        <nav className="crumbs">
          <button
            className={`crumb${isAtRoot ? ' active' : ''}`}
            onClick={() => loadFolder(null)}
            disabled={isAtRoot}
          >
            🏠 Home
          </button>

          {/* Each folder in the path gets a separator + clickable crumb.
              Fragment with key avoids adding a wrapper DOM element. */}
          {crumbs.map((c, i) => {
            const isLast = i === crumbs.length - 1
            const active = isLast && !inSearch
            return (
              <Fragment key={c.id}>
                <span className="sep">›</span>
                <button
                  className={`crumb${active ? ' active' : ''}`}
                  onClick={() => loadFolder(c.id)}
                  disabled={active}
                >
                  {c.name}
                </button>
              </Fragment>
            )
          })}

          {/* In search mode, add the search query as a non-clickable final crumb */}
          {inSearch && (
            <Fragment>
              <span className="sep">›</span>
              <span className="crumb active">🔍 "{searchMode.query}"</span>
            </Fragment>
          )}
        </nav>

        {!inSearch ? (
          <>
            <button
              className="btn btn-outline"
              onClick={() => setModal({
                title:  '📁 New Folder',
                action: (name) => api.createFolder(name, folderId),
              })}
            >
              📁 New Folder
            </button>
            <button
              className="btn btn-primary"
              onClick={() => setModal({
                title:  '📄 New File',
                action: (name) => api.createFile(name, folderId),
              })}
            >
              📄 New File
            </button>
          </>
        ) : (
          <button className="btn btn-outline" onClick={() => loadFolder(folderId)}>
            ✕ Clear search
          </button>
        )}
      </div>

      {/* ── Content ── */}
      <main className="content">
        {inSearch && (
          <div className="status">
            <span>
              <strong>{searchMode.results.length}</strong>{' '}
              result{searchMode.results.length !== 1 ? 's' : ''} for{' '}
              "<strong>{searchMode.query}</strong>"
            </span>
            <button className="btn btn-outline" onClick={() => loadFolder(folderId)}>
              ✕ Clear
            </button>
          </div>
        )}

        <div className="grid">
          {loading
            ? <div className="empty">Loading…</div>
            : visibleNodes.length === 0
              ? <div className="empty">
                  {inSearch ? 'No results found.' : 'This folder is empty.'}
                </div>
              : visibleNodes.map((node) => (
                  <Card
                    key={node.id}
                    node={node}
                    onOpen={loadFolder}
                    onDelete={handleDelete}
                  />
                ))
          }
        </div>
      </main>

      {/* Modal mounts only when needed. Unmounting resets its state for free. */}
      {modal && (
        <Modal
          title={modal.title}
          onClose={() => setModal(null)}
          onConfirm={handleCreate}
        />
      )}
    </>
  )
}