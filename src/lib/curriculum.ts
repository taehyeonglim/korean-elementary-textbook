export interface CurriculumSource {
  mcp: string;
  method: "get_standard";
  topicMethod?: "get_topic";
  version?: string;
}

/**
 * An immutable capture of a curriculum MCP response used during workbook
 * authoring. These records are private source evidence, never browser inputs.
 */
export interface CurriculumSnapshot {
  schemaVersion: 1;
  source: CurriculumSource;
  retrievedAt: string;
  standard: Record<string, unknown>;
  topics: Array<Record<string, unknown>>;
}
