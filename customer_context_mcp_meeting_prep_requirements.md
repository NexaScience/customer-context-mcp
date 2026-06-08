# Customer Context MCP - Meeting Prep Assistant Requirements

## 1. Overview

Customer Context MCP is an MCP server and iframe-based MCP App that helps sales and customer success teams prepare for customer meetings.

The app retrieves customer-related information from Notion, Slack, and Google Drive, analyzes it with an LLM, and displays an evidence-backed customer brief. Users can also ask follow-up questions inside the iframe UI.

## 2. Target Use Case

### Primary Use Case

Prepare for an upcoming customer meeting.

Example prompt:

```text
A社との明日の商談に向けて、Notion、Slack、Google Driveの情報をもとに状況を整理してください。
```

### Target Users

- Sales
- Customer Success
- Account Managers
- Founders / Executives handling strategic customers

## 3. Data Sources

The MVP retrieves information only from the following sources.

| Source | Retrieved Information |
|---|---|
| Notion | Meeting notes, customer pages, project notes, internal customer memos |
| Slack | Internal discussions, customer-related threads, risk signals, recent updates |
| Google Drive | Proposals, meeting minutes, requirement documents, security materials |

## 4. Core Features

### 4.1 Customer Context Search

Search customer-related information across Notion, Slack, and Google Drive.

Input:

```ts
{
  customer_name: string;
  customer_aliases?: string[];
  period?: "7d" | "30d" | "90d" | "all";
  sources?: ("notion" | "slack" | "google_drive")[];
}
```

### 4.2 Meeting Brief Generation

Generate a structured customer meeting brief using retrieved context.

Output:

```ts
{
  summary: string;
  meeting_objective: string;
  key_topics: string[];
  risks: Risk[];
  opportunities: Opportunity[];
  suggested_questions: Question[];
  recommended_actions: Action[];
  timeline: TimelineEvent[];
  evidence: Evidence[];
}
```

### 4.3 Interactive Follow-up Q&A

Allow users to ask questions about the generated brief inside the iframe MCP App.

Examples:

- この顧客の最大の懸念点は？
- 次回商談で確認すべき質問は？
- Slack上の根拠だけを見せて
- Google Driveの提案資料から論点を抽出して
- 先方に送るフォローアップ文面を作って

### 4.4 Evidence Display

Every summary, risk, opportunity, and recommendation must be linked to evidence.

Evidence fields:

```ts
{
  id: string;
  source: "notion" | "slack" | "google_drive";
  title: string;
  excerpt: string;
  url?: string;
  timestamp?: string;
}
```

## 5. MCP Tools

### 5.1 `search_customer_context`

Retrieves customer-related documents, messages, and notes.

```ts
search_customer_context({
  customer_name,
  customer_aliases,
  period,
  sources
})
```

### 5.2 `generate_meeting_brief`

Analyzes retrieved context and generates a meeting preparation brief.

```ts
generate_meeting_brief({
  customer_name,
  customer_aliases,
  meeting_date,
  objective,
  period
})
```

### 5.3 `ask_meeting_brief`

Answers follow-up questions using the generated brief and evidence.

```ts
ask_meeting_brief({
  brief_id,
  question,
  evidence_scope?
})
```

### 5.4 `get_evidence_detail`

Returns detailed evidence for a selected insight.

```ts
get_evidence_detail({
  evidence_id
})
```

### 5.5 `draft_customer_message`

Generates draft messages for follow-up or internal sharing.

```ts
draft_customer_message({
  brief_id,
  purpose: "follow_up_email" | "internal_slack_summary" | "meeting_agenda"
})
```

## 6. iframe MCP App UI

### Main Screen

The iframe app displays a customer meeting brief dashboard.

Sections:

1. Customer Header
2. Executive Summary
3. Key Topics
4. Risks
5. Opportunities
6. Suggested Questions
7. Timeline
8. Recommended Actions
9. Evidence Drawer
10. Ask Panel

### Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Customer Meeting Brief                                       │
├──────────────────────────────────────────────────────────────┤
│ Customer / Meeting / Sources / Last Updated                  │
├───────────────────────────────┬──────────────────────────────┤
│ Summary                       │ Ask about this customer       │
│ Key Topics                    │ Suggested Questions           │
│ Risks                         │ Interactive Q&A               │
│ Opportunities                 │                              │
│ Timeline                      │ Evidence Drawer               │
│ Recommended Actions           │                              │
└───────────────────────────────┴──────────────────────────────┘
```

## 7. MVP Scope

### In Scope

- Read-only integration with Notion, Slack, and Google Drive
- Customer search by name and aliases
- LLM-based meeting brief generation
- Structured dashboard in iframe
- Follow-up Q&A inside iframe
- Evidence-linked insights
- Draft generation for follow-up messages and internal summaries

### Out of Scope

- CRM integration
- Email sending
- Slack posting
- Notion / Google Drive write-back
- Task creation
- Complex permission management
- Multi-customer portfolio dashboard

## 8. Success Criteria

The MVP is successful if a user can:

1. Enter a customer name and meeting objective
2. Retrieve relevant information from Notion, Slack, and Google Drive
3. View a structured meeting preparation brief
4. Understand risks, opportunities, and recommended actions
5. Open evidence for each insight
6. Ask follow-up questions inside the iframe UI
7. Generate a draft follow-up message or internal summary

## 9. Recommended Demo Scenario

Prompt:

```text
A社との明日の商談に向けて、Notion、Slack、Google Driveの情報をもとに、状況・懸念点・確認すべき質問・提案すべき内容を整理してください。
```

Expected result:

- A customer meeting brief dashboard is displayed
- Key risks and opportunities are shown
- Timeline is generated from Notion, Slack, and Google Drive
- Each insight has evidence
- User can ask follow-up questions in the iframe
