import React, { useRef, useState } from "react";

interface AttachmentButtonProps {
  disabled?: boolean;
  onFilesSelected: (files: File[]) => Promise<void>;
  onError?: (message: string) => void;
}

export const AttachmentButton: React.FC<AttachmentButtonProps> = ({
  disabled,
  onFilesSelected,
  onError,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);

  const validateFiles = (files: File[]): File[] => {
    const maxSize = 20 * 1024 * 1024;
    for (const file of files) {
      if (file.size > maxSize) {
        throw new Error(`File ${file.name} exceeds 20 MB limit`);
      }
    }
    return files;
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || disabled || uploading) {
      return;
    }

    try {
      const selected = validateFiles(Array.from(files));
      setUploading(true);
      await onFilesSelected(selected);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to upload files";
      onError?.(message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <button
      type="button"
      className={`attach-trigger ${dragActive ? "is-drag-active" : ""}`}
      onClick={() => inputRef.current?.click()}
      disabled={disabled || uploading}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled && !uploading) {
          setDragActive(true);
        }
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        setDragActive(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragActive(false);
        void handleFiles(event.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        accept="image/*,video/*,application/pdf,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain,text/markdown,text/x-python,text/javascript,application/json"
        onChange={(event) => {
          void handleFiles(event.currentTarget.files);
          event.currentTarget.value = "";
        }}
      />

      <span className="attach-chip">
        {uploading ? "Uploading..." : "+ Files"}
      </span>
    </button>
  );
};
