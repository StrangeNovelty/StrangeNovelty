export type Mode = "plot" | "realm" | "npc" | "monster" | "item";
export type Choice = { id: string; label: string; detail?: string };
export type Card = {
  id?: string;
  text: string;
  category: string;
  manual: boolean;
};
export type BrainstormSummary = {
  id: string;
  title: string;
  mode: Mode;
  modeLabel: string;
  cards: Card[];
  result: string;
  updatedAt: string;
};
export type Brainstorm = BrainstormSummary & {
  activeWork: Choice | null;
  characters: Choice[];
  selectedCharacterIds: string[];
  focus: string;
  exclusions: string;
  authorNotes: string;
  threatLevel: string;
  discipline: string;
  resultState: string;
  suggestionId: string | null;
  categories: string[];
};
export type ChatSummary = { id: string; title: string; updatedAt: string };
export type ChatMessage = {
  id: string;
  role: "author" | "assistant" | "system";
  content: string;
  suggestionId?: string | null;
};
export type Chat = ChatSummary & {
  messages: ChatMessage[];
  characters: Choice[];
  selectedCharacterIds: string[];
  activeWork: Choice | null;
};
