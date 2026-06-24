import type { DbMessage, DbRoom, GenResult, Message } from "./types";

const BASE = "http://localhost:8000";

// --- Generation ---

export async function generateInChat(
  chatId: string,
  message: string,
  history: Message[],
  referenceImage?: string,
  referenceMode?: string,
): Promise<GenResult> {
  const body: Record<string, unknown> = {
    message,
    chat_id: chatId,
    history: history
      .filter(m => !m.hero && !m.typing && m.text)
      .map(m => ({ role: m.role === "user" ? "user" : "ai", text: m.text! })),
  };
  if (referenceImage) {
    body.reference_image = referenceImage.replace(/^data:[^;]+;base64,/, "");
    if (referenceMode) body.reference_mode = referenceMode;
  }
  const res = await fetch(`${BASE}/chats/${chatId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`Generation failed (${res.status}): ${err}`);
  }
  return res.json();
}

// Backend WebSocket that streams real generation progress (relays ComfyUI sampling events)
export function progressWsUrl(): string {
  return BASE.replace(/^http/, "ws") + "/ws/progress";
}

export function imageUrl(imagePath: string): string {
  const filename = imagePath.replace(/\\/g, "/").split("/").pop() ?? imagePath;
  return `${BASE}/images/${filename}`;
}

export function downloadUrl(imagePath: string): string {
  return `${imageUrl(imagePath)}?download=1`;
}

export function downloadImage(imagePath: string): void {
  const a = document.createElement("a");
  a.href = downloadUrl(imagePath);
  a.click();
}

// --- Chat (room) CRUD ---

export async function listChats(): Promise<DbRoom[]> {
  const res = await fetch(`${BASE}/chats`);
  if (!res.ok) return [];
  return res.json();
}

export async function createChat(name?: string): Promise<DbRoom> {
  const res = await fetch(`${BASE}/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name ?? "새 채팅" }),
  });
  if (!res.ok) throw new Error("Failed to create chat");
  return res.json();
}

export async function getChat(chatId: string): Promise<{ room: { id: string; name: string }; messages: DbMessage[] }> {
  const res = await fetch(`${BASE}/chats/${chatId}`);
  if (!res.ok) throw new Error("Failed to load chat");
  return res.json();
}

export async function renameChat(chatId: string, name: string): Promise<void> {
  await fetch(`${BASE}/chats/${chatId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function deleteChat(chatId: string): Promise<void> {
  await fetch(`${BASE}/chats/${chatId}`, { method: "DELETE" });
}

// --- Model management ---

export async function listModels(): Promise<{ available: string[]; current: string }> {
  const res = await fetch(`${BASE}/models`);
  if (!res.ok) return { available: [], current: "" };
  return res.json();
}

export async function setChatModel(model: string): Promise<void> {
  await fetch(`${BASE}/models/chat`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
  });
}

// Convert a DB message row to the local Message shape (UI-only fields omitted)
export function dbMsgToLocal(m: DbMessage): Message {
  return {
    id: m.id,
    role: m.role as "user" | "ai",
    text: m.text ?? undefined,
    imagePath: m.image_path ?? undefined,
  };
}
