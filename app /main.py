const express = require('express');
const axios = require('axios');
const rateLimit = require('express-rate-limit');

const app = express();
app.use(express.json());

// Configuration
const CONFIG = {
  UPSTREAM_API_URL: process.env.UPSTREAM_API_URL || 'http://localhost:3000',
  PORT: process.env.PORT || 8080,
  API_KEYS: {
    'demo_free_key': { plan: 'free', limit: 100 },
    'demo_basic_key': { plan: 'basic', limit: 1000 },
    'demo_pro_key': { plan: 'pro', limit: 10000 },
    'demo_enterprise_key': { plan: 'enterprise', limit: -1 } // unlimited
  }
};

// In-memory usage tracking (use Redis in production)
const usageTracker = new Map();

// Middleware: API Key Validation
const validateApiKey = (req, res, next) => {
  const apiKey = req.headers['x-api-key'] || req.query.api_key;
  
  if (!apiKey) {
    return res.status(401).json({
      success: false,
      error: {
        code: 'MISSING_API_KEY',
        message: 'API key is required. Include it in X-API-Key header or api_key query parameter.'
      }
    });
  }

  const keyData = CONFIG.API_KEYS[apiKey];
  if (!keyData) {
    return res.status(401).json({
      success: false,
      error: {
        code: 'INVALID_API_KEY',
        message: 'The provided API key is invalid.'
      }
    });
  }

  // Check usage limits
  const currentMonth = new Date().toISOString().slice(0, 7);
  const usageKey = `${apiKey}_${currentMonth}`;
  const currentUsage = usageTracker.get(usageKey) || 0;

  if (keyData.limit !== -1 && currentUsage >= keyData.limit) {
    return res.status(429).json({
      success: false,
      error: {
        code: 'RATE_LIMIT_EXCEEDED',
        message: `Monthly limit of ${keyData.limit} requests exceeded. Upgrade your plan for more requests.`
      },
      usage: {
        used: currentUsage,
        limit: keyData.limit,
        plan: keyData.plan
      }
    });
  }

  // Attach key data to request
  req.apiKeyData = keyData;
  req.apiKey = apiKey;
  req.usageKey = usageKey;
  req.currentUsage = currentUsage;

  next();
};

// Middleware: Track usage
const trackUsage = (req, res, next) => {
  const originalJson = res.json.bind(res);
  res.json = (data) => {
    // Increment usage only on successful requests
    if (data.success !== false) {
      const newUsage = (usageTracker.get(req.usageKey) || 0) + 1;
      usageTracker.set(req.usageKey, newUsage);
    }
    return originalJson(data);
  };
  next();
};

// Helper: Forward request to upstream API
const forwardRequest = async (req, res, endpoint, method = 'GET') => {
  try {
    const config = {
      method,
      url: `${CONFIG.UPSTREAM_API_URL}${endpoint}`,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    if (method === 'POST' || method === 'PUT') {
      config.data = req.body;
    } else if (method === 'GET') {
      config.params = req.query;
      delete config.params.api_key; // Remove gateway's api_key param
    }

    const response = await axios(config);
    
    // Standardize response
    return res.json({
      success: true,
      data: response.data,
      usage: {
        used: req.currentUsage + 1,
        limit: req.apiKeyData.limit,
        plan: req.apiKeyData.plan
      }
    });

  } catch (error) {
    // Handle upstream errors
    const status = error.response?.status || 500;
    const errorData = error.response?.data || {};
    
    return res.status(status).json({
      success: false,
      error: {
        code: errorData.code || 'UPSTREAM_ERROR',
        message: errorData.message || 'An error occurred while processing your request.'
      }
    });
  }
};

// Rate limiting per IP (additional protection)
const ipRateLimit = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 100, // 100 requests per minute per IP
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    error: {
      code: 'TOO_MANY_REQUESTS',
      message: 'Too many requests from this IP. Please try again later.'
    }
  }
});

app.use(ipRateLimit);

// Routes

// Health check (no auth required)
app.get('/health', async (req, res) => {
  try {
    const upstreamHealth = await axios.get(`${CONFIG.UPSTREAM_API_URL}/health`, {
      timeout: 5000
    });
    
    res.json({
      success: true,
      data: {
        gateway: 'operational',
        upstream: upstreamHealth.data,
        timestamp: new Date().toISOString()
      }
    });
  } catch (error) {
    res.status(503).json({
      success: false,
      error: {
        code: 'SERVICE_UNAVAILABLE',
        message: 'Upstream API is not responding.'
      }
    });
  }
});

// Verify single email
app.get('/verify', validateApiKey, trackUsage, (req, res) => {
  if (!req.query.email) {
    return res.status(400).json({
      success: false,
      error: {
        code: 'MISSING_PARAMETER',
        message: 'Email parameter is required.'
      }
    });
  }
  forwardRequest(req, res, '/verify');
});

// Batch verification
app.post('/batch', validateApiKey, trackUsage, (req, res) => {
  if (!req.body.emails || !Array.isArray(req.body.emails)) {
    return res.status(400).json({
      success: false,
      error: {
        code: 'INVALID_REQUEST',
        message: 'Request body must contain an "emails" array.'
      }
    });
  }

  // Check batch size limits based on plan
  const maxBatchSize = {
    free: 10,
    basic: 100,
    pro: 1000,
    enterprise: 10000
  };

  const limit = maxBatchSize[req.apiKeyData.plan];
  if (req.body.emails.length > limit) {
    return res.status(400).json({
      success: false,
      error: {
        code: 'BATCH_TOO_LARGE',
        message: `Batch size exceeds limit of ${limit} for ${req.apiKeyData.plan} plan.`
      }
    });
  }

  forwardRequest(req, res, '/batch', 'POST');
});

// Get statistics
app.get('/stats', validateApiKey, (req, res) => {
  const currentMonth = new Date().toISOString().slice(0, 7);
  const usageKey = `${req.apiKey}_${currentMonth}`;
  const used = usageTracker.get(usageKey) || 0;

  res.json({
    success: true,
    data: {
      plan: req.apiKeyData.plan,
      period: 'monthly',
      usage: {
        used,
        limit: req.apiKeyData.limit,
        remaining: req.apiKeyData.limit === -1 ? 'unlimited' : Math.max(0, req.apiKeyData.limit - used)
      },
      period_start: `${currentMonth}-01`,
      period_end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().split('T')[0]
    }
  });
});

// Get supported domains info
app.get('/domains', validateApiKey, (req, res) => {
  forwardRequest(req, res, '/domains');
});

// Documentation endpoint
app.get('/', (req, res) => {
  res.json({
    name: 'Email Validation API Gateway',
    version: '1.0.0',
    endpoints: {
      '/verify': 'GET - Verify a single email address',
      '/batch': 'POST - Verify multiple email addresses',
      '/stats': 'GET - Get your API usage statistics',
      '/domains': 'GET - Get list of supported domains',
      '/health': 'GET - Check API health status'
    },
    authentication: 'Include your API key in X-API-Key header or api_key query parameter',
    documentation: 'https://docs.yourapi.com'
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An internal error occurred. Please contact support.'
    }
  });
});

// Start server
app.listen(CONFIG.PORT, () => {
  console.log(`🚀 API Gateway running on port ${CONFIG.PORT}`);
  console.log(`📡 Forwarding to upstream: ${CONFIG.UPSTREAM_API_URL}`);
  console.log(`\n🔑 Demo API Keys:`);
  Object.entries(CONFIG.API_KEYS).forEach(([key, data]) => {
    console.log(`   ${key} - ${data.plan} plan (${data.limit === -1 ? 'unlimited' : data.limit} requests/month)`);
  });
});

module.exports = app;
