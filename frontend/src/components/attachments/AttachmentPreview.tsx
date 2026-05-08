import React from "react";
import { Attachment } from "@/types/attachment";

interface AttachmentPreviewProps {
  attachment: Attachment;
  onRemove?: () => void;
}

export const AttachmentPreview: React.FC<AttachmentPreviewProps> = ({
  attachment,
  onRemove,
}) => {
  const iconMap: Record<string, string> = {
    image: "🖼️",
    generated_image: "🎨",
    video: "🎥",
    pdf: "📄",
    code: "📝",
    table: "📊",
    text: "📃",
  };
  const icon = iconMap[attachment.attachment_type] || "📄";

  const sizeInKB = (attachment.file_size / 1024).toFixed(1);

  return (
    <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
      <span>{icon}</span>
      <span className="max-w-xs truncate">{attachment.original_filename}</span>
      <span className="text-xs text-slate-500">
        ({sizeInKB} KB)
      </span>
      {onRemove && (
        <button
          onClick={onRemove}
          className="ml-1 rounded px-1 text-slate-500 transition-colors hover:text-red-600"
          title="Remove attachment"
        >
          ✕
        </button>
      )}
    </div>
  );
};
