import { FormEvent, useEffect, useState } from "react";

import { createThread, deleteThread, getThread, listThreads, streamChat, updateThread } from "../lib/api";
import { ChatThread, ChatMessage, User } from "../types/index";

interface ChatPageProps {
  user: User;
  token: string;
  onLogout: () => void;
}

function toChatMessages(messages: ChatThread["messages"]): ChatMessage[] {
  return (
    messages?.map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
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

export function ChatPage({ user, token, onLogout }: Readonly<ChatPageProps>) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThread, setActiveThread] = useState<ChatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasActiveThread = activeThread !== null;
  const messageCountLabel =
    messages.length === 1 ? "1 message" : `${messages.length} messages`;

  useEffect(() => {
    loadThreads();
  }, []);

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

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!input.trim() || !activeThread || isLoading) return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36).slice(2),
      role: "user",
      content: input,
    };
    const assistantId = Math.random().toString(36).slice(2);

    setError(null);
    setInput("");
    setIsLoading(true);
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantId, role: "assistant", content: "" },
    ]);

    try {
      await streamChat(token, activeThread.id, userMessage.content, {
        onToken(token) {
          setMessages((prev) => appendAssistantToken(prev, assistantId, token));
        },
        onDone() {
          setIsLoading(false);
          getThread(token, activeThread.id)
            .then((thread) => {
              setActiveThread(thread);
              setMessages(toChatMessages(thread.messages));
              setThreads((prev) => mergeUpdatedThread(prev, thread));
            })
            .catch(() => {
              // Ignore refresh failures; current message stream already rendered in UI.
            });
        },
        onError(messageText) {
          setError(messageText);
          setIsLoading(false);
        },
      });
    } catch (err) {
      const messageText = err instanceof Error ? err.message : "Unexpected error";
      setError(messageText);
      setIsLoading(false);
    }
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
            <header className="chat-thread-header">
              <div>
                <p className="chat-thread-kicker">Active thread</p>
                <h2>{activeThread.title}</h2>
              </div>
              <p className="chat-thread-subtitle">
                {messages.length > 0 ? messageCountLabel : "No messages yet"}
              </p>
            </header>

            <div className="chat-messages">
              {messages.length === 0 ? (
                <div className="chat-conversation-empty">
                  <h3>Start the conversation</h3>
                  <p>Send the first message in this thread to begin generating responses.</p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className={`message-row message-row-${msg.role}`}>
                    <div className={`message-avatar message-avatar-${msg.role}`}>
                      {getMessageBadge(msg.role)}
                    </div>
                    <div className={`message message-${msg.role}`}>
                      <div className="message-meta">
                        <strong>{getMessageLabel(msg.role)}</strong>
                      </div>
                      <p>{msg.content || (msg.role === "assistant" && isLoading ? "..." : "")}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="chat-composer-shell">
              <div className="chat-composer-copy">
                <p className="chat-composer-kicker">Message</p>
                <p className="chat-composer-note">
                  Ask a follow-up question or continue the active thread.
                </p>
              </div>

              <form onSubmit={handleSendMessage} className="chat-input-form">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Type your message"
                  disabled={isLoading}
                />
                <button type="submit" disabled={isLoading || !input.trim()}>
                  {isLoading ? "Sending..." : "Send"}
                </button>
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
