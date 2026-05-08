export interface Attachment {
  id: string;
  user_id: string;
  thread_id: string;
  source_message_id?: string | null;
  message_id: string | null;
  original_filename: string;
  stored_filename: string;
  storage_path: string;
  public_url: string | null;
  mime_type: string;
  file_size: number;
  attachment_type: "image" | "video" | "pdf" | "table" | "code" | "text" | "generated_image";
  storage_bucket?: string | null;
  model_name?: string | null;
  prompt?: string | null;
  width?: number | null;
  height?: number | null;
  generation_status?: string | null;
  generation_error?: string | null;
  indexed_status?: string | null;
  indexed_at?: string | null;
  chunk_count?: number | null;
  indexing_error?: string | null;
  created_at: string;
}

export interface MessageWithAttachments {
  message: string;
  attachment_ids: string[];
}

export interface UploadAttachmentsResponse {
  attachment_ids: string[];
  attachments: Attachment[];
}
