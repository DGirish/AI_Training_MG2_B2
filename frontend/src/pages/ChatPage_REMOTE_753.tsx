import { FormEvent, useEffect, useRef, useState } from "react";

import {
  createThread,
  deleteAttachment,
  deleteThread,
  getThread,
  ingestPdfForRag,
  listThreads,
  ragChat,
  streamChatWithAttachments,
  updateThread,
  uploadAttachments,
} from "../lib/api";
import { ChatThread, ChatMessage, User, Attachment } from "../types/index";
import { AttachmentButton, AttachmentPreview, MessageAttachments } from "../components/attachments";

interface ChatPageProps {
  user: User;
  token: string;
  onLogout: () => void;
}

function formatMessageContent(text: string): string {
  // Convert **text** to <strong>text</strong>
  let formatted = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  // Convert line breaks to <br>
  formatted = formatted.replace(/\n/g, "<br>");
  return formatted;
}

function toChatMessages(messages: ChatThread["messages"]): ChatMessage[] {
  return (
    messages?.map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      attachment_ids: msg.attachment_ids,
      attachments: msg.attachments,
    })) ?? []
  );
}

function appendAssistantToken(
  currentMessages: ChatMessage[],
  assistantId: string,
  tokenChunk: string
): ChatMessage[] {
  return currentMessages.map((item) => {
    if (item.id !== assistantId) {
      return item;
    }

    return { ...item, content: `${item.content}${tokenChunk}` };
  });
}

function getMessageLabel(role: ChatMessage["role"]): string {
  return role === "user" ? "You" : "Stackyon AI";
}

function getMessageBadge(role: ChatMessage["role"]): string {
  return role === "user" ? "YU" : "AI";
}

function mergeUpdatedThread(existingThreads: ChatThread[], updatedThread: ChatThread): ChatThread[] {
  const merged = [updatedThread, ...existingThreads.filter((item) => item.id !== updatedThread.id)];
  return merged.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
}

function patchAttachmentIndexState(
  list: Attachment[],
  attachmentId: string,
  indexedStatus: string,
  indexingError?: string | null
): Attachment[] {
  return list.map((item) => (
    item.id === attachmentId
      ? {
          ...item,
          indexed_status: indexedStatus,
          indexing_error: indexingError ?? null,
        }
      : item
  ));
}

export function ChatPage({ user, token, onLogout }: Readonly<ChatPageProps>) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThread, setActiveThread] = useState<ChatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [generateImageMode, setGenerateImageMode] = useState(false);
  const [ragModeByThread, setRagModeByThread] = useState<Record<string, { attachmentId: string; fileName: string }>>({});
  const [ragBusy, setRagBusy] = useState(false);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const hasActiveThread = activeThread !== null;
  const activeRag = activeThread ? ragModeByThread[activeThread.id] : undefined;
  const activeRagAttachmentId = activeRag?.attachmentId ?? null;
  const activeRagFileName = activeRag?.fileName ?? null;
  let sendButtonLabel = "Send";
  if (generateImageMode) {
    sendButtonLabel = "Generate";
  }
  if (isLoading) {
    sendButtonLabel = generateImageMode ? "Generating..." : "Sending...";
  }

  useEffect(() => {
    loadThreads();
  }, []);

  useEffect(() => {
    if (!messagesRef.current) {
      return;
    }
    messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [messages, activeThread?.id]);

  async function loadThreads() {
    try {
      const result = await listThreads(token);
      setThreads(result);
      if (result.length === 0) {
        setActiveThread(null);
        setMessages([]);
        return;
      }

      const nextActiveThread = activeThread
        ? result.find((thread) => thread.id === activeThread.id) ?? result[0]
        : result[0];
      setActiveThread(nextActiveThread);
      setMessages(toChatMessages(nextActiveThread.messages));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load threads");
    }
  }

  async function handleCreateThread(title = "New Chat") {
    const cleanedTitle = title.trim() || "New Chat";

    try {
      const thread = await createThread(token, cleanedTitle);
      setThreads((prev) => [thread, ...prev]);
      setActiveThread(thread);
      setMessages(toChatMessages(thread.messages));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create thread");
    }
  }

  async function handleRenameThread(thread: ChatThread, e: React.MouseEvent) {
    e.stopPropagation();

    const nextTitle = globalThis.prompt("Rename thread", thread.title)?.trim();
    if (!nextTitle || nextTitle === thread.title) {
      return;
    }

    try {
      const updated = await updateThread(token, thread.id, nextTitle);
      setThreads((prev) => prev.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)));
      if (activeThread?.id === updated.id) {
        setActiveThread((prev) => (prev ? { ...prev, title: updated.title, updated_at: updated.updated_at } : prev));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rename thread");
    }
  }

  async function handleSelectThread(thread: ChatThread) {
    setActiveThread(thread);
    setMessages(toChatMessages(thread.messages));
    setError(null);
  }

  async function handleDeleteThread(thread: ChatThread, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await deleteThread(token, thread.id);
      setThreads((prev) => prev.filter((t) => t.id !== thread.id));
      if (activeThread?.id === thread.id) {
        setActiveThread(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete thread");
    }
  }

  async function refreshThreadMessages() {
    if (!activeThread) return;
    try {
      const thread = await getThread(token, activeThread.id);
      setActiveThread(thread);
      setMessages(toChatMessages(thread.messages));
      setThreads((prev) => mergeUpdatedThread(prev, thread));
    } catch {
      // Ignore refresh failures; current message stream already rendered in UI.
    }
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!input.trim() && attachments.length === 0) return;
    if (!activeThread || isLoading) return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36).slice(2),
      role: "user",
      content: input,
      attachment_ids: attachments.map((a) => a.id),
      attachments,
    };
    const assistantId = Math.random().toString(36).slice(2);

    setError(null);
    setInput("");
    setAttachments([]);
    setIsLoading(true);
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantId, role: "assistant", content: "" },
    ]);

    try {
      if (activeRagAttachmentId) {
        const ragResponse = await ragChat(token, activeThread.id, activeRagAttachmentId, userMessage.content);
        setMessages((prev) => prev.map((item) => (
          item.id === assistantId ? { ...item, content: ragResponse.answer } : item
        )));
        setIsLoading(false);
        void refreshThreadMessages();
      } else {
        const attachmentIds = attachments.map((a) => a.id);
        await streamChatWithAttachments(token, activeThread.id, userMessage.content, attachmentIds, {
          onToken(token) {
            setMessages((prev) => appendAssistantToken(prev, assistantId, token));
          },
          onDone() {
            setIsLoading(false);
            void refreshThreadMessages();
          },
          onError(messageText) {
            setError(messageText);
            setIsLoading(false);
          },
        }, generateImageMode);
      }
      setGenerateImageMode(false);
    } catch (err) {
      const messageText = err instanceof Error ? err.message : "Unexpected error";
      setError(messageText);
      setIsLoading(false);
    }
  }

  async function handleRemoveAttachment(attachmentId: string) {
    try {
      await deleteAttachment(token, attachmentId);
      setAttachments((prev) => prev.filter((a) => a.id !== attachmentId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove attachment");
    }
  }

  async function handleUploadFiles(files: File[]) {
    if (!activeThread) {
      setError("Select a thread before uploading files");
      return;
    }

    try {
      const uploaded = await uploadAttachments(token, activeThread.id, files);
      setAttachments((prev) => [...prev, ...uploaded.attachments]);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload files");
    }
  }

  function updateAttachmentIndexedStatus(attachmentId: string, indexedStatus: string, indexingError?: string | null) {
    setMessages((prev) => prev.map((message) => {
      if (!message.attachments || message.attachments.length === 0) {
        return message;
      }

      const nextAttachments = patchAttachmentIndexState(
        message.attachments,
        attachmentId,
        indexedStatus,
        indexingError
      );

      return { ...message, attachments: nextAttachments };
    }));

    setAttachments((prev) => patchAttachmentIndexState(prev, attachmentId, indexedStatus, indexingError));
  }

  async function handleAskPdf(attachment: Attachment) {
    if (!activeThread) {
      setError("Select a thread before enabling PDF mode");
      return;
    }

    setError(null);
    updateAttachmentIndexedStatus(attachment.id, "indexing", null);
    setRagBusy(true);
    try {
      const ingestResponse = await ingestPdfForRag(token, activeThread.id, attachment.id);
      if (ingestResponse.indexed_status !== "indexed") {
        throw new Error("PDF indexing did not complete successfully");
      }

      updateAttachmentIndexedStatus(attachment.id, "indexed", null);

      setRagModeByThread((prev) => ({
        ...prev,
        [activeThread.id]: {
          attachmentId: attachment.id,
          fileName: attachment.original_filename,
        },
      }));
    } catch (err) {
      const errorText = err instanceof Error ? err.message : "Failed to enable PDF RAG mode";
      updateAttachmentIndexedStatus(attachment.id, "failed", errorText);
      setError(err instanceof Error ? err.message : "Failed to enable PDF RAG mode");
    } finally {
      setRagBusy(false);
    }
  }

  function handleExitRagMode() {
    if (!activeThread) {
      return;
    }

    setRagModeByThread((prev) => {
      const next = { ...prev };
      delete next[activeThread.id];
      return next;
    });
  }

  return (
    <div className="chat-layout">
      <aside className="chat-sidebar">
        <div className="sidebar-header">
          <h2>Threads</h2>
          <button onClick={() => handleCreateThread()} className="new-thread-btn" title="Create new chat">
            +
          </button>
        </div>

        <div className="threads-list">
          {threads.map((thread) => (
            <div
              key={thread.id}
              className={`thread-item ${activeThread?.id === thread.id ? "active" : ""}`}
            >
              <button
                type="button"
                className="thread-item-button"
                onClick={() => handleSelectThread(thread)}
              >
                <div className="thread-item-copy">
                  <span className="thread-item-title">{thread.title}</span>
                  <span className="thread-item-meta">Open conversation</span>
                </div>
              </button>
              <button
                type="button"
                className="thread-action-btn"
                title="Rename thread"
                onClick={(e) => handleRenameThread(thread, e)}
              >
                ✎
              </button>
              <button
                type="button"
                className="delete-btn"
                onClick={(e) => handleDeleteThread(thread, e)}
                title="Delete thread"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <p>{user.email}</p>
          <button onClick={onLogout} className="logout-btn">
            Logout
          </button>
        </div>
      </aside>

      <main className="chat-main">
        {hasActiveThread ? (
          <>
            <header className="chat-header-container">
              <div className="chat-header-content">
                <h1 className="chat-title">Stackyon AI Chat</h1>
                <p className="chat-subtitle">Powered by Gemini via LiteLLM</p>
                {activeRagAttachmentId && activeRagFileName && (
                  <div className="rag-mode-banner">
                    <span>RAG mode: Asking {activeRagFileName}</span>
                    <button type="button" className="rag-exit-btn" onClick={handleExitRagMode}>
                      Exit
                    </button>
                  </div>
                )}
              </div>
            </header>

            <div className="chat-messages" ref={messagesRef}>
              {messages.length === 0 ? (
                <div className="chat-conversation-empty">
                  <h3>Start the conversation</h3>
                  <p>Send the first message in this thread to begin generating responses.</p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className={`message-row message-row-${msg.role}`}>
                    <div className={`message-bubble message-bubble-${msg.role}`}>
                      <div className="message-content">
                        {msg.role === "assistant" && msg.content && (
                          <div className="message-text" dangerouslySetInnerHTML={{ __html: formatMessageContent(msg.content) }} />
                        )}
                        {msg.role === "user" && <div className="message-text">{msg.content}</div>}
                        {msg.role === "assistant" && !msg.content && isLoading && (
                          <div className="message-text">...</div>
                        )}
                      </div>
                      <MessageAttachments
                        attachments={msg.attachments ?? []}
                        token={token}
                        onAskPdf={handleAskPdf}
                        activeRagAttachmentId={activeRagAttachmentId}
                        ragBusy={ragBusy || isLoading}
                      />
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="chat-input-container">
              {attachments.length > 0 && (
                <div className="attachment-list">
                  {attachments.map((attachment) => (
                    <AttachmentPreview
                      key={attachment.id}
                      attachment={attachment}
                      onRemove={() => handleRemoveAttachment(attachment.id)}
                    />
                  ))}
                </div>
              )}

              <form onSubmit={handleSendMessage} className="chat-input-form">
                <div className="chat-input-row">
                  <AttachmentButton onFilesSelected={handleUploadFiles} onError={(error) => setError(error)} disabled={isLoading} />
                  <button
                    type="button"
                    className={`image-mode-btn ${generateImageMode ? "active" : ""}`}
                    onClick={() => setGenerateImageMode((prev) => !prev)}
                    disabled={isLoading}
                    title="Toggle image generation mode"
                  >
                    🎨
                  </button>
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={generateImageMode ? "Describe the image you want to generate" : "Type a message..."}
                    disabled={isLoading}
                    className="chat-input"
                  />
                  <button type="submit" disabled={isLoading || (!input.trim() && attachments.length === 0)} className="send-btn">
                    {sendButtonLabel}
                  </button>
                </div>
              </form>
            </div>

            {error && <p className="chat-error">{error}</p>}
          </>
        ) : (
          <div className="chat-empty">
            <div className="chat-empty-card">
              <h3>No thread selected</h3>
              <p>Create a new thread or choose one from the sidebar to start chatting.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
