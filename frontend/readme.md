# ChatGPT-Clone Frontend — Project Spec

A lightweight, plain **HTML + CSS + JS** chat interface (no frameworks) styled like ChatGPT, with a PDF-only document upload feature that sends the file to a Python backend service and renders the response as a chat reply.

---

## 1. Goals

- Single-page chat UI (HTML/CSS/JS only — no React/Vue/build tools).
- Chat-style message list (user messages right-aligned, assistant messages left-aligned) similar to ChatGPT.
- File upload button that accepts **PDF only** (images and other file types rejected client-side).
- On upload, send the file to a Python backend (e.g., FastAPI/Flask) via `multipart/form-data`.
- Display the backend's response as an assistant message in the chat.
- Support a normal text input too, so the user can chat without uploading a file (optional — confirm if needed).

---

## 2. File Structure

```
chatgpt-clone/
├── index.html
├── style.css
└── script.js
```

Keep everything in 3 files as requested — no bundlers, no external frameworks. Optional: a `assets/` folder for icons.

---

## 3. index.html — Structure

- `<header>` — App title / logo (e.g., "DocChat").
- `<main id="chat-window">` — Scrollable message list container.
  - Each message rendered as `<div class="message user">` or `<div class="message assistant">`.
- `<footer id="input-bar">`
  - `<input type="file" id="file-input" accept="application/pdf" hidden>` — hidden, triggered by a paperclip/upload icon button.
  - `<button id="upload-btn">📎</button>` — opens file picker.
  - `<textarea id="text-input" placeholder="Message...">` — optional text chat.
  - `<button id="send-btn">Send</button>`.
- A small **file preview chip** area above the input bar showing the selected PDF's name + a remove (✕) button before sending.
- A **loading indicator** (typing dots or spinner) while waiting for the Python service response.

---

## 4. style.css — Styling Notes

- Match ChatGPT's general layout: centered column (max-width ~768px), dark or light theme (pick one, or add a toggle).
- `#chat-window`: `flex-direction: column`, `overflow-y: auto`, padding, gap between messages.
- `.message.user`: aligned right, accent background (e.g., `#10a37f` or similar), rounded corners.
- `.message.assistant`: aligned left, neutral background (`#f7f7f8` light / `#444654` dark).
- `#input-bar`: sticky to bottom, `display: flex`, rounded input container with shadow.
- File preview chip: small pill showing 📄 filename + ✕, positioned above the input bar.
- Loading indicator: 3 bouncing dots animation (`@keyframes bounce`).
- Disabled state styling for send button while a request is in-flight.
- Responsive: stack nicely on mobile widths.

---

## 5. script.js — Core Logic

### 5.1 State
```js
let selectedFile = null; // holds the validated PDF File object
let isLoading = false;
```

### 5.2 File Selection & Validation (PDF only)
- Listen to `file-input` `change` event.
- **Validate strictly**:
  - `file.type === 'application/pdf'` **AND**
  - filename ends with `.pdf` (belt-and-suspenders, since `type` can be empty/unreliable in some browsers).
- If validation fails (e.g., user picks a `.png`/`.jpg`):
  - Show an inline error toast/message: *"Only PDF files are supported right now."*
  - Reset the file input (`file-input.value = ''`) so the same invalid file can be reselected after correction.
  - Do **not** add it to `selectedFile`.
- If valid: store in `selectedFile`, render the file preview chip, enable send button.

```js
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;

  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  if (!isPdf) {
    showError('Only PDF files are supported. Please select a .pdf file.');
    e.target.value = '';
    return;
  }
  selectedFile = file;
  renderFilePreview(file);
}
```

### 5.3 Sending a Message / File to the Python Service
- On `send-btn` click (or Enter key):
  - Build a `FormData` object:
    ```js
    const formData = new FormData();
    if (selectedFile) formData.append('file', selectedFile);
    if (textInput.value.trim()) formData.append('message', textInput.value.trim());
    ```
  - `POST` to your Python service endpoint (e.g., `http://localhost:8000/api/chat` or `/upload`):
    ```js
    async function sendToBackend(formData) {
      isLoading = true;
      showTypingIndicator();
      try {
        const res = await fetch(BACKEND_URL, { method: 'POST', body: formData });
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data = await res.json(); // expect { reply: "..." } or similar
        appendMessage('assistant', data.reply);
      } catch (err) {
        appendMessage('assistant', `⚠️ Error: ${err.message}`);
      } finally {
        isLoading = false;
        hideTypingIndicator();
        clearSelectedFile();
        textInput.value = '';
      }
    }
    ```
  - Append the user's message (text + a "📄 filename.pdf attached" note) to the chat immediately (optimistic render), then wait for the assistant's reply.

### 5.4 Rendering Messages
```js
function appendMessage(role, text) {
  const el = document.createElement('div');
  el.className = `message ${role}`;
  el.textContent = text; // sanitize/escape before using innerHTML if rendering markdown/HTML
  chatWindow.appendChild(el);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}
```
- If the Python service returns markdown, consider a lightweight markdown-to-HTML step (or keep it plain text initially — confirm requirement).

### 5.5 Config
- Keep `BACKEND_URL` as a constant at the top of `script.js` for easy editing:
  ```js
  const BACKEND_URL = 'http://localhost:8000/api/chat';
  ```

---

## 6. Backend Contract (what your Python service should expect/return)

**Request** (`multipart/form-data`):
| Field | Type | Notes |
|---|---|---|
| `file` | PDF binary | optional if only sending text |
| `message` | string | optional user text alongside the file |

**Response** (JSON):
```json
{
  "reply": "Extracted/answered content from the PDF..."
}
```
> Adjust field names to match your actual Python API — flag this if your service uses a different contract (e.g., `answer`, `result`, streaming response, etc.).

- CORS: your Python service must allow requests from the frontend's origin (`Access-Control-Allow-Origin`) since this is plain HTML served separately (e.g., via `file://`, Live Server, or a static host).

---

## 7. Validation & Edge Cases to Handle

- [ ] Reject non-PDF files client-side with a clear message (no image support yet, per requirement).
- [ ] Reject if file size exceeds a sane limit (e.g., 20MB) — configurable.
- [ ] Disable send button while `isLoading` is true (prevent double submits).
- [ ] Handle backend errors/timeouts gracefully (show error bubble, don't crash the UI).
- [ ] Allow removing a selected file before sending (✕ on the preview chip).
- [ ] Auto-scroll chat to bottom on new messages.
- [ ] Escape/sanitize any HTML in assistant responses before inserting into the DOM (avoid `innerHTML` with raw text, or sanitize if rendering markdown).

---

## 8. Future Enhancements (not in this phase)

- Image upload support (explicitly excluded for now).
- Multi-file upload.
- Streaming responses (Server-Sent Events / chunked fetch) instead of waiting for full reply.
- Chat history persistence (localStorage or backend-side sessions).
- Dark/light theme toggle.

---

## 9. Open Questions to Confirm Before Building

1. What is the exact Python backend endpoint URL and request/response schema?
2. Should plain text chat (no file) also be supported, or is upload the only input mode?
3. Any max file size limit for the PDF?
4. Should assistant responses support markdown/code rendering, or plain text only?
5. Any authentication needed for the backend call (API key/header)?
