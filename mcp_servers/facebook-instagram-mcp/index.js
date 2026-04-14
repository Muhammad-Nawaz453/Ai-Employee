#!/usr/bin/env node

/**
 * Facebook & Instagram MCP Server
 * 
 * Provides tools for:
 * - Posting to Facebook Pages
 * - Posting to Instagram Business
 * - Retrieving posts and engagement metrics
 * - Generating social media summaries
 * 
 * All posts require human approval (HITL pattern)
 */

const { McpServer } = require("@modelcontextprotocol/sdk/server/mcp.js");
const { StreamableHTTPServerTransport } = require("@modelcontextprotocol/sdk/server/streamableHttp.js");
const { z } = require("zod");
const axios = require("axios");
const fs = require("fs-extra");
const path = require("path");

// Configuration
const CONFIG = {
  vaultPath: process.env.VAULT_PATH || "./vault",
  facebookAccessToken: process.env.FACEBOOK_ACCESS_TOKEN || "",
  instagramAccountId: process.env.INSTAGRAM_ACCOUNT_ID || "",
  facebookPageId: process.env.FACEBOOK_PAGE_ID || "",
  sessionPath: process.env.SESSION_PATH || "./session",
  maxPostLength: 5000,
  maxHashtags: 30,
};

// Session storage
const SESSION_FILE = path.join(CONFIG.sessionPath, "storage.json");

async function loadSession() {
  try {
    if (await fs.pathExists(SESSION_FILE)) {
      return await fs.readJson(SESSION_FILE);
    }
  } catch (error) {
    console.error("Error loading session:", error.message);
  }
  return { initialized: false };
}

async function saveSession(session) {
  try {
    await fs.ensureDir(CONFIG.sessionPath);
    await fs.writeJson(SESSION_FILE, session, { spaces: 2 });
  } catch (error) {
    console.error("Error saving session:", error.message);
  }
}

// Create MCP Server
const server = new McpServer({
  name: "facebook-instagram-mcp",
  version: "1.0.0",
});

/**
 * Tool: facebook_post
 * Creates a draft post that requires human approval
 */
server.registerTool(
  "facebook_post",
  {
    title: "Create Facebook Post Draft",
    description: "Create a draft Facebook post (requires human approval before publishing)",
    inputSchema: z.object({
      message: z.string().describe("Post message content"),
      link: z.string().optional().describe("Optional link to share"),
      scheduledTime: z.string().optional().describe("Optional ISO 8601 scheduled time"),
    }),
  },
  async ({ message, link, scheduledTime }) => {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const approvalId = `FB_POST_${timestamp}`;
      
      // Validate post length
      if (message.length > CONFIG.maxPostLength) {
        return {
          content: [
            {
              type: "text",
              text: `Error: Post exceeds maximum length of ${CONFIG.maxPostLength} characters`,
            },
          ],
        };
      }

      // Create approval request file
      const approvalContent = {
        type: "approval_request",
        action: "facebook_post",
        platform: "facebook",
        message,
        link: link || null,
        scheduledTime: scheduledTime || null,
        created: new Date().toISOString(),
        status: "pending",
      };

      const approvalPath = path.join(
        CONFIG.vaultPath,
        "Pending_Approval",
        `${approvalId}.md`
      );

      const markdownContent = `---
type: approval_request
action: facebook_post
platform: facebook
scheduledTime: ${scheduledTime || "immediate"}
created: ${new Date().toISOString()}
status: pending
---

# Facebook Post Draft

## Content
${message}

${link ? `## Link\n${link}\n` : ""}
${scheduledTime ? `## Scheduled For\n${scheduledTime}\n` : ""}

## Approval Instructions
Move this file to /Approved to publish.
Move to /Rejected to cancel.
`;

      await fs.ensureDir(path.join(CONFIG.vaultPath, "Pending_Approval"));
      await fs.writeFile(approvalPath, markdownContent);

      return {
        content: [
          {
            type: "text",
            text: `Facebook post draft created. Approval request: ${approvalId}\nPending in: ${approvalPath}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error creating Facebook post: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

/**
 * Tool: instagram_post
 * Creates a draft Instagram post that requires human approval
 */
server.registerTool(
  "instagram_post",
  {
    title: "Create Instagram Post Draft",
    description: "Create a draft Instagram post (requires human approval before publishing)",
    inputSchema: z.object({
      caption: z.string().describe("Post caption"),
      imageUrl: z.string().optional().describe("URL of image to post"),
      hashtags: z.array(z.string()).optional().describe("Array of hashtags (max 30)"),
      scheduledTime: z.string().optional().describe("Optional ISO 8601 scheduled time"),
    }),
  },
  async ({ caption, imageUrl, hashtags, scheduledTime }) => {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const approvalId = `IG_POST_${timestamp}`;

      // Validate caption length
      if (caption.length > 2200) {
        return {
          content: [
            {
              type: "text",
              text: "Error: Caption exceeds maximum length of 2200 characters",
            },
          ],
        };
      }

      // Validate hashtags
      if (hashtags && hashtags.length > CONFIG.maxHashtags) {
        return {
          content: [
            {
              type: "text",
              text: `Error: Too many hashtags. Maximum is ${CONFIG.maxHashtags}`,
            },
          ],
        };
      }

      // Build caption with hashtags
      let fullCaption = caption;
      if (hashtags && hashtags.length > 0) {
        fullCaption += "\n\n" + hashtags.map(h => h.startsWith("#") ? h : `#${h}`).join(" ");
      }

      // Create approval request file
      const approvalPath = path.join(
        CONFIG.vaultPath,
        "Pending_Approval",
        `${approvalId}.md`
      );

      const markdownContent = `---
type: approval_request
action: instagram_post
platform: instagram
scheduledTime: ${scheduledTime || "immediate"}
created: ${new Date().toISOString()}
status: pending
---

# Instagram Post Draft

## Caption
${fullCaption}

${imageUrl ? `## Image URL\n${imageUrl}\n` : "## Note\nImage required - provide imageUrl when approving."}
${scheduledTime ? `## Scheduled For\n${scheduledTime}\n` : ""}

## Approval Instructions
Move this file to /Approved to publish.
Move to /Rejected to cancel.
`;

      await fs.ensureDir(path.join(CONFIG.vaultPath, "Pending_Approval"));
      await fs.writeFile(approvalPath, markdownContent);

      return {
        content: [
          {
            type: "text",
            text: `Instagram post draft created. Approval request: ${approvalId}\nPending in: ${approvalPath}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error creating Instagram post: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

/**
 * Tool: publish_approved_post
 * Publishes a post that has been approved
 */
server.registerTool(
  "publish_approved_post",
  {
    title: "Publish Approved Social Media Post",
    description: "Publish a post that has been approved by human",
    inputSchema: z.object({
      platform: z.enum(["facebook", "instagram"]).describe("Platform to post to"),
      approvalFile: z.string().describe("Path to approved approval file"),
    }),
  },
  async ({ platform, approvalFile }) => {
    try {
      // Read approval file
      const approvalData = await fs.readFile(approvalFile, "utf-8");
      
      // Extract message/caption from file (simple parsing)
      const messageMatch = approvalData.match(/## Content\n([\s\S]*?)(\n##|$)/);
      const captionMatch = approvalData.match(/## Caption\n([\s\S]*?)(\n##|$)/);
      
      const message = messageMatch ? messageMatch[1].trim() : "";
      const caption = captionMatch ? captionMatch[1].trim() : "";

      if (!CONFIG.facebookAccessToken) {
        return {
          content: [
            {
              type: "text",
              text: "Error: FACEBOOK_ACCESS_TOKEN not configured",
            },
          ],
          isError: true,
        };
      }

      let result;
      
      if (platform === "facebook") {
        // Post to Facebook Page
        const postUrl = `https://graph.facebook.com/v18.0/${CONFIG.facebookPageId}/feed`;
        const postData = {
          message,
          access_token: CONFIG.facebookAccessToken,
        };

        result = await axios.post(postUrl, postData);
      } else if (platform === "instagram") {
        // Post to Instagram (two-step process)
        const igAccountId = CONFIG.instagramAccountId;
        
        // Step 1: Create media container
        const containerUrl = `https://graph.facebook.com/v18.0/${igAccountId}/media`;
        const containerData = {
          image_url: "https://example.com/placeholder.jpg", // In production, use actual image
          caption,
          access_token: CONFIG.facebookAccessToken,
        };

        const containerResponse = await axios.post(containerUrl, containerData);
        const creationId = containerResponse.data.id;

        // Step 2: Publish the container
        const publishUrl = `https://graph.facebook.com/v18.0/${igAccountId}/media_publish`;
        const publishData = {
          creation_id: creationId,
          access_token: CONFIG.facebookAccessToken,
        };

        result = await axios.post(publishUrl, publishData);
      }

      // Log the action
      const logEntry = {
        timestamp: new Date().toISOString(),
        action: `${platform}_post`,
        result: "success",
        postId: result.data.id || "unknown",
      };

      const logDir = path.join(CONFIG.vaultPath, "Logs");
      await fs.ensureDir(logDir);
      const logFile = path.join(logDir, `${new Date().toISOString().split("T")[0]}.jsonl`);
      await fs.appendFile(logFile, JSON.stringify(logEntry) + "\n");

      return {
        content: [
          {
            type: "text",
            text: `Successfully published to ${platform}. Post ID: ${result.data.id}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error publishing post: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

/**
 * Tool: get_facebook_insights
 * Retrieves Facebook page insights and metrics
 */
server.registerTool(
  "get_facebook_insights",
  {
    title: "Get Facebook Page Insights",
    description: "Retrieve engagement metrics from Facebook Page",
    inputSchema: z.object({
      metric: z.string().optional().describe("Specific metric (page_impressions, page_post_engagements, etc.)"),
      period: z.string().optional().describe("Time period (day, week, month)"),
    }),
  },
  async ({ metric, period }) => {
    try {
      if (!CONFIG.facebookAccessToken) {
        return {
          content: [
            {
              type: "text",
              text: "Error: FACEBOOK_ACCESS_TOKEN not configured",
            },
          ],
          isError: true,
        };
      }

      const insightsMetric = metric || "page_impressions,page_engaged_users,page_post_engagements";
      const insightsPeriod = period || "week";

      const insightsUrl = `https://graph.facebook.com/v18.0/${CONFIG.facebookPageId}/insights`;
      
      const response = await axios.get(insightsUrl, {
        params: {
          metric: insightsMetric,
          period: insightsPeriod,
          access_token: CONFIG.facebookAccessToken,
        },
      });

      // Format insights
      const insights = response.data.data || [];
      let summary = "# Facebook Page Insights\n\n";
      
      insights.forEach(item => {
        const values = item.values || [];
        const latestValue = values.length > 0 ? values[values.length - 1].value : "N/A";
        summary += `## ${item.title || item.name}\n`;
        summary += `- Value: ${latestValue}\n`;
        summary += `- Description: ${item.description}\n\n`;
      });

      return {
        content: [
          {
            type: "text",
            text: summary,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error fetching Facebook insights: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

/**
 * Tool: get_social_summary
 * Generates a summary of social media activity
 */
server.registerTool(
  "get_social_summary",
  {
    title: "Get Social Media Summary",
    description: "Generate summary of recent social media activity and engagement",
    inputSchema: z.object({
      platform: z.enum(["facebook", "instagram", "all"]).optional().describe("Platform to summarize"),
      days: z.number().optional().describe("Number of days to look back"),
    }),
  },
  async ({ platform, days }) => {
    try {
      const lookbackDays = days || 7;
      const platforms = platform === "all" ? ["facebook", "instagram"] : [platform || "facebook"];
      
      let summary = `# Social Media Summary (Last ${lookbackDays} Days)\n\n`;

      for (const plat of platforms) {
        summary += `## ${plat.charAt(0).toUpperCase() + plat.slice(1)}\n\n`;
        
        try {
          if (plat === "facebook" && CONFIG.facebookPageId && CONFIG.facebookAccessToken) {
            // Get recent posts
            const postsUrl = `https://graph.facebook.com/v18.0/${CONFIG.facebookPageId}/posts`;
            const response = await axios.get(postsUrl, {
              params: {
                fields: "message,created_time,likes.summary(true),comments.summary(true),shares",
                since: new Date(Date.now() - lookbackDays * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
                access_token: CONFIG.facebookAccessToken,
                limit: 10,
              },
            });

            const posts = response.data.data || [];
            summary += `### Recent Posts (${posts.length})\n\n`;
            
            let totalLikes = 0;
            let totalComments = 0;

            posts.forEach((post, idx) => {
              const likes = post.likes?.summary?.total_count || 0;
              const comments = post.comments?.summary?.total_count || 0;
              const shares = post.shares?.count || 0;
              
              totalLikes += likes;
              totalComments += comments;

              summary += `#### Post ${idx + 1} (${post.created_time})\n`;
              summary += `- Message: ${(post.message || "").substring(0, 100)}...\n`;
              summary += `- Likes: ${likes} | Comments: ${comments} | Shares: ${shares}\n\n`;
            });

            summary += `### Engagement Summary\n`;
            summary += `- Total Likes: ${totalLikes}\n`;
            summary += `- Total Comments: ${totalComments}\n`;
            summary += `- Average Engagement: ${posts.length > 0 ? ((totalLikes + totalComments) / posts.length).toFixed(1) : 0} per post\n\n`;
          } else {
            summary += "*No data available - configure access tokens*\n\n";
          }
        } catch (error) {
          summary += `*Error fetching data: ${error.message}*\n\n`;
        }
      }

      // Save summary to vault
      const timestamp = new Date().toISOString().split("T")[0];
      const summaryPath = path.join(CONFIG.vaultPath, "Briefings", `social_summary_${timestamp}.md`);
      await fs.ensureDir(path.join(CONFIG.vaultPath, "Briefings"));
      await fs.writeFile(summaryPath, summary);

      return {
        content: [
          {
            type: "text",
            text: summary,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error generating social summary: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

/**
 * Tool: schedule_social_post
 * Creates a scheduled post approval request
 */
server.registerTool(
  "schedule_social_post",
  {
    title: "Schedule Social Media Post",
    description: "Create a scheduled post for Facebook or Instagram with future publish time",
    inputSchema: z.object({
      platform: z.enum(["facebook", "instagram"]).describe("Platform to post"),
      content: z.string().describe("Post content"),
      scheduledTime: z.string().describe("ISO 8601 scheduled publish time"),
      hashtags: z.array(z.string()).optional().describe("Hashtags (Instagram only)"),
    }),
  },
  async ({ platform, content, scheduledTime, hashtags }) => {
    try {
      // Validate scheduled time is in the future
      const scheduleDate = new Date(scheduledTime);
      if (scheduleDate <= new Date()) {
        return {
          content: [
            {
              type: "text",
              text: "Error: Scheduled time must be in the future",
            },
          ],
          isError: true,
        };
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const approvalId = `SCHEDULED_${platform.toUpperCase()}_${timestamp}`;

      const approvalPath = path.join(
        CONFIG.vaultPath,
        "Pending_Approval",
        `${approvalId}.md`
      );

      const markdownContent = `---
type: approval_request
action: schedule_${platform}_post
platform: ${platform}
scheduledTime: ${scheduledTime}
created: ${new Date().toISOString()}
status: pending
---

# Scheduled ${platform.charAt(0).toUpperCase() + platform.slice(1)} Post

## Content
${content}

${hashtags && platform === "instagram" ? `## Hashtags\n${hashtags.join(" ")}\n` : ""}

## Schedule
- **Publish At:** ${scheduledTime}
- **Status:** Pending Approval

## Approval Instructions
Move this file to /Approved to schedule.
Move to /Rejected to cancel.
`;

      await fs.ensureDir(path.join(CONFIG.vaultPath, "Pending_Approval"));
      await fs.writeFile(approvalPath, markdownContent);

      return {
        content: [
          {
            type: "text",
            text: `Scheduled ${platform} post created for ${scheduledTime}. Approval: ${approvalId}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error scheduling post: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Start server
async function main() {
  const transport = new StreamableHTTPServerTransport();
  await server.connect(transport);
  
  const port = process.env.PORT || 8810;
  const httpServer = require("http").createServer(async (req, res) => {
    if (req.method === "POST") {
      await transport.handleRequest(req, res);
    } else {
      res.writeHead(405);
      res.end("Method not allowed");
    }
  });

  httpServer.listen(port, () => {
    console.log(`Facebook/Instagram MCP Server running on port ${port}`);
    console.log(`Vault: ${CONFIG.vaultPath}`);
  });
}

main().catch(console.error);

// Export for testing
module.exports = { server, CONFIG };
