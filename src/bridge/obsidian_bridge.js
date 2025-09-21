const express = require('express');
const cors = require('cors');
const fs = require('fs').promises;
const path = require('path');
const matter = require('gray-matter');
const { v4: uuidv4 } = require('uuid');
const axios = require('axios');

const app = express();
const PORT = process.env.BRIDGE_PORT || 3000;
const VAULT_PATH = process.env.VAULT_PATH || 'D:\\Knowledge-Vault';
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://localhost:8000';

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true }));

// Logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
  next();
});

// Utility functions
const getCurrentTimestamp = () =>
  new Date().toISOString().replace('T', ' ').replace(/\..+/, '');

const createFrontmatter = data => {
  const timestamp = getCurrentTimestamp();
  return {
    pake_id: data.pake_id || uuidv4(),
    created: data.created || timestamp,
    modified: timestamp,
    type: data.type || 'note',
    status: data.status || 'draft',
    confidence_score: data.confidence_score || 0.0,
    verification_status: data.verification_status || 'pending',
    source_uri: data.source_uri || 'local://api',
    tags: data.tags || [],
    connections: data.connections || [],
    ai_summary: data.ai_summary || '',
    human_notes: data.human_notes || '',
    ...data.customFields,
  };
};

const sanitizeFilename = title => {
  return title
    .replace(/[<>:"/\\|?*]/g, '-')
    .replace(/\s+/g, '-')
    .toLowerCase()
    .slice(0, 100);
};

const getFolderPath = (type, status) => {
  const folderMap = {
    daily: '01-Daily',
    project: '03-Projects',
    resource: '05-Resources',
    system: '02-Permanent',
  };

  if (status === 'draft') return '00-Inbox';
  if (status === 'verified') return '02-Permanent';
  if (status === 'archived') return '06-Archives';

  return folderMap[type] || '00-Inbox';
};

// API Endpoints

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    vault_path: VAULT_PATH,
    mcp_server: MCP_SERVER_URL,
  });
});

// Create new atomic note
app.post('/api/notes', async (req, res) => {
  try {
    const {
      title,
      content,
      type = 'note',
      source_uri = 'local://api',
      ...otherData
    } = req.body;

    if (!title || !content) {
      return res.status(400).json({
        error: 'Title and content are required',
      });
    }

    // Create frontmatter
    const frontmatter = createFrontmatter({
      type,
      source_uri,
      ...otherData,
    });

    // Create file content
    const noteContent = matter.stringify(content, frontmatter);

    // Generate filename
    const timestamp = new Date().toISOString().split('T')[0];
    const filename = `${timestamp}-${sanitizeFilename(title)}.md`;

    // Determine folder
    const folder = getFolderPath(type, frontmatter.status);
    const filepath = path.join(VAULT_PATH, folder, filename);

    // Ensure directory exists
    await fs.mkdir(path.dirname(filepath), { recursive: true });

    // Write file
    await fs.writeFile(filepath, noteContent, 'utf8');

    // Send to MCP server for processing
    try {
      const mcpPayload = {
        pake_id: frontmatter.pake_id,
        content: title + '\n\n' + content,
        confidence_score: frontmatter.confidence_score,
        metadata: {
          title,
          folder,
          filename,
          created_via: 'rest_api',
        },
        type,
        status: frontmatter.status,
        verification_status: frontmatter.verification_status,
        source_uri,
        tags: frontmatter.tags,
        connections: frontmatter.connections,
      };

      await axios.post(`${MCP_SERVER_URL}/ingest`, mcpPayload);
    } catch (mcpError) {
      console.warn('Failed to send to MCP server:', mcpError.message);
    }

    res.status(201).json({
      success: true,
      pake_id: frontmatter.pake_id,
      filepath: path.relative(VAULT_PATH, filepath),
      folder,
      filename,
    });
  } catch (error) {
    console.error('Error creating note:', error);
    res.status(500).json({
      error: 'Failed to create note',
      details: error.message,
    });
  }
});

// Get note by PAKE ID
app.get('/api/notes/:pake_id', async (req, res) => {
  try {
    const { pake_id } = req.params;
    const note = await findNoteByPakeId(pake_id);

    if (!note) {
      return res.status(404).json({ error: 'Note not found' });
    }

    res.json(note);
  } catch (error) {
    console.error('Error fetching note:', error);
    res.status(500).json({
      error: 'Failed to fetch note',
      details: error.message,
    });
  }
});

// Enhanced get note by ID function (PAKE MCP Tool)
app.get('/api/get_note_by_id', async (req, res) => {
  try {
    const { pake_id } = req.query;

    if (!pake_id) {
      return res.status(400).json({ error: 'pake_id parameter is required' });
    }

    const allFiles = await getAllMarkdownFiles();

    // Search for note with matching PAKE ID
    for (const filepath of allFiles) {
      try {
        const content = await fs.readFile(filepath, 'utf8');
        const parsed = matter(content);

        if (parsed.data.pake_id === pake_id) {
          const title =
            parsed.content.split('\n')[0].replace(/^#\s*/, '') || 'Untitled';

          return res.json({
            pake_id: parsed.data.pake_id,
            title: title,
            content: parsed.content,
            metadata: {
              type: parsed.data.type,
              status: parsed.data.status,
              confidence_score: parsed.data.confidence_score,
              verification_status: parsed.data.verification_status,
              source_uri: parsed.data.source_uri,
              tags: parsed.data.tags || [],
              connections: parsed.data.connections || [],
              ai_summary: parsed.data.ai_summary || '',
              human_notes: parsed.data.human_notes || '',
              created: parsed.data.created,
              modified: parsed.data.modified,
              ...parsed.data.customFields,
            },
            filepath: path.relative(VAULT_PATH, filepath),
          });
        }
      } catch (error) {
        console.warn(`Error processing file ${filepath}:`, error.message);
        continue;
      }
    }

    return res.status(404).json({ error: 'Note not found' });
  } catch (error) {
    console.error('Error in get_note_by_id:', error);
    res.status(500).json({
      error: 'Failed to retrieve note',
      details: error.message,
    });
  }
});

// Update note
app.patch('/api/notes/:pake_id', async (req, res) => {
  try {
    const { pake_id } = req.params;
    const updates = req.body;

    const noteInfo = await findNoteByPakeId(pake_id);
    if (!noteInfo) {
      return res.status(404).json({ error: 'Note not found' });
    }

    // Read current content
    const currentContent = await fs.readFile(noteInfo.filepath, 'utf8');
    const parsed = matter(currentContent);

    // Update frontmatter
    const updatedData = {
      ...parsed.data,
      ...updates,
      modified: getCurrentTimestamp(),
    };

    // Update content if provided
    const newContent = updates.content || parsed.content;

    // Write updated file
    const updatedFile = matter.stringify(newContent, updatedData);
    await fs.writeFile(noteInfo.filepath, updatedFile, 'utf8');

    // Update MCP server
    try {
      const mcpPayload = {
        pake_id,
        content: newContent,
        confidence_score: updatedData.confidence_score,
        metadata: updatedData,
        type: updatedData.type,
        status: updatedData.status,
        verification_status: updatedData.verification_status,
        source_uri: updatedData.source_uri,
        tags: updatedData.tags,
        connections: updatedData.connections,
      };

      await axios.post(`${MCP_SERVER_URL}/ingest`, mcpPayload);
    } catch (mcpError) {
      console.warn('Failed to update MCP server:', mcpError.message);
    }

    res.json({
      success: true,
      pake_id,
      updated_fields: Object.keys(updates),
    });
  } catch (error) {
    console.error('Error updating note:', error);
    res.status(500).json({
      error: 'Failed to update note',
      details: error.message,
    });
  }
});

// Query notes by confidence score
app.get('/api/notes/confidence/:threshold', async (req, res) => {
  try {
    const threshold = parseFloat(req.params.threshold);
    const { limit = 50, order = 'desc' } = req.query;

    if (isNaN(threshold) || threshold < 0 || threshold > 1) {
      return res.status(400).json({
        error: 'Threshold must be between 0 and 1',
      });
    }

    const notes = await queryNotesByConfidence(
      threshold,
      parseInt(limit),
      order
    );
    res.json({ notes, count: notes.length });
  } catch (error) {
    console.error('Error querying notes:', error);
    res.status(500).json({
      error: 'Failed to query notes',
      details: error.message,
    });
  }
});

// Update verification status
app.patch('/api/notes/:pake_id/verify', async (req, res) => {
  try {
    const { pake_id } = req.params;
    const { verification_status, human_notes = '' } = req.body;

    const validStatuses = ['pending', 'verified', 'rejected'];
    if (!validStatuses.includes(verification_status)) {
      return res.status(400).json({
        error: `Invalid verification status. Must be one of: ${validStatuses.join(', ')}`,
      });
    }

    const updates = {
      verification_status,
      human_notes,
      modified: getCurrentTimestamp(),
    };

    // If verifying, potentially move to permanent folder
    if (verification_status === 'verified') {
      updates.status = 'verified';
    }

    const result = await updateNoteByPakeId(pake_id, updates);

    if (!result.success) {
      return res.status(404).json({ error: 'Note not found' });
    }

    res.json({
      success: true,
      pake_id,
      verification_status,
      message: `Note ${verification_status} successfully`,
    });
  } catch (error) {
    console.error('Error updating verification:', error);
    res.status(500).json({
      error: 'Failed to update verification',
      details: error.message,
    });
  }
});

// Search notes with enhanced metadata filtering
app.post('/api/search', async (req, res) => {
  try {
    const {
      query,
      sources = ['web', 'arxiv', 'pubmed'],
      maxResults = 20,
    } = req.body;

    if (!query || query.trim().length === 0) {
      return res.status(400).json({ error: 'Search query is required' });
    }

    console.log(`[RESEARCH] Starting multi-source search for: ${query}`);
    const startTime = Date.now();

    // Try MCP server first for enhanced results
    try {
      const searchPayload = {
        query: query.trim(),
        limit: parseInt(maxResults),
        confidence_threshold: 0.0,
        semantic_search: true,
        sources: sources,
      };

      const mcpResponse = await axios.post(
        `${MCP_SERVER_URL}/search`,
        searchPayload
      );

      if (mcpResponse.data && mcpResponse.data.results) {
        const processingTime = Date.now() - startTime;
        console.log(`[RESEARCH] MCP search completed in ${processingTime}ms`);

        return res.json({
          success: true,
          query: query.trim(),
          results: mcpResponse.data.results.map(result => ({
            id: result.id || Date.now().toString() + Math.random().toString(36),
            title: result.title || 'Untitled',
            content: result.content || result.description || '',
            source: result.source || 'web',
            url: result.url || result.source_url,
            authors: result.authors || [],
            publishedDate: result.published_date || result.date,
            confidence: result.confidence || result.quality_score,
            metadata: result.metadata || {},
          })),
          metrics: {
            totalResults: mcpResponse.data.results.length,
            processingTime,
            sourcesQueried: sources.length,
          },
        });
      }
    } catch (mcpError) {
      console.warn(
        '[RESEARCH] MCP server not available, using fallback search'
      );
    }

    // Fallback: Return demo results that simulate our pipeline
    const demoResults = [
      {
        id: '1',
        title: `Research Results for: ${query}`,
        content: `This is a demo result showing how the multi-source research pipeline would work. The system searched across ${sources.join(', ')} for relevant information about "${query}".`,
        source: 'web',
        url: 'https://example.com/research',
        confidence: 0.85,
        metadata: { demo: true },
      },
      {
        id: '2',
        title: `Academic Paper: ${query} Analysis`,
        content: `Academic research paper discussing various aspects of ${query}. This would typically come from ArXiv or similar academic databases.`,
        source: 'arxiv',
        url: 'https://arxiv.org/abs/demo',
        authors: ['Dr. Research', 'Prof. Science'],
        publishedDate: new Date().toISOString(),
        confidence: 0.92,
        metadata: { demo: true, type: 'academic' },
      },
      {
        id: '3',
        title: `Biomedical Study: ${query}`,
        content: `Medical research findings related to ${query}. This demonstrates how PubMed integration would provide biomedical literature results.`,
        source: 'pubmed',
        url: 'https://pubmed.ncbi.nlm.nih.gov/demo',
        authors: ['Medical Researcher', 'Clinical Specialist'],
        publishedDate: new Date(Date.now() - 86400000).toISOString(),
        confidence: 0.78,
        metadata: { demo: true, type: 'medical' },
      },
    ].filter(result => sources.includes(result.source));

    const processingTime = Date.now() - startTime;
    console.log(`[RESEARCH] Demo search completed in ${processingTime}ms`);

    return res.json({
      success: true,
      query: query.trim(),
      results: demoResults,
      metrics: {
        totalResults: demoResults.length,
        processingTime,
        sourcesQueried: sources.length,
      },
      note: 'Demo results - connect MCP server for live data',
    });
  } catch (error) {
    console.error('Error searching notes:', error);
    res.status(500).json({
      error: 'Search failed',
      details: error.message,
    });
  }
});

// Enhanced metadata-based search function (PAKE MCP Tool)
app.post('/api/search_notes', async (req, res) => {
  try {
    const { filters = {} } = req.body;

    const results = [];
    const allFiles = await getAllMarkdownFiles();

    for (const filepath of allFiles) {
      try {
        const content = await fs.readFile(filepath, 'utf8');
        const parsed = matter(content);
        const metadata = parsed.data;

        // Check if note matches all metadata filters
        const matchesFilters = Object.entries(filters).every(([key, value]) => {
          if (!metadata[key]) return false;

          // Handle array fields (tags, connections)
          if (Array.isArray(metadata[key])) {
            if (Array.isArray(value)) {
              return value.some(v => metadata[key].includes(v));
            }
            return metadata[key].includes(value);
          }

          // Handle exact matches
          return metadata[key] === value;
        });

        if (matchesFilters) {
          const title =
            parsed.content.split('\n')[0].replace(/^#\s*/, '') || 'Untitled';
          results.push({
            pake_id: metadata.pake_id,
            title: title,
            summary:
              metadata.ai_summary || parsed.content.substring(0, 200) + '...',
            pake_type: metadata.type,
            confidence_score: metadata.confidence_score,
            status: metadata.status,
            verification_status: metadata.verification_status,
            tags: metadata.tags || [],
            filepath: path.relative(VAULT_PATH, filepath),
            created: metadata.created,
            modified: metadata.modified,
          });
        }
      } catch (error) {
        console.warn(`Error processing file ${filepath}:`, error.message);
        continue;
      }
    }

    // Sort by confidence score (descending) and creation date
    results.sort((a, b) => {
      const confidenceDiff =
        (b.confidence_score || 0) - (a.confidence_score || 0);
      if (confidenceDiff !== 0) return confidenceDiff;
      return new Date(b.created || 0) - new Date(a.created || 0);
    });

    res.json(results);
  } catch (error) {
    console.error('Error in metadata search:', error);
    res.status(500).json({
      error: 'Metadata search failed',
      details: error.message,
    });
  }
});

// List notes with pagination
app.get('/api/notes', async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      type,
      status,
      verification_status,
      sort_by = 'modified',
      order = 'desc',
    } = req.query;

    const offset = (parseInt(page) - 1) * parseInt(limit);
    const results = await listNotes({
      limit: parseInt(limit),
      offset,
      type,
      status,
      verification_status,
      sort_by,
      order,
    });

    res.json(results);
  } catch (error) {
    console.error('Error listing notes:', error);
    res.status(500).json({
      error: 'Failed to list notes',
      details: error.message,
    });
  }
});

// Create connection between notes
app.post('/api/connections', async (req, res) => {
  try {
    const { source_id, target_id, connection_type = 'relates_to' } = req.body;

    if (!source_id || !target_id) {
      return res.status(400).json({
        error: 'source_id and target_id are required',
      });
    }

    // Update both notes to add the connection
    const sourceUpdate = await addConnectionToNote(source_id, target_id);
    const targetUpdate = await addConnectionToNote(target_id, source_id);

    if (!sourceUpdate.success || !targetUpdate.success) {
      return res.status(404).json({ error: 'One or both notes not found' });
    }

    // Notify MCP server
    try {
      await axios.post(`${MCP_SERVER_URL}/connect`, {
        source_id,
        target_id,
        connection_type,
      });
    } catch (mcpError) {
      console.warn(
        'Failed to notify MCP server of connection:',
        mcpError.message
      );
    }

    res.json({
      success: true,
      message: 'Connection created successfully',
      source_id,
      target_id,
      connection_type,
    });
  } catch (error) {
    console.error('Error creating connection:', error);
    res.status(500).json({
      error: 'Failed to create connection',
      details: error.message,
    });
  }
});

// Statistics endpoint
app.get('/api/stats', async (req, res) => {
  try {
    const stats = await getVaultStatistics();
    res.json(stats);
  } catch (error) {
    console.error('Error getting statistics:', error);
    res.status(500).json({
      error: 'Failed to get statistics',
      details: error.message,
    });
  }
});

// Helper functions
async function findNoteByPakeId(pakeId) {
  const allFiles = await getAllMarkdownFiles();

  for (const filepath of allFiles) {
    try {
      const content = await fs.readFile(filepath, 'utf8');
      const parsed = matter(content);

      if (parsed.data.pake_id === pakeId) {
        return {
          ...parsed.data,
          content: parsed.content,
          filepath,
          relative_path: path.relative(VAULT_PATH, filepath),
        };
      }
    } catch (error) {
      console.warn(`Error reading file ${filepath}:`, error.message);
    }
  }

  return null;
}

async function getAllMarkdownFiles() {
  const files = [];

  async function walkDir(dir) {
    const items = await fs.readdir(dir, { withFileTypes: true });

    for (const item of items) {
      const fullPath = path.join(dir, item.name);

      if (item.isDirectory() && !item.name.startsWith('.')) {
        await walkDir(fullPath);
      } else if (item.isFile() && item.name.endsWith('.md')) {
        files.push(fullPath);
      }
    }
  }

  await walkDir(VAULT_PATH);
  return files;
}

async function queryNotesByConfidence(threshold, limit, order) {
  const allFiles = await getAllMarkdownFiles();
  const notes = [];

  for (const filepath of allFiles) {
    try {
      const content = await fs.readFile(filepath, 'utf8');
      const parsed = matter(content);

      if (parsed.data.confidence_score !== undefined) {
        const score = parseFloat(parsed.data.confidence_score);
        if (score >= threshold) {
          notes.push({
            pake_id: parsed.data.pake_id,
            confidence_score: score,
            title: parsed.content.split('\n')[0].replace(/^#\s*/, ''),
            type: parsed.data.type,
            status: parsed.data.status,
            modified: parsed.data.modified,
            relative_path: path.relative(VAULT_PATH, filepath),
          });
        }
      }
    } catch (error) {
      console.warn(`Error processing file ${filepath}:`, error.message);
    }
  }

  // Sort by confidence score
  notes.sort((a, b) => {
    if (order === 'desc') {
      return b.confidence_score - a.confidence_score;
    } else {
      return a.confidence_score - b.confidence_score;
    }
  });

  return notes.slice(0, limit);
}

async function updateNoteByPakeId(pakeId, updates) {
  const noteInfo = await findNoteByPakeId(pakeId);
  if (!noteInfo) {
    return { success: false, error: 'Note not found' };
  }

  try {
    const content = await fs.readFile(noteInfo.filepath, 'utf8');
    const parsed = matter(content);

    const updatedData = {
      ...parsed.data,
      ...updates,
    };

    const updatedFile = matter.stringify(parsed.content, updatedData);
    await fs.writeFile(noteInfo.filepath, updatedFile, 'utf8');

    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function addConnectionToNote(noteId, targetId) {
  const noteInfo = await findNoteByPakeId(noteId);
  if (!noteInfo) {
    return { success: false, error: 'Note not found' };
  }

  try {
    const connections = noteInfo.connections || [];
    if (!connections.includes(targetId)) {
      connections.push(targetId);

      return await updateNoteByPakeId(noteId, {
        connections,
        modified: getCurrentTimestamp(),
      });
    }

    return { success: true }; // Connection already exists
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function searchNotesLocal(query, filters, limit) {
  const allFiles = await getAllMarkdownFiles();
  const results = [];
  const searchRegex = new RegExp(query, 'gi');

  for (const filepath of allFiles) {
    try {
      const content = await fs.readFile(filepath, 'utf8');
      const parsed = matter(content);

      // Apply filters
      if (filters.type && parsed.data.type !== filters.type) continue;
      if (filters.status && parsed.data.status !== filters.status) continue;
      if (
        filters.min_confidence &&
        parsed.data.confidence_score < filters.min_confidence
      )
        continue;

      // Search in content and title
      const fullText = parsed.content;
      if (searchRegex.test(fullText)) {
        const title = fullText.split('\n')[0].replace(/^#\s*/, '');
        results.push({
          pake_id: parsed.data.pake_id,
          title,
          confidence_score: parsed.data.confidence_score,
          type: parsed.data.type,
          snippet: fullText.substring(0, 200) + '...',
          relative_path: path.relative(VAULT_PATH, filepath),
        });
      }
    } catch (error) {
      console.warn(`Error searching file ${filepath}:`, error.message);
    }
  }

  return results.slice(0, limit);
}

async function listNotes(options) {
  const allFiles = await getAllMarkdownFiles();
  const notes = [];

  for (const filepath of allFiles) {
    try {
      const content = await fs.readFile(filepath, 'utf8');
      const parsed = matter(content);

      // Apply filters
      if (options.type && parsed.data.type !== options.type) continue;
      if (options.status && parsed.data.status !== options.status) continue;
      if (
        options.verification_status &&
        parsed.data.verification_status !== options.verification_status
      )
        continue;

      const title = parsed.content.split('\n')[0].replace(/^#\s*/, '');
      notes.push({
        pake_id: parsed.data.pake_id,
        title,
        type: parsed.data.type,
        status: parsed.data.status,
        confidence_score: parsed.data.confidence_score,
        verification_status: parsed.data.verification_status,
        created: parsed.data.created,
        modified: parsed.data.modified,
        tags: parsed.data.tags,
        connections_count: (parsed.data.connections || []).length,
        relative_path: path.relative(VAULT_PATH, filepath),
      });
    } catch (error) {
      console.warn(`Error processing file ${filepath}:`, error.message);
    }
  }

  // Sort notes
  notes.sort((a, b) => {
    const aVal = a[options.sort_by] || '';
    const bVal = b[options.sort_by] || '';

    if (options.order === 'desc') {
      return bVal > aVal ? 1 : -1;
    } else {
      return aVal > bVal ? 1 : -1;
    }
  });

  const total = notes.length;
  const paginatedNotes = notes.slice(
    options.offset,
    options.offset + options.limit
  );

  return {
    notes: paginatedNotes,
    pagination: {
      total,
      page: Math.floor(options.offset / options.limit) + 1,
      limit: options.limit,
      pages: Math.ceil(total / options.limit),
    },
  };
}

async function getVaultStatistics() {
  const allFiles = await getAllMarkdownFiles();
  const stats = {
    total_notes: 0,
    by_type: {},
    by_status: {},
    by_verification: {},
    confidence_distribution: {
      excellent: 0, // 0.9-1.0
      high: 0, // 0.7-0.9
      medium: 0, // 0.5-0.7
      low: 0, // 0.3-0.5
      poor: 0, // 0.0-0.3
    },
    avg_confidence: 0,
    total_connections: 0,
    most_connected: [],
    recent_activity: [],
  };

  const confidenceScores = [];
  const connectionCounts = [];
  const recentNotes = [];

  for (const filepath of allFiles) {
    try {
      const content = await fs.readFile(filepath, 'utf8');
      const parsed = matter(content);
      const data = parsed.data;

      stats.total_notes++;

      // By type
      stats.by_type[data.type] = (stats.by_type[data.type] || 0) + 1;

      // By status
      stats.by_status[data.status] = (stats.by_status[data.status] || 0) + 1;

      // By verification
      stats.by_verification[data.verification_status] =
        (stats.by_verification[data.verification_status] || 0) + 1;

      // Confidence distribution
      const score = parseFloat(data.confidence_score) || 0;
      confidenceScores.push(score);

      if (score >= 0.9) stats.confidence_distribution.excellent++;
      else if (score >= 0.7) stats.confidence_distribution.high++;
      else if (score >= 0.5) stats.confidence_distribution.medium++;
      else if (score >= 0.3) stats.confidence_distribution.low++;
      else stats.confidence_distribution.poor++;

      // Connections
      const connections = data.connections || [];
      stats.total_connections += connections.length;
      connectionCounts.push({
        pake_id: data.pake_id,
        count: connections.length,
        title: parsed.content.split('\n')[0].replace(/^#\s*/, ''),
      });

      // Recent activity
      if (data.modified) {
        recentNotes.push({
          pake_id: data.pake_id,
          title: parsed.content.split('\n')[0].replace(/^#\s*/, ''),
          modified: data.modified,
          type: data.type,
        });
      }
    } catch (error) {
      console.warn(
        `Error processing file ${filepath} for stats:`,
        error.message
      );
    }
  }

  // Calculate averages
  if (confidenceScores.length > 0) {
    stats.avg_confidence =
      confidenceScores.reduce((a, b) => a + b, 0) / confidenceScores.length;
  }

  // Most connected notes
  stats.most_connected = connectionCounts
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  // Recent activity
  stats.recent_activity = recentNotes
    .sort((a, b) => new Date(b.modified) - new Date(a.modified))
    .slice(0, 10);

  return stats;
}

// Start server
app.listen(PORT, () => {
  console.log(`PAKE+ Obsidian Bridge API running on port ${PORT}`);
  console.log(`Vault path: ${VAULT_PATH}`);
  console.log(`MCP server: ${MCP_SERVER_URL}`);
  console.log('API endpoints:');
  console.log('  GET  /health');
  console.log('  POST /api/notes');
  console.log('  GET  /api/notes/:pake_id');
  console.log('  PATCH /api/notes/:pake_id');
  console.log('  POST /api/search');
  console.log('  GET  /api/stats');
});

module.exports = app;
