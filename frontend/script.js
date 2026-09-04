const BACKEND_URL = 'http://localhost:8000/api/chat';
const DEMO_MODE = false;
const MAX_FILE_SIZE = 20 * 1024 * 1024;

let selectedFiles = [];
let isLoading = false;
let toastTimer;

const chatWindow = document.querySelector('#chat-window');
const welcomeState = document.querySelector('#welcome-state');
const fileInput = document.querySelector('#file-input');
const filePreview = document.querySelector('#file-preview');
const textInput = document.querySelector('#text-input');
const inputBar = document.querySelector('#input-bar');
const sendButton = document.querySelector('#send-btn');
const uploadButton = document.querySelector('#upload-btn');
const toast = document.querySelector('#toast');
const modeLabel = document.querySelector('#mode-label');

modeLabel.textContent = DEMO_MODE ? 'Demo mode' : 'Backend ready';

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function showError(message) {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add('visible');
  toastTimer = window.setTimeout(() => toast.classList.remove('visible'), 4200);
}

function renderFilePreview() {
  filePreview.replaceChildren();
  selectedFiles.forEach((file, index) => {
    const chip = document.createElement('div');
    chip.className = 'file-chip';

    const icon = document.createElement('span');
    icon.className = 'file-icon';
    icon.textContent = 'PDF';
    icon.setAttribute('aria-hidden', 'true');

    const name = document.createElement('span');
    name.className = 'file-name';
    name.textContent = file.name;

    const size = document.createElement('span');
    size.className = 'file-size';
    size.textContent = formatFileSize(file.size);

    const removeButton = document.createElement('button');
    removeButton.className = 'icon-button';
    removeButton.type = 'button';
    removeButton.title = `Remove ${file.name}`;
    removeButton.setAttribute('aria-label', `Remove ${file.name}`);
    removeButton.innerHTML = '&times;';
    removeButton.addEventListener('click', () => removeFile(index));

    chip.append(icon, name, size, removeButton);
    filePreview.append(chip);
  });
  filePreview.hidden = selectedFiles.length === 0;
  updateSendState();
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  renderFilePreview();
}

function clearSelectedFiles() {
  selectedFiles = [];
  fileInput.value = '';
  renderFilePreview();
}

function updateSendState() {
  sendButton.disabled = isLoading || (!selectedFiles.length && !textInput.value.trim());
}

function appendMessage(role, text, attachmentNames = []) {
  welcomeState?.remove();
  const message = document.createElement('div');
  message.className = `message ${role}`;

  const meta = document.createElement('span');
  meta.className = 'message-meta';
  meta.textContent = role === 'user' ? 'You' : 'DocChat';
  message.append(meta);

  const content = document.createElement('span');
  content.textContent = text;
  message.append(content);

  if (attachmentNames.length) {
    const attachment = document.createElement('span');
    attachment.className = 'message-meta';
    attachment.textContent = `${attachmentNames.length} PDF${attachmentNames.length === 1 ? '' : 's'} attached: ${attachmentNames.join(', ')}`;
    message.append(attachment);
  }

  chatWindow.append(message);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showTypingIndicator() {
  const indicator = document.createElement('div');
  indicator.className = 'message assistant';
  indicator.id = 'typing-indicator';
  indicator.setAttribute('aria-label', 'DocChat is typing');
  indicator.innerHTML = '<span class="message-meta">DocChat</span><span class="typing"><span></span><span></span><span></span></span>';
  chatWindow.append(indicator);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function hideTypingIndicator() {
  document.querySelector('#typing-indicator')?.remove();
}

function getDemoReply(message, files) {
  if (files.length) {
    return `I have received ${files.length} PDF${files.length === 1 ? '' : 's'}. In Demo mode I cannot inspect them yet, but your Python service can return its extracted answer here. Try setting DEMO_MODE to false in script.js when /api/chat is running.`;
  }
  return `I’m in Demo mode, so I can show the conversation flow but I cannot answer “${message}” yet. Connect your Python service at ${BACKEND_URL} to make this response live.`;
}

async function sendToBackend(formData, message, files) {
  if (DEMO_MODE) {
    await new Promise((resolve) => window.setTimeout(resolve, 650));
    return { reply: getDemoReply(message, files) };
  }

  const response = await fetch(BACKEND_URL, {
    method: 'POST',
    body: formData,
    signal: AbortSignal.timeout(30000)
  });

  if (!response.ok) throw new Error(`Server error: ${response.status}`);
  const data = await response.json();
  if (!data.reply) throw new Error('The service returned no reply.');
  return data;
}

async function handleSubmit(event) {
  event.preventDefault();
  if (isLoading) return;

  const message = textInput.value.trim();
  if (!message && !selectedFiles.length) return;

  const attachedFiles = [...selectedFiles];
  const formData = new FormData();
  attachedFiles.forEach((file) => formData.append('file', file));
  if (message) formData.append('message', message);

  appendMessage('user', message || 'Please review these documents.', attachedFiles.map((file) => file.name));
  isLoading = true;
  updateSendState();
  showTypingIndicator();

  try {
    const data = await sendToBackend(formData, message, attachedFiles);
    appendMessage('assistant', data.reply);
  } catch (error) {
    const errorMessage = error.name === 'TimeoutError'
      ? 'The service took too long to respond. Please try again.'
      : `I could not reach the document service. ${error.message}`;
    appendMessage('assistant', errorMessage);
  } finally {
    hideTypingIndicator();
    isLoading = false;
    clearSelectedFiles();
    textInput.value = '';
    textInput.style.height = 'auto';
    updateSendState();
  }
}

fileInput.addEventListener('change', (event) => {
  const files = [...event.target.files];
  files.forEach((file) => {
    const isPdf = file.type === 'application/pdf' && file.name.toLowerCase().endsWith('.pdf');
    if (!isPdf) {
      showError(`${file.name} is not a PDF. Only PDF files are supported right now.`);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      showError(`${file.name} is larger than 20 MB. Please choose a smaller file.`);
      return;
    }

    const alreadySelected = selectedFiles.some((selectedFile) => selectedFile.name === file.name && selectedFile.size === file.size && selectedFile.lastModified === file.lastModified);
    if (!alreadySelected) selectedFiles.push(file);
  });

  event.target.value = '';
  renderFilePreview();
});

uploadButton.addEventListener('click', () => fileInput.click());
inputBar.addEventListener('submit', handleSubmit);
textInput.addEventListener('input', () => {
  textInput.style.height = 'auto';
  textInput.style.height = `${Math.min(textInput.scrollHeight, 140)}px`;
  updateSendState();
});
textInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    inputBar.requestSubmit();
  }
});
document.querySelectorAll('.suggestion').forEach((button) => {
  button.addEventListener('click', () => {
    textInput.value = button.dataset.prompt;
    textInput.dispatchEvent(new Event('input'));
    textInput.focus();
  });
});

updateSendState();
