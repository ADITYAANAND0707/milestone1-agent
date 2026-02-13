/**
 * MCP client for the design system server.
 * Connects to http://127.0.0.1:3845/mcp and exposes tools/resources.
 */

import {
  CallToolResultSchema,
  Client,
  ListResourcesResultSchema,
  ListToolsResultSchema,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";

const MCP_URL = "http://127.0.0.1:3845/mcp";

export type DesignSystemContext = {
  tools: { name: string; description?: string; inputSchema?: unknown }[];
  resources: { uri: { uri: string }; name?: string }[];
  resourceContents: Record<string, string>;
};

let client: Client | null = null;
let transport: StreamableHTTPClientTransport | null = null;

export async function connect(): Promise<Client> {
  if (client) return client;

  client = new Client(
    {
      name: "milestone1-agent",
      version: "1.0.0",
    },
    { capabilities: {} }
  );

  client.onerror = (err) => {
    console.error("[MCP] Client error:", err);
  };

  transport = new StreamableHTTPClientTransport(new URL(MCP_URL));
  await client.connect(transport);
  return client;
}

export async function disconnect(): Promise<void> {
  if (transport) {
    await transport.close();
    transport = null;
  }
  client = null;
}

export async function listTools(): Promise<Tool[]> {
  const c = client ?? (await connect());
  const result = await c.request(
    { method: "tools/list", params: {} },
    ListToolsResultSchema
  );
  return result.tools;
}

export async function callTool(
  name: string,
  args: Record<string, unknown> = {}
): Promise<string> {
  const c = client ?? (await connect());
  const result = await c.request(
    {
      method: "tools/call",
      params: { name, arguments: args },
    },
    CallToolResultSchema
  );
  const parts: string[] = [];
  for (const item of result.content) {
    if (item.type === "text") parts.push(item.text);
  }
  return parts.join("\n");
}

export async function listResources(): Promise<Resource[]> {
  const c = client ?? (await connect());
  const result = await c.request(
    { method: "resources/list", params: {} },
    ListResourcesResultSchema
  );
  return result.resources;
}

export async function readResource(uri: string): Promise<string> {
  const c = client ?? (await connect());
  const result = await c.request(
    { method: "resources/read", params: { uri } },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (x: any) => x
  );
  const contents = (result as { contents?: { text?: string }[] }).contents;
  if (contents?.[0] && "text" in contents[0]) return contents[0].text;
  return JSON.stringify(result);
}

/**
 * Gather all design system context (tools + resources) for the agent.
 */
export async function getDesignSystemContext(): Promise<DesignSystemContext> {
  const c = client ?? (await connect());
  const tools = await listTools();
  const resources = await listResources();
  const resourceContents: Record<string, string> = {};
  for (const r of resources) {
    try {
      resourceContents[r.uri.uri] = await readResource(r.uri.uri);
    } catch {
      resourceContents[r.uri.uri] = "";
    }
  }
  return { tools, resources, resourceContents };
}
