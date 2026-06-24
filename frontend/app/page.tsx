"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { Theme, Room, Message } from "../lib/types";
import {
  generateInChat,
  imageUrl,
  progressWsUrl,
  downloadImage,
  listChats,
  createChat,
  getChat,
  deleteChat,
  renameChat,
  dbMsgToLocal,
  listModels,
  setChatModel,
} from "../lib/api";
import styles from "./page.module.css";

// ── Themes ────────────────────────────────────────────────────────────────────
const THEMES: { id: Theme; name: string; bg: string; fg: string }[] = [
  { id: "dark", name: "다크", bg: "#0a0a0b", fg: "#f4f4f5" },
  { id: "light", name: "라이트", bg: "#fff", fg: "#18181b" },
  { id: "slate", name: "슬레이트", bg: "#0c0f16", fg: "#e6eaf2" },
  { id: "sand", name: "샌드", bg: "#faf9f6", fg: "#22201b" },
];

function uid() {
  return Math.random().toString(36).slice(2);
}

// Reference-use modes (Doc 14). pose disabled until openpose preprocessor lands.
type RefMode = "character" | "pose" | "vary";
const REF_MODES: { id: RefMode; label: string; tip: string; disabled?: boolean }[] = [
  { id: "character", label: "캐릭터 이식", tip: "이 캐릭터를 새 포즈·장면으로 (IPAdapter)" },
  { id: "pose", label: "포즈 이식", tip: "준비 중 — 이 자세로 다른 캐릭터를 (openpose 예정)", disabled: true },
  { id: "vary", label: "변형", tip: "이 이미지를 살짝 바꿔 (img2img)" },
];

// ── GenCard ───────────────────────────────────────────────────────────────────
function GenCard({
  msg,
  onLightbox,
}: {
  msg: Message;
  onLightbox: (path: string, params: Message["params"]) => void;
}) {
  const [progress, setProgress] = useState(0);
  const [label, setLabel] = useState("준비 중 …");
  const [flipped, setFlipped] = useState(false);

  // Real progress: subscribe to the backend WS while this card is generating.
  // ComfyUI emits no events during LLM-unload / checkpoint-load, so the bar sits
  // at 0% ("준비 중") until sampling starts, then tracks actual value/max.
  useEffect(() => {
    if (!msg.generating) return;
    const ws = new WebSocket(progressWsUrl());
    ws.onmessage = e => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === "progress" && typeof d.pct === "number") {
          setProgress(d.pct);
          setLabel(d.pct >= 99 ? "VAE 디코딩" : "샘플링 중 …");
        }
      } catch {
        // ignore non-JSON frames
      }
    };
    return () => ws.close();
  }, [msg.generating]);

  // Reveal: once the image arrives, fill the bar and flip to the result.
  useEffect(() => {
    if (!msg.imagePath) return;
    setProgress(100);
    setLabel("완료");
    const t = setTimeout(() => setFlipped(true), 250);
    return () => clearTimeout(t);
  }, [msg.imagePath]);

  const res = msg.params?.resolution;
  const wStr = res ? `${res.width}×${res.height}` : "832×1216";
  const stepsStr = msg.params ? `${msg.params.steps} steps · cfg ${msg.params.cfg}` : "28 steps · cfg 5.0";

  return (
    <div className={styles.flip3d + (flipped ? " " + styles.done : "")}>
      <div className={styles.flipInner}>
        {/* front — loading */}
        <div className={styles.faceFront}>
          <div className={styles.progressBar}>
            <i style={{ width: `${progress}%` }} />
          </div>
          <div className={styles.picPlaceholder}>
            <div className={styles.genStat}>
              <b>{progress}%</b>
              <span>{label}</span>
            </div>
          </div>
          <div className={styles.cardBar}>
            <span className={styles.tag}>{stepsStr}</span>
          </div>
        </div>
        {/* back — result */}
        <div className={styles.faceBack}>
          {msg.imagePath ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrl(msg.imagePath)}
              alt="생성된 이미지"
              className={styles.genImage}
              onClick={() => onLightbox(msg.imagePath!, msg.params)}
            />
          ) : (
            <div className={styles.picPlaceholder} />
          )}
          <div className={styles.cardBar}>
            <span className={styles.tag}>{wStr}</span>
            <span className={styles.spacer} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── ChatMessage ────────────────────────────────────────────────────────────────
function ChatMessage({
  msg,
  onLightbox,
}: {
  msg: Message;
  onLightbox: (path: string, params: Message["params"]) => void;
}) {
  if (msg.hero) {
    return (
      <div className={styles.hero}>
        <div className={styles.heroMark}>화</div>
        <h1>무엇을 그려볼까요?</h1>
        <p>한국어로 설명하면 의도를 해석해 프롬프트를 합성하고 그려냅니다.</p>
      </div>
    );
  }

  if (msg.role === "user") {
    return (
      <div className={styles.msgUser}>
        <div className={styles.av + " " + styles.avUser}>나</div>
        <div className={styles.bubbleUser}>
          {msg.referenceImage && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={msg.referenceImage} alt="첨부 이미지" className={styles.refThumb} />
          )}
          {msg.text && <p>{msg.text}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.msgAi}>
      <div className={styles.av + " " + styles.avAi}>화</div>
      <div className={styles.bubble}>
        {msg.typing && (
          <div className={styles.typing}>
            <span /><span /><span />
          </div>
        )}
        {msg.text && <p>{msg.text}</p>}
        {(msg.generating || msg.imagePath) && (
          <GenCard msg={msg} onLightbox={onLightbox} />
        )}
      </div>
    </div>
  );
}

// ── Lightbox ───────────────────────────────────────────────────────────────────
function Lightbox({
  imagePath,
  params,
  onClose,
}: {
  imagePath: string | null;
  params: Message["params"] | null;
  onClose: () => void;
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  if (!imagePath) return null;

  const res = params?.resolution;
  const wStr = res ? `${res.width}×${res.height}` : "832×1216";
  const stepsStr = params ? `${params.steps} steps · cfg ${params.cfg}` : "";

  return (
    <div className={styles.lightboxOverlay} onClick={onClose}>
      <button className={styles.lbClose} onClick={onClose}>✕</button>
      <div className={styles.lbContent} onClick={e => e.stopPropagation()}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={imageUrl(imagePath)} alt="확대 이미지" className={styles.lbImage} />
      </div>
      <div className={styles.lbInfo}>
        <span className={styles.tag}>{wStr}</span>
        {stepsStr && <span className={styles.tag}>{stepsStr}</span>}
        <button
          className={styles.tag}
          onClick={e => { e.stopPropagation(); downloadImage(imagePath); }}
          title="다운로드"
        >⬇ 다운로드</button>
      </div>
    </div>
  );
}

// ── Settings ───────────────────────────────────────────────────────────────────
function Settings({ theme, onTheme }: { theme: Theme; onTheme: (t: Theme) => void }) {
  const [models, setModels] = useState<string[]>([]);
  const [currentModel, setCurrentModel] = useState<string>("");

  useEffect(() => {
    listModels().then(data => {
      setModels(data.available);
      setCurrentModel(data.current);
    }).catch(() => {});
  }, []);

  async function handleModelChange(model: string) {
    setCurrentModel(model);
    try {
      await setChatModel(model);
    } catch {
      // revert shown selection on failure? No — optimistic; backend error non-fatal here
    }
  }

  return (
    <div className={styles.setWrap}>
      <div className={styles.setTitle}>설정</div>
      <div className={styles.setSub}>화면 테마와 생성 기본값을 조정합니다.</div>
      <h3 className={styles.setLabel}>테마</h3>
      <div className={styles.card}>
        <div className={styles.themes}>
          {THEMES.map(t => (
            <button
              key={t.id}
              className={styles.swatch + (t.id === theme ? " " + styles.swatchSel : "")}
              onClick={() => onTheme(t.id)}
            >
              <div className={styles.swatchPrev} style={{ background: t.bg, color: t.fg }}>
                <div className={styles.swatchL} />
                <div className={styles.swatchR} />
              </div>
              <div className={styles.swatchLbl}>
                {t.name}
                {t.id === theme && <span className={styles.swatchCk}>✓</span>}
              </div>
            </button>
          ))}
        </div>
      </div>
      <h3 className={styles.setLabel}>두뇌 / 동작</h3>
      <div className={styles.card}>
        <div className={styles.row}>
          <div className={styles.rowInfo}>
            <b>대화 모델</b>
            <small>의도 해석에 사용할 ollama 모델. NSFW 폴백은 고정.</small>
          </div>
          {models.length > 0 ? (
            <select
              className={styles.modelSelect}
              value={currentModel}
              onChange={e => handleModelChange(e.target.value)}
            >
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          ) : (
            <span className={styles.tag}>로드 중…</span>
          )}
        </div>
        <div className={styles.row}>
          <div className={styles.rowInfo}>
            <b>자기평가 Critic 루프</b>
            <small>생성 후 자동 품질검사 (Phase 3)</small>
          </div>
          <div className={styles.toggle} />
        </div>
        <div className={styles.row}>
          <div className={styles.rowInfo}>
            <b>NSFW 허용</b>
            <small>로컬 무검열 · 개인용</small>
          </div>
          <div className={styles.toggle + " " + styles.toggleOn} />
        </div>
      </div>
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────────
export default function Home() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const [theme, setTheme] = useState<Theme>("dark");
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [screen, setScreen] = useState<"chat" | "settings">("chat");
  const [lightbox, setLightbox] = useState<{ path: string; params: Message["params"] | null } | null>(null);
  const [attachedImage, setAttachedImage] = useState<string | null>(null); // base64 data URL
  const [refMode, setRefMode] = useState<RefMode>("character"); // how to use the reference (Doc 14)
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeRoom = rooms.find(r => r.id === activeId) ?? rooms[0] ?? { id: "", name: "", messages: [], loaded: true };
  const recentImages = rooms
    .flatMap(r => r.messages)
    .filter(m => m.imagePath)
    .slice(-10)
    .reverse();

  const applyTheme = useCallback((t: Theme) => {
    document.documentElement.setAttribute("data-theme", t);
    setTheme(t);
  }, []);

  // Load chat list from DB on mount
  useEffect(() => {
    listChats().then(async dbRooms => {
      if (dbRooms.length === 0) {
        const r = await createChat("새 작업");
        const room: Room = { id: r.id, name: r.name, messages: [{ id: "h1", role: "ai", hero: true }], loaded: true };
        setRooms([room]);
        setActiveId(room.id);
      } else {
        const localRooms: Room[] = dbRooms.map(r => ({
          id: r.id,
          name: r.name,
          messages: [{ id: "h-" + r.id, role: "ai", hero: true }],
          loaded: false,
        }));
        setRooms(localRooms);
        setActiveId(localRooms[0].id);
      }
    }).catch(() => {
      // Backend not available — fall back to local state
      const fallback: Room = { id: "local-1", name: "새 작업", messages: [{ id: "h1", role: "ai", hero: true }], loaded: true };
      setRooms([fallback]);
      setActiveId(fallback.id);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [activeRoom?.messages]);

  async function addRoom() {
    try {
      const r = await createChat(`작업 ${rooms.length + 1}`);
      const newRoom: Room = { id: r.id, name: r.name, messages: [{ id: uid(), role: "ai", hero: true }], loaded: true };
      setRooms(prev => [...prev, newRoom]);
      setActiveId(r.id);
      setScreen("chat");
    } catch {
      // fallback: local room
      const id = uid();
      const newRoom: Room = { id, name: `작업 ${rooms.length + 1}`, messages: [{ id: uid(), role: "ai", hero: true }], loaded: true };
      setRooms(prev => [...prev, newRoom]);
      setActiveId(id);
      setScreen("chat");
    }
  }

  function delRoom(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    deleteChat(id).catch(() => {});
    setRooms(prev => {
      const next = prev.filter(r => r.id !== id);
      if (next.length === 0) {
        const fallback: Room = { id: uid(), name: "새 작업", messages: [{ id: uid(), role: "ai", hero: true }], loaded: true };
        setActiveId(fallback.id);
        return [fallback];
      }
      if (id === activeId) setActiveId(next[next.length - 1].id);
      return next;
    });
  }

  async function loadRoomMessages(roomId: string) {
    try {
      const data = await getChat(roomId);
      const messages: Message[] = data.messages.length > 0
        ? data.messages.map(dbMsgToLocal)
        : [{ id: "h-" + roomId, role: "ai", hero: true }];
      setRooms(prev => prev.map(r => r.id === roomId ? { ...r, messages, loaded: true } : r));
    } catch {
      // keep existing messages
    }
  }

  function updateRoom(id: string, updater: (r: Room) => Room) {
    setRooms(prev => prev.map(r => r.id === id ? updater(r) : r));
  }

  async function sendMessage(text?: string) {
    const msg = (text ?? taRef.current?.value ?? "").trim();
    if (!msg && !attachedImage) return;
    if (taRef.current) { taRef.current.value = ""; taRef.current.style.height = "auto"; }

    const roomId = activeId;
    const userMsgId = uid();
    const aiMsgId = uid();
    const refImg = attachedImage;
    setAttachedImage(null);

    // Capture history BEFORE adding this turn's messages (for backend context)
    const historySnapshot = (rooms.find(r => r.id === roomId)?.messages ?? [])
      .filter(m => !m.hero);

    const displayText = msg || "이미지를 첨부했습니다.";

    const newName = displayText.length > 20 ? displayText.slice(0, 20) + "…" : displayText;
    renameChat(roomId, newName).catch(() => {});
    updateRoom(roomId, r => ({
      ...r,
      name: newName,
      messages: [
        ...r.messages.filter(m => !m.hero),
        { id: userMsgId, role: "user", text: msg || undefined, referenceImage: refImg ?? undefined },
        { id: aiMsgId, role: "ai", typing: true },
      ],
    }));

    try {
      const result = await generateInChat(roomId, msg || "이미지를 참고해서 그림을 그려줘", historySnapshot, refImg ?? undefined, refImg ? refMode : undefined);

      updateRoom(roomId, r => ({
        ...r,
        messages: r.messages.map(m =>
          m.id === aiMsgId
            ? {
                ...m,
                typing: false,
                text: result.image_path
                  ? "생성 완료. 클릭하면 확대할 수 있습니다."
                  : "생성에 실패했습니다.",
                generating: !!result.image_path,
                imagePath: result.image_path ?? undefined,
                params: result.params ?? undefined,
              }
            : m
        ),
      }));
    } catch (err) {
      updateRoom(roomId, r => ({
        ...r,
        messages: r.messages.map(m =>
          m.id === aiMsgId
            ? { ...m, typing: false, text: `오류: ${err instanceof Error ? err.message : "알 수 없는 오류"}` }
            : m
        ),
      }));
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      setAttachedImage(ev.target?.result as string);
    };
    reader.readAsDataURL(file);
    // Reset input so same file can be re-selected
    e.target.value = "";
  }

  return (
    <div
      className={
        styles.app +
        (!leftOpen ? " " + styles.leftCollapsed : "") +
        (!rightOpen ? " " + styles.rightCollapsed : "")
      }
    >
      {/* Left sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles.brandMark}>화</div>
          <div>
            <b>화가 에이전트</b>
            <span>local image-gen</span>
          </div>
        </div>
        <button className={styles.newChat} onClick={addRoom}>＋ 새 채팅방</button>
        <div className={styles.rooms}>
          <div className={styles.roomsLabel}>채팅방</div>
          {rooms.map(r => (
            <div
              key={r.id}
              className={styles.room + (r.id === activeId ? " " + styles.roomActive : "")}
              onClick={() => {
                setActiveId(r.id);
                setScreen("chat");
                if (!r.loaded) loadRoomMessages(r.id);
              }}
            >
              <span className={styles.roomName}>{r.name}</span>
              <button className={styles.roomDel} onClick={e => delRoom(r.id, e)}>×</button>
            </div>
          ))}
        </div>
        <div className={styles.sideFoot}>
          <button
            className={styles.navBtn + (screen === "chat" ? " " + styles.navActive : "")}
            onClick={() => setScreen("chat")}
          >채팅</button>
          <button
            className={styles.navBtn + (screen === "settings" ? " " + styles.navActive : "")}
            onClick={() => setScreen("settings")}
          >설정</button>
        </div>
      </aside>

      {/* Main area */}
      <main className={styles.main}>
        <div className={styles.topbar}>
          <button className={styles.iconBtn} onClick={() => setLeftOpen(v => !v)} title="사이드바">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <line x1="9" y1="4" x2="9" y2="20" />
            </svg>
          </button>
          <h2 className={styles.topTitle}>
            {screen === "settings" ? "설정" : activeRoom.name}
          </h2>
          {screen === "chat" && (
            <span className={styles.pill}>
              <span className={styles.pillDot} />
              SDXL · illustrious
            </span>
          )}
          <button className={styles.iconBtn} onClick={() => setRightOpen(v => !v)} title="최근 생성">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <line x1="15" y1="4" x2="15" y2="20" />
            </svg>
          </button>
        </div>

        {screen === "chat" ? (
          <>
            <div className={styles.chatScroll} ref={chatScrollRef}>
              <div className={styles.chatWrap}>
                {activeRoom.messages.map(msg => (
                  <ChatMessage
                    key={msg.id}
                    msg={msg}
                    onLightbox={(path, params) => setLightbox({ path, params })}
                  />
                ))}
              </div>
            </div>

            <div className={styles.composer}>
              {/* hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                style={{ display: "none" }}
                onChange={handleFileSelect}
              />
              {/* attached image preview */}
              {attachedImage && (
                <div className={styles.attachPreview}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={attachedImage} alt="첨부 이미지" className={styles.attachThumb} />
                  <div className={styles.attachInfo}>
                    <span>레퍼런스 활용 방식</span>
                    <div className={styles.modeSelect} role="group" aria-label="레퍼런스 모드">
                      {REF_MODES.map(m => (
                        <button
                          key={m.id}
                          type="button"
                          className={styles.modeOpt + (refMode === m.id ? " " + styles.modeOptActive : "")}
                          title={m.tip}
                          disabled={m.disabled}
                          onClick={() => setRefMode(m.id)}
                        >{m.label}</button>
                      ))}
                    </div>
                  </div>
                  <button
                    className={styles.attachClear}
                    onClick={() => setAttachedImage(null)}
                    title="첨부 해제"
                  >✕</button>
                </div>
              )}
              <div className={styles.composerInner}>
                <button
                  className={styles.attach + (attachedImage ? " " + styles.attachActive : "")}
                  title="레퍼런스 이미지 첨부"
                  onClick={() => fileInputRef.current?.click()}
                >＋</button>
                <textarea
                  ref={taRef}
                  className={styles.composerTa}
                  rows={1}
                  placeholder="만들고 싶은 그림을 설명해 주세요"
                  onInput={e => {
                    const t = e.currentTarget;
                    t.style.height = "auto";
                    t.style.height = t.scrollHeight + "px";
                  }}
                  onKeyDown={e => {
                    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
                  }}
                />
                <button className={styles.sendBtn} onClick={() => sendMessage()}>↑</button>
              </div>
              <div className={styles.quickChips}>
                <button className={styles.chip} onClick={() => sendMessage("분홍 머리 트윈테일 소녀가 창가에서 웃으며")}>예시 프롬프트</button>
                <button className={styles.chip} onClick={() => sendMessage("노을 지는 판타지 도시 풍경")}>풍경</button>
                <button className={styles.chip} onClick={() => sendMessage("몽환적인 수채화풍 인물")}>스타일</button>
              </div>
            </div>
          </>
        ) : (
          <div className={styles.chatScroll}>
            <Settings theme={theme} onTheme={applyTheme} />
          </div>
        )}
      </main>

      {/* Right sidebar */}
      <aside className={styles.rside}>
        <div className={styles.rsideHead}>
          <b>최근 생성</b>
          <span className={styles.rMeta}>{recentImages.length}</span>
          <button className={styles.iconBtn} onClick={() => setRightOpen(v => !v)} style={{ marginLeft: "auto" }}>✕</button>
        </div>
        <div className={styles.rgrid}>
          {recentImages.map(m => (
            <div
              key={m.id}
              className={styles.thumb}
              onClick={() => setLightbox({ path: m.imagePath!, params: m.params ?? null })}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={imageUrl(m.imagePath!)} alt="썸네일" className={styles.thumbImg} />
              <div className={styles.thumbCap}>{m.text}</div>
            </div>
          ))}
          {recentImages.length === 0 && (
            <p className={styles.emptyHint}>생성한 이미지가 여기에 표시됩니다</p>
          )}
        </div>
      </aside>

      {/* Lightbox */}
      {lightbox && (
        <Lightbox
          imagePath={lightbox.path}
          params={lightbox.params}
          onClose={() => setLightbox(null)}
        />
      )}
    </div>
  );
}
