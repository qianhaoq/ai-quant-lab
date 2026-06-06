const LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql";

export class LinearClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }

  async request(query, variables = {}) {
    const response = await fetch(LINEAR_GRAPHQL_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: this.apiKey,
      },
      body: JSON.stringify({ query, variables }),
    });

    const body = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(`Linear API HTTP ${response.status}: ${JSON.stringify(body)}`);
    }
    if (body?.errors?.length) {
      throw new Error(`Linear GraphQL 错误：${body.errors.map((error) => error.message).join("; ")}`);
    }
    return body.data;
  }
}

export async function loadTeamContext(client, config) {
  const data = await client.request(`
    query RunnerTeams {
      teams(first: 100) {
        nodes {
          id
          key
          name
          states(first: 100) {
            nodes {
              id
              name
              type
            }
          }
        }
      }
    }
  `);

  const team = data.teams.nodes.find((item) => item.key === config.teamKey || item.name === config.teamKey);
  if (!team) {
    throw new Error(`找不到 Linear team：${config.teamKey}`);
  }

  const states = new Map(team.states.nodes.map((state) => [state.name, state]));
  const requiredStates = [
    config.readyState,
    config.runningState,
    config.aiReviewState,
    config.humanReviewState,
    config.failureState,
  ];
  const missing = requiredStates.filter((stateName) => !states.has(stateName));
  if (missing.length) {
    throw new Error(`Linear team ${team.name} 缺少状态：${missing.join(", ")}`);
  }

  return {
    team,
    states,
  };
}

export async function listQueueIssues(client, config, context) {
  const data = await client.request(
    `
    query QueueIssues($teamId: ID!, $stateId: ID!, $first: Int!) {
      issues(
        first: $first,
        filter: {
          team: { id: { eq: $teamId } },
          state: { id: { eq: $stateId } }
        }
      ) {
        nodes {
          id
          identifier
          title
          description
          priority
          estimate
          url
          branchName
          createdAt
          updatedAt
          state {
            id
            name
            type
          }
          assignee {
            name
          }
          labels {
            nodes {
              id
              name
            }
          }
          project {
            id
            name
          }
        }
      }
    }
  `,
    {
      teamId: context.team.id,
      stateId: context.states.get(config.readyState).id,
      first: config.selectionLimit,
    },
  );

  const issues = data.issues.nodes.filter((issue) => {
    if (config.issue && issue.identifier !== config.issue) {
      return false;
    }
    return (issue.labels?.nodes ?? []).some((label) => label.name === config.requiredLabel);
  });

  return issues;
}

export async function getIssueDetails(client, issueId) {
  const data = await client.request(
    `
    query IssueDetails($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        description
        priority
        estimate
        url
        branchName
        createdAt
        updatedAt
        state {
          id
          name
          type
        }
        labels {
          nodes {
            id
            name
          }
        }
        project {
          id
          name
        }
        comments(first: 50) {
          nodes {
            id
            body
            createdAt
            user {
              name
            }
          }
        }
      }
    }
  `,
    { id: issueId },
  );

  return data.issue;
}

export async function updateIssueState(client, issue, state) {
  const data = await client.request(
    `
    mutation RunnerIssueUpdate($id: String!, $stateId: String!) {
      issueUpdate(id: $id, input: { stateId: $stateId }) {
        success
        issue {
          id
          identifier
          state {
            name
          }
        }
      }
    }
  `,
    {
      id: issue.identifier,
      stateId: state.id,
    },
  );

  return data.issueUpdate.issue;
}

export async function createComment(client, issue, body) {
  const data = await client.request(
    `
    mutation RunnerCommentCreate($issueId: String!, $body: String!) {
      commentCreate(input: { issueId: $issueId, body: $body }) {
        success
        comment {
          id
        }
      }
    }
  `,
    {
      issueId: issue.id,
      body,
    },
  );

  return data.commentCreate.comment;
}

export async function createAttachment(client, issue, { title, url }) {
  const data = await client.request(
    `
    mutation RunnerAttachmentCreate($issueId: String!, $title: String!, $url: String!) {
      attachmentCreate(input: { issueId: $issueId, title: $title, url: $url }) {
        success
        attachment {
          id
        }
      }
    }
  `,
    {
      issueId: issue.id,
      title,
      url,
    },
  );

  return data.attachmentCreate.attachment;
}

export function countRunnerAttempts(issue) {
  const comments = issue.comments?.nodes ?? [];
  return comments.filter((comment) => comment.body.includes("Agent Runner 已认领")).length;
}
