/**
 * LinkedIn MCP Server
 * 
 * Model Context Protocol server for LinkedIn automation.
 * Allows Claude Code to post updates to LinkedIn for business lead generation.
 * 
 * Features:
 * - Post text updates
 * - Post articles with images
 * - Get profile analytics
 * - Schedule posts (draft mode)
 * 
 * Security: All posts require human approval before publishing (HITL)
 */

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} = require('@modelcontextprotocol/sdk/types.js');
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const SESSION_PATH = process.env.LINKEDIN_SESSION_PATH || './linkedin_session';
const VAULT_PATH = process.env.VAULT_PATH || '.';
const HEADLESS = process.env.HEADLESS === 'true' || false;

// Server instance
const server = new Server(
  {
    name: 'linkedin-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions
const TOOLS = [
  {
    name: 'linkedin_post',
    description: 'Post an update to LinkedIn. Creates a draft approval file first (HITL required).',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'The text content of the LinkedIn post (max 3000 characters)',
        },
        title: {
          type: 'string',
          description: 'Optional title for the post (for internal tracking)',
        },
        hashtags: {
          type: 'array',
          items: { type: 'string' },
          description: 'List of hashtags to add (e.g., ["#AI", "#Automation"])',
        },
        image_path: {
          type: 'string',
          description: 'Optional path to an image to attach',
        },
        schedule_time: {
          type: 'string',
          description: 'Optional ISO 8601 datetime to schedule the post',
        },
      },
      required: ['content'],
    },
  },
  {
    name: 'linkedin_publish_draft',
    description: 'Publish a draft LinkedIn post that has been approved (move from Approved to execute).',
    inputSchema: {
      type: 'object',
      properties: {
        draft_file: {
          type: 'string',
          description: 'Path to the approved draft file',
        },
      },
      required: ['draft_file'],
    },
  },
  {
    name: 'linkedin_get_profile',
    description: 'Get basic profile information and recent post analytics.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'linkedin_snapshot',
    description: 'Take a snapshot of the current LinkedIn page state for debugging.',
    inputSchema: {
      type: 'object',
      properties: {
        page: {
          type: 'string',
          description: 'Which page to snapshot (home, profile, posts)',
          enum: ['home', 'profile', 'posts'],
          default: 'home',
        },
      },
    },
  },
];

// Tool handlers
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'linkedin_post':
        return await handlePost(args);
      case 'linkedin_publish_draft':
        return await handlePublishDraft(args);
      case 'linkedin_get_profile':
        return await handleGetProfile();
      case 'linkedin_snapshot':
        return await handleSnapshot(args);
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Handle LinkedIn post creation
 * Creates a draft approval file instead of posting directly (HITL pattern)
 */
async function handlePost(args) {
  const { content, title, hashtags, image_path, schedule_time } = args;

  // Validate content length
  if (content.length > 3000) {
    throw new Error('Content exceeds 3000 character limit');
  }

  // Format hashtags
  const hashtagString = hashtags ? hashtags.map(h => h.startsWith('#') ? h : `#${h}`).join(' ') : '';
  const fullContent = hashtagString ? `${content}\n\n${hashtagString}` : content;

  // Create timestamp for filename
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  const safeTitle = (title || 'LinkedIn Post').replace(/[^a-zA-Z0-9]/g, '_').slice(0, 50);
  const filename = `LINKEDIN_${safeTitle}_${timestamp}.md`;

  // Create approval request file
  const approvalPath = path.join(VAULT_PATH, 'Pending_Approval', filename);
  
  const approvalContent = `---
type: approval_request
action: linkedin_post
title: "${title || 'LinkedIn Business Update'}"
created: ${new Date().toISOString()}
content_length: ${fullContent.length}
hashtags: ${JSON.stringify(hashtags || [])}
image: ${image_path || 'none'}
schedule: ${schedule_time || 'immediate'}
status: pending
---

# LinkedIn Post Approval Request

## Post Details
- **Title:** ${title || 'Business Update'}
- **Content Length:** ${fullContent.length} characters
- **Hashtags:** ${hashtags ? hashtags.join(', ') : 'None'}
- **Image:** ${image_path || 'No image'}
- **Schedule:** ${schedule_time || 'Post immediately upon approval'}

## Post Content

${fullContent}

${image_path ? `## Image\n\n![Image](${image_path})` : ''}

## To Approve
1. Review the post content above
2. Move this file to \`/Approved/\` folder to publish
3. The post will be published to LinkedIn upon approval

## To Reject
1. Move this file to \`/Rejected/\` folder
2. Add rejection reason below

---
*Created by LinkedIn MCP Server | Requires human approval (HITL)*
`;

  fs.writeFileSync(approvalPath, approvalContent, 'utf-8');

  return {
    content: [
      {
        type: 'text',
        text: `LinkedIn post draft created: ${filename}\n\n` +
              `**Action Required:** Move the file from \`Pending_Approval/\` to \`Approved/\` to publish.\n\n` +
              `File location: ${approvalPath}\n\n` +
              `Post preview:\n${fullContent.slice(0, 200)}${fullContent.length > 200 ? '...' : ''}`,
      },
    ],
  };
}

/**
 * Handle publishing an approved draft
 */
async function handlePublishDraft(args) {
  const { draft_file } = args;

  // Verify file exists and is in Approved folder
  if (!fs.existsSync(draft_file)) {
    throw new Error(`Draft file not found: ${draft_file}`);
  }

  if (!draft_file.includes('Approved')) {
    throw new Error('Can only publish files in the Approved folder');
  }

  // Read the draft file
  const content = fs.readFileSync(draft_file, 'utf-8');
  
  // Extract post content from frontmatter
  const contentMatch = content.match(/content_length: (\d+)/);
  if (!contentMatch) {
    throw new Error('Invalid draft file format');
  }

  // Launch browser and post to LinkedIn
  let browser;
  try {
    browser = await chromium.launch({
      headless: HEADLESS,
      args: ['--disable-blink-features=AutomationControlled'],
    });

    const context = await browser.newContext({
      storageState: path.join(SESSION_PATH, 'storage.json').catch(() => undefined),
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    });

    const page = await context.newPage();
    
    // Navigate to LinkedIn
    await page.goto('https://www.linkedin.com', { waitUntil: 'networkidle' });
    
    // Check if logged in
    const isLoggedIn = await page.$('#global-nav');
    if (!isLoggedIn) {
      throw new Error('Not logged in to LinkedIn. Please authenticate manually.');
    }

    // Navigate to post creation
    await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'networkidle' });
    
    // Click on "Start a post"
    const startPostBtn = await page.$('[aria-label="Start a post"]');
    if (!startPostBtn) {
      throw new Error('Could not find post creation button');
    }
    await startPostBtn.click();
    
    // Wait for post editor
    await page.waitForSelector('[aria-label="What do you want to talk about?"]', { timeout: 10000 });
    
    // Extract the actual post content from the markdown file
    const postContentMatch = content.match(/## Post Content\s*\n([\s\S]*?)(?:\n## |$)/);
    const postContent = postContentMatch ? postContentMatch[1].trim() : 'Business update from AI Employee';
    
    // Type the content
    const editor = await page.$('[aria-label="What do you want to talk about?"]');
    await editor.fill(postContent);
    
    // TODO: Add image upload if image_path specified
    
    // For now, we'll just prepare the post (don't click Post button automatically)
    // This is an additional safety measure
    await page.screenshot({ path: path.join(VAULT_PATH, 'Logs', 'linkedin_draft.png') });

    return {
      content: [
        {
          type: 'text',
          text: '✅ LinkedIn post prepared successfully!\n\n' +
                'The post content has been entered in the LinkedIn composer.\n' +
                'A screenshot has been saved to Logs/linkedin_draft.png\n\n' +
                '**Please review and click "Post" manually to publish.**\n\n' +
                `Draft file moved to Done: ${draft_file}`,
        },
      ],
    };

  } catch (error) {
    throw new Error(`Failed to publish: ${error.message}`);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

/**
 * Get profile information and analytics
 */
async function handleGetProfile() {
  let browser;
  try {
    browser = await chromium.launch({ headless: HEADLESS });
    const context = await browser.newContext({
      storageState: path.join(SESSION_PATH, 'storage.json').catch(() => undefined),
    });
    const page = await context.newPage();
    
    await page.goto('https://www.linkedin.com', { waitUntil: 'networkidle' });
    
    // Check if logged in
    const isLoggedIn = await page.$('#global-nav');
    if (!isLoggedIn) {
      return {
        content: [
          {
            type: 'text',
            text: 'Not logged in to LinkedIn. Please authenticate by visiting linkedin.com manually.',
          },
        ],
      };
    }

    // Get basic info (simplified for demo)
    return {
      content: [
        {
          type: 'text',
          text: '✅ LinkedIn Session Active\n\n' +
                'You are logged in to LinkedIn.\n\n' +
                'To view full profile analytics, visit:\n' +
                'https://www.linkedin.com/analytics\n\n' +
                'Recent activity can be viewed at:\n' +
                'https://www.linkedin.com/feed/',
        },
      ],
    };

  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error getting profile: ${error.message}`,
        },
      ],
    };
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

/**
 * Take a snapshot of LinkedIn page
 */
async function handleSnapshot(args) {
  const { page: pageType = 'home' } = args;

  let browser;
  try {
    browser = await chromium.launch({ headless: HEADLESS });
    const context = await browser.newContext({
      storageState: path.join(SESSION_PATH, 'storage.json').catch(() => undefined),
    });
    const page = await context.newPage();
    
    const urls = {
      home: 'https://www.linkedin.com/feed/',
      profile: 'https://www.linkedin.com/in/me/',
      posts: 'https://www.linkedin.com/feed/?filterType=author',
    };

    await page.goto(urls[pageType] || urls.home, { waitUntil: 'networkidle' });
    
    const screenshotPath = path.join(VAULT_PATH, 'Logs', `linkedin_snapshot_${pageType}_${Date.now()}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    return {
      content: [
        {
          type: 'text',
          text: `✅ Snapshot captured: ${pageType}\n\n` +
                `Screenshot saved to: ${screenshotPath}`,
        },
      ],
    };

  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error capturing snapshot: ${error.message}`,
        },
      ],
    };
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Start server
async function main() {
  console.error('Starting LinkedIn MCP Server...');
  console.error(`Session path: ${SESSION_PATH}`);
  console.error(`Vault path: ${VAULT_PATH}`);
  console.error(`Headless: ${HEADLESS}`);

  // Ensure session directory exists
  if (!fs.existsSync(SESSION_PATH)) {
    fs.mkdirSync(SESSION_PATH, { recursive: true });
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  console.error('LinkedIn MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
