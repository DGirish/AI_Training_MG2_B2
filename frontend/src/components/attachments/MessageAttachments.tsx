import React from "react";

import { API_BASE_URL } from "@/config/env";
import { Attachment } from "@/types/attachment";

interface MessageAttachmentsProps {
  attachments: Attachment[];
  token: string;
  onAskPdf?: (attachment: Attachment) => Promise<void>;
  activeRagAttachmentId?: string | null;
  ragBusy?: boolean;
}

function buildAttachmentUrl(attachmentId: string, token: string): string {
  return `${API_BASE_URL}/api/chat/attachments/${attachmentId}/content?token=${encodeURIComponent(token)}`;
}

export const MessageAttachments: React.FC<MessageAttachmentsProps> = ({
  attachments,
  token,
  onAskPdf,
  activeRagAttachmentId,
  ragBusy,
}) => {
  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 grid gap-2">
      {attachments.map((attachment) => {
        const pdfStatus = (attachment.indexed_status ?? "not_indexed").toLowerCase();
        const isPdfIndexing = attachment.attachment_type === "pdf" && pdfStatus === "indexing";
        let askPdfLabel = "Ask PDF";
        if (isPdfIndexing) {
          askPdfLabel = "Indexing...";
        } else if (activeRagAttachmentId === attachment.id) {
          askPdfLabel = "RAG Active";
        }

        return (
        <div key={attachment.id} className="attachment-card">
          {(attachment.attachment_type === "image" || attachment.attachment_type === "generated_image") && (
            <img
              src={buildAttachmentUrl(attachment.id, token)}
              alt={attachment.prompt || attachment.original_filename}
              className="mb-2 max-h-72 w-full rounded-lg object-cover"
            />
          )}

          {attachment.attachment_type === "video" && (
            <video controls className="mb-2 max-h-72 w-full rounded-lg" src={buildAttachmentUrl(attachment.id, token)}>
              <track kind="captions" />
            </video>
          )}

          <p className="font-semibold">{attachment.original_filename}</p>
          <div className="attachment-meta-row">
            <p className="text-slate-500">
              {attachment.attachment_type} • {(attachment.file_size / 1024).toFixed(1)} KB
            </p>
            {attachment.attachment_type === "pdf" && (
              <span
                className={`indexed-pill indexed-pill-${pdfStatus} ${isPdfIndexing ? "is-indexing" : ""}`}
                title={`Index status: ${attachment.indexed_status ?? "not_indexed"}`}
              >
                {isPdfIndexing ? "Indexing..." : (attachment.indexed_status ?? "not_indexed").replace("_", " ")}
              </span>
            )}
          </div>
          {attachment.attachment_type === "pdf" && onAskPdf && (
            <button
              type="button"
              className={`rag-ask-btn ${activeRagAttachmentId === attachment.id ? "active" : ""}`}
              onClick={() => void onAskPdf(attachment)}
              disabled={Boolean(ragBusy) || isPdfIndexing}
            >
              {askPdfLabel}
            </button>
          )}
          {attachment.model_name && <p className="text-slate-500">Model: {attachment.model_name}</p>}
          {attachment.prompt && <p className="mt-1 text-slate-600">Prompt: {attachment.prompt}</p>}
          {attachment.generation_error && <p className="mt-1 text-red-600">{attachment.generation_error}</p>}
          {attachment.indexing_error && <p className="mt-1 text-red-600">{attachment.indexing_error}</p>}
        </div>
      );})}
    </div>
  );
};
