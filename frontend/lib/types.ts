export type Theme = "dark" | "light" | "slate" | "sand";

export interface GenParams {
  steps: number;
  cfg: number;
  sampler: string;
  scheduler: string;
  resolution: { width: number; height: number };
  denoise: number;
}

export interface GenResult {
  image_path: string | null;
  params: GenParams | null;
  critique: { passed: boolean; issues: string[]; retry: boolean } | null;
  seed?: number | null;
  generation_id?: string | null;
}

// Local (in-memory) message shape — includes UI-only fields
export interface Message {
  id: string;
  role: "user" | "ai";
  text?: string;
  typing?: boolean;
  hero?: boolean;
  imagePath?: string;       // generated output path (backend)
  referenceImage?: string;  // attached input image (base64 data URL)
  params?: GenParams;
  generating?: boolean;
}

// Local room — messages may be empty until loaded from DB
export interface Room {
  id: string;
  name: string;
  messages: Message[];
  loaded?: boolean;  // true once messages have been fetched from DB
}

// DB response shapes
export interface DbRoom {
  id: string;
  name: string;
  updated_at: number;
}

export interface DbMessage {
  id: string;
  role: string;
  text: string | null;
  image_path: string | null;
  reference_image: string | null;
  generation_id: string | null;
  created_at: number;
}
