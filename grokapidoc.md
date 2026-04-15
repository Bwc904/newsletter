# Grok API Guide for Building a Daily X (Twitter) Trending Newsletter

You are helping build a **daily newsletter** that curates the top trending and most engaging posts from X across multiple topics (e.g., Tech, AI, Politics, Finance, Sports, Business, Science, etc.).

The core capability comes from **xAI's Grok API**, which has native, real-time **X Search tools** — one of the strongest advantages for this use case.

## 1. Recommended Model
**Primary model: `grok-4-1-fast-reasoning`** (or `grok-4-1-fast-non-reasoning` if you want slightly lower cost/latency)

- **Pricing**: $0.20 per million input tokens / $0.50 per million output tokens
- **Context window**: 2,000,000 tokens (plenty for multiple topics + full post threads)
- **Why this model?**
  - Excellent at agentic tool calling and structured output (JSON)
  - Very cost-effective for daily runs with many tool calls
  - Strong reasoning for summarizing, filtering quality posts, spotting trends, and writing engaging newsletter copy
  - Fast enough for scheduled jobs

**Avoid for this project**: Grok 4.20 series ($2.00 / $6.00) — it is overkill and ~10x more expensive unless you need extremely deep multi-agent analysis.

**Batch API tip**: Use the Batch API (50% cheaper) since the newsletter is asynchronous/daily.

## 2. X Search Tools (The Key Feature)
Grok has built-in server-side X tools that run on xAI infrastructure (no extra API keys needed):

- **`x_keyword_search`**: Advanced search with all Twitter operators (since:YYYY-MM-DD, until:YYYY-MM-DD, min_faves:, min_retweets:, from:user, filter:images, etc.). Supports "Latest" or "Top" mode.
- **`x_semantic_search`**: Finds relevant posts based on meaning (great for broad topics like "trending discussions about AI safety").
- **`x_user_search`**: Find user profiles.
- **`x_thread_fetch`**: Get full context of a thread by post ID.

You enable them by including `{"type": "x_search"}` in the tools array (or using the xAI SDK's `x_search()` helper).

**Tool calling cost**: X search tools are billed at ~$5 per 1,000 calls (on top of token costs). For a daily newsletter with 5–10 topics, this is usually only $0.05–$0.20 per day.

## 3. Core Workflow You Should Implement
Every day:
1. Define a list of topics/categories for the newsletter.
2. For each topic, have Grok:
   - Call X search tools (mix of semantic + keyword with time filters like last 24h)
   - Fetch high-engagement posts (high likes, retweets, replies, from verified/reputable accounts when possible)
   - Filter for quality, originality, and relevance (avoid spam, duplicates, low-effort posts)
   - Summarize key insights or quote the best parts
   - Write a short, engaging newsletter blurb for each selected post
3. Compile everything into clean sections (with post links, author handles, engagement stats, optional images).
4. Output in structured JSON or Markdown ready for your email template.

**Strong system prompt style**:
"Act as a senior newsletter curator. Use the x_search tool to find the top 8–12 most engaging posts from the last 24 hours on [TOPIC]. Prioritize virality (likes + retweets + replies), verified accounts, and substantive content. For each post, provide: author, handle, post text/link, engagement numbers, one-sentence summary, and why it's noteworthy. Then select the best 3–5 for the newsletter and write witty/intelligent commentary."

Force structured output with JSON mode or strict schema for easy parsing.

## 4. Cost Expectations (Using Grok 4.1 Fast)
- **Per daily run** (5–10 topics, moderate depth): Usually $0.30 – $2.00 total (tokens + tool calls)
- **Monthly**: $10 – $60 for a solid newsletter (can be lower with optimization and batch API)
- Tips to minimize cost:
  - Use `limit` parameter to return fewer posts per call
  - Request only JSON output (reduces output tokens)
  - Run once per day via cron / GitHub Actions / serverless
  - Cache results if a topic doesn't change much
  - Start with 3–5 topics and scale up

## 5. API Setup Reminders
- Get your key at https://console.x.ai
- Add payment method and set a monthly spending limit
- Use the official xAI SDK (`pip install xai-sdk`) for easiest tool calling, or OpenAI-compatible client with base_url `https://api.x.ai/v1`
- Enable tools: `tools=[x_search()]` (or equivalent in OpenAI format)

## 6. Best Practices for High-Quality Newsletter
- Combine semantic search for discovery + keyword search for precision
- Add time filters (`since:2026-04-14` style) to focus on last 24–48 hours
- Instruct Grok to deduplicate across topics
- Ask for neutral, truthful summaries (Grok is good at this)
- Include direct links to posts: `https://x.com/user/status/ID`
- Optionally fetch full threads for important posts
- Style: Keep it concise, insightful, and slightly opinionated/witty like Grok's personality

## 7. Example Prompt Skeleton (Copy & Adapt)
You are curating the [Topic] section of a daily newsletter.
Use x_search tools aggressively to gather fresh data from the last 24 hours.
Find the most trending/engaging posts about [TOPIC].
For each promising post return:

author, handle, post_url, text, likes, retweets, replies, timestamp
short summary
why it matters

Then select the top 4 and write engaging newsletter intros.
Output ONLY valid JSON with this schema: { "topic": "...", "posts": [...], "curated": [...] }
textNow you have everything needed. Use this knowledge to help me write code, refine prompts, design the full pipeline, or generate sample newsletter sections.

Let me know what you want to build first!