Set-Location "D:\. AI Forge Training\backend\Stackyon Intelligent Chat"
$ErrorActionPreference = 'Stop'

$base = 'http://127.0.0.1:8001'
$token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNjA5YWFlOS0yNjYwLTQ4ODYtYWM5Mi1lNzlhZDkzNGEyNzYiLCJlbWFpbCI6ImdpcmlzaC5kYW11bHVyaUBzdGFja3lvbi5jb20iLCJleHAiOjE3NzgzMTQzNDR9.hq-ILgv3B2uKSRTaJ3uteNjzMAlTYP7fNxBcWfxW2Bg'
$pdfPath = Join-Path $PWD 'backend\tmp_test_attachment.pdf'

$pdfContent = "%PDF-1.1`n1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n2 0 obj`n<< /Type /Pages /Kids [3 0 R] /Count 1 >>`nendobj`n3 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>`nendobj`n4 0 obj`n<< /Length 85 >>`nstream`nBT`n/F1 16 Tf`n40 90 Td`n(Quarterly revenue in the PDF is 42 million dollars.) Tj`nET`nendstream`nendobj`n5 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`nendobj`nxref`n0 6`n0000000000 65535 f `n0000000010 00000 n `n0000000063 00000 n `n0000000122 00000 n `n0000000256 00000 n `n0000000391 00000 n `ntrailer`n<< /Root 1 0 R /Size 6 >>`nstartxref`n461`n%%EOF`n"
[IO.File]::WriteAllText($pdfPath, $pdfContent, [Text.Encoding]::ASCII)

$thread = Invoke-RestMethod -Method Post -Uri "${base}/api/threads?token=${token}" -ContentType 'application/json' -Body '{"title":"Attachment Validation Thread"}'
$threadId = $thread.id

$uploadRaw = curl.exe -s -X POST "${base}/api/chat/attachments/upload?thread_id=${threadId}&token=${token}" -F "files=@$pdfPath;type=application/pdf"
$upload = $uploadRaw | ConvertFrom-Json
$attachmentId = $upload.attachment_ids[0]

$payload = @{ message = 'What revenue value is mentioned in the uploaded PDF?'; attachment_ids = @($attachmentId) } | ConvertTo-Json -Depth 5 -Compress
$null = Invoke-WebRequest -Method Post -Uri "${base}/api/threads/${threadId}/messages?token=${token}" -ContentType 'application/json' -Body $payload

$threadAfter = $null
for ($i = 0; $i -lt 6; $i++) {
  try {
    $threadAfter = Invoke-RestMethod -Method Get -Uri "${base}/api/threads/${threadId}?token=${token}"
    if ($threadAfter) { break }
  } catch {}
}

$assistantMsg = $threadAfter.messages | Where-Object { $_.role -eq 'assistant' } | Select-Object -Last 1

$refreshThread = $null
for ($i = 0; $i -lt 6; $i++) {
  try {
    $refreshThread = Invoke-RestMethod -Method Get -Uri "${base}/api/threads/${threadId}?token=${token}"
    if ($refreshThread) { break }
  } catch {}
}

$refreshUserMsg = $refreshThread.messages | Where-Object { $_.role -eq 'user' } | Select-Object -Last 1

$dbProof = & ".\.venv311\Scripts\python.exe" -c "import os,pathlib; from dotenv import load_dotenv; load_dotenv(pathlib.Path('backend/.env')); import psycopg; u=(os.getenv('DATABASE_URL') or '').replace('+asyncpg',''); c=psycopg.connect(u); cur=c.cursor(); cur.execute('select id, thread_id, original_filename, mime_type, file_size from chat_attachments where thread_id=%s order by created_at desc limit 1', ('$threadId',)); print(cur.fetchone()); cur.close(); c.close()"

[PSCustomObject]@{
  step1_upload_pdf = [bool]$attachmentId
  step2_question_sent = $true
  step3_response_preview = ($assistantMsg.content | Out-String).Trim()
  step4_refresh_attachment_persisted = [bool]($refreshUserMsg.attachment_ids -contains $attachmentId)
  step5_db_row_proof = $dbProof
  thread_id = $threadId
  attachment_id = $attachmentId
} | ConvertTo-Json -Depth 6
